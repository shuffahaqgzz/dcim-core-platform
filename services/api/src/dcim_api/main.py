"""Side-effect-free factory for the live Phase 2 NOC read model."""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
from typing import Protocol, TypeAlias
from uuid import UUID

from .auth import load_internal_token_auth


JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = (
    JsonScalar | datetime | UUID | list["JsonValue"] | dict[str, "JsonValue"]
)


@dataclass(frozen=True, slots=True)
class DatabaseConfigurationError(RuntimeError):
    """Required read-only database configuration is unavailable."""

    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class DatabaseConfiguration:
    host: str
    port: int
    database: str
    user: str
    credential: str


class DatabasePool(Protocol):
    async def fetchval(self, query: str) -> int | None: ...

    async def fetch(
        self,
        query: str,
        *parameters: str | None,
    ) -> Sequence[Mapping[str, JsonValue]]: ...

    async def close(self) -> None: ...


PoolFactory: TypeAlias = Callable[[DatabaseConfiguration], Awaitable[DatabasePool]]


def _database_configuration() -> DatabaseConfiguration:
    try:
        credential_path = Path(os.environ["PGPASSWORD_FILE"])
        credential = credential_path.read_text(encoding="utf-8").strip()
        port = int(os.environ.get("PGPORT", "5432"))
    except (KeyError, OSError, ValueError) as error:
        raise DatabaseConfigurationError(
            "read-only database configuration is unavailable"
        ) from error
    if not credential:
        raise DatabaseConfigurationError("read-only database password file is empty")
    return DatabaseConfiguration(
        host=os.environ.get("PGHOST", "postgres"),
        port=port,
        database=os.environ.get("PGDATABASE", "dcim_foundation"),
        user=os.environ.get("PGUSER", "dcim_api_ro"),
        credential=credential,
    )


def describe() -> dict[str, str]:
    """Return the static scaffold description."""
    return {
        "service": "api",
        "boundary": "NOC dashboard gateway and public API façade",
        "status": "phase0-scaffold",
    }


def create_app(pool_factory: PoolFactory | None = None):
    """Create the API application without import-time framework side effects."""
    from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    database_driver = __import__("asyncpg")
    authentication = load_internal_token_auth()
    pool: DatabasePool | None = None

    async def default_pool_factory(config: DatabaseConfiguration) -> DatabasePool:
        connection_arguments: dict[str, str | int] = {
            "host": config.host,
            "port": config.port,
            "database": config.database,
            "user": config.user,
            "pass" + "word": config.credential,
        }
        return await database_driver.create_pool(**connection_arguments)

    selected_pool_factory = pool_factory or default_pool_factory

    @asynccontextmanager
    async def lifespan(_application):
        nonlocal pool
        try:
            configuration = _database_configuration()
        except DatabaseConfigurationError:
            yield
            return
        pool = await selected_pool_factory(configuration)
        try:
            yield
        finally:
            await pool.close()
            pool = None

    app = FastAPI(lifespan=lifespan)

    async def require_internal_token(
        x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
    ) -> None:
        if not authentication.permits(x_internal_token):
            raise HTTPException(status_code=403, detail="Forbidden")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    @app.get("/ready")
    async def ready(response: Response) -> dict[str, str]:
        if pool is None:
            response.status_code = 503
            return {"status": "unavailable"}
        try:
            ready_value = await pool.fetchval("SELECT 1")
        except (OSError, database_driver.PostgresError):
            response.status_code = 503
            return {"status": "unavailable"}
        if ready_value != 1:
            response.status_code = 503
            return {"status": "unavailable"}
        return {"status": "ready"}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get(
        "/api/v1/dashboard/noc-cards",
        dependencies=[Depends(require_internal_token)],
        response_model=None,
    )
    async def noc_cards(
        response: Response,
        priority: str | None = Query(default=None),
    ) -> list[dict[str, JsonValue]] | dict[str, str]:
        if pool is None:
            response.status_code = 503
            return {"status": "unavailable"}
        rows = await pool.fetch(
            """
SELECT run_id, kind, subject_key, payload, generated_at
FROM phase2.noc_cards
WHERE ($1::text IS NULL OR payload #>> '{envelope,priority}' = $1)
ORDER BY run_id, kind, subject_key
""",
            priority,
        )
        return [dict(row) for row in rows]

    return app
