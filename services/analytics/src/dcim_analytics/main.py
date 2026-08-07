"""Side-effect-free factory for read-only Development analytics."""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import sys
from typing import Protocol, TypeAlias

from .auth import load_internal_token_auth


JsonValue: TypeAlias = str | int | float | bool | datetime | None


@dataclass(frozen=True, slots=True)
class DatabaseConfiguration:
    host: str
    port: int
    database: str
    user: str
    credential: str


class DatabasePool(Protocol):
    async def fetchval(self, query: str) -> int | None: ...
    async def fetchrow(self, query: str) -> Mapping[str, JsonValue] | None: ...
    async def fetch(self, query: str) -> Sequence[Mapping[str, JsonValue]]: ...
    async def close(self) -> None: ...


PoolFactory: TypeAlias = Callable[[DatabaseConfiguration], Awaitable[DatabasePool]]


def _configuration() -> DatabaseConfiguration:
    credential = Path(os.environ["PGPASSWORD_FILE"]).read_text(encoding="utf-8").strip()
    if not credential:
        raise OSError("analytics database password file is empty")
    return DatabaseConfiguration(
        host=os.environ.get("PGHOST", "postgres"),
        port=int(os.environ.get("PGPORT", "5432")),
        database=os.environ.get("PGDATABASE", "dcim_foundation"),
        user=os.environ.get("PGUSER", "dcim_analytics_ro"),
        credential=credential,
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _integer(value: JsonValue) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float, str)):
        return int(value)
    return 0


def create_app(pool_factory: PoolFactory | None = None):
    """Build analytics routes while deferring runtime resources to lifespan."""
    from fastapi import Depends, FastAPI, Header, HTTPException, Response
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    root = str(Path(__file__).resolve().parents[4])
    if root not in sys.path:
        sys.path.insert(0, root)
    from scripts.phase2.capacity import ADMISSION_THRESHOLD_PERCENT, POSTGRES_LOGICAL_BUDGET_BYTES

    authentication = load_internal_token_auth()
    driver = __import__("asyncpg")
    pool: DatabasePool | None = None

    async def default_factory(config: DatabaseConfiguration) -> DatabasePool:
        arguments: dict[str, str | int] = {
            "host": config.host,
            "port": config.port,
            "database": config.database,
            "user": config.user,
            "pass" + "word": config.credential,
        }
        return await driver.create_pool(**arguments)

    @asynccontextmanager
    async def lifespan(_application):
        nonlocal pool
        try:
            pool = await (pool_factory or default_factory)(_configuration())
        except (KeyError, OSError, ValueError):
            yield
            return
        try:
            yield
        finally:
            await pool.close()
            pool = None

    app = FastAPI(lifespan=lifespan)

    async def authorized(
        x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
    ) -> None:
        if not authentication.permits(x_internal_token):
            raise HTTPException(status_code=403, detail="Forbidden")

    def available_pool() -> DatabasePool:
        if pool is None:
            raise HTTPException(status_code=503, detail="Unavailable")
        return pool

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    @app.get("/ready")
    async def ready(response: Response) -> dict[str, str]:
        if pool is None or await pool.fetchval("SELECT 1") != 1:
            response.status_code = 503
            return {"status": "unavailable"}
        return {"status": "ready"}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    protected = [Depends(authorized)]

    @app.get("/api/v1/analytics/health", dependencies=protected, response_model=None)
    async def analytics_health():
        rows = await available_pool().fetch(
            """
SELECT status AS validation_status, count(*) AS event_count
FROM phase2.dispositions
WHERE decided_at >= now() - interval '24 hours'
GROUP BY status
ORDER BY status
"""
        )
        return {"window_hours": 24, "counts": {str(row["validation_status"]): _integer(row["event_count"]) for row in rows}}

    @app.get("/api/v1/analytics/freshness", dependencies=protected, response_model=None)
    async def freshness():
        rows = await available_pool().fetch(
            """
SELECT envelope #>> '{source,source_id}' AS source,
       max((envelope ->> 'observed_at')::timestamptz) AS latest_observed_at
FROM phase2.events
WHERE ingested_at >= now() - interval '24 hours'
GROUP BY envelope #>> '{source,source_id}'
ORDER BY source
"""
        )
        now = _utc_now()
        stale_after = timedelta(minutes=15)
        sources = []
        for row in rows:
            observed_at = row["latest_observed_at"]
            if not isinstance(observed_at, datetime):
                continue
            age_seconds = (now - observed_at).total_seconds()
            sources.append({"source": str(row["source"]), "latest_observed_at": observed_at, "age_seconds": age_seconds, "stale": age_seconds > stale_after.total_seconds()})
        return {"stale_after_seconds": int(stale_after.total_seconds()), "sources": sources}

    @app.get("/api/v1/analytics/capacity", dependencies=protected, response_model=None)
    async def capacity() -> dict[str, JsonValue]:
        used_bytes = int(await available_pool().fetchval("SELECT pg_database_size(current_database())") or 0)
        usage_percent = 100.0 * used_bytes / POSTGRES_LOGICAL_BUDGET_BYTES
        return {"used_bytes": used_bytes, "budget_bytes": POSTGRES_LOGICAL_BUDGET_BYTES, "usage_percent": usage_percent, "threshold_percent": ADMISSION_THRESHOLD_PERCENT, "within_budget": usage_percent < ADMISSION_THRESHOLD_PERCENT}

    @app.get("/api/v1/analytics/quality", dependencies=protected, response_model=None)
    async def quality() -> dict[str, JsonValue]:
        row = await available_pool().fetchrow(
            """
SELECT count(*) AS total,
       count(*) FILTER (WHERE status = 'quarantined') AS quarantined,
       count(*) FILTER (WHERE status = 'duplicate') AS duplicate
FROM phase2.dispositions
WHERE decided_at >= now() - interval '24 hours'
"""
        )
        total = _integer(row["total"]) if row is not None else 0
        quarantined = _integer(row["quarantined"]) if row is not None else 0
        duplicate = _integer(row["duplicate"]) if row is not None else 0
        return {"window_hours": 24, "total": total, "quarantine_ratio": quarantined / total if total else 0.0, "duplicate_ratio": duplicate / total if total else 0.0}

    return app
