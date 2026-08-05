"""Side-effect-free factory for the live Phase 2 NOC read model."""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
from typing import Any, Protocol, TypeAlias
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


class UpstreamConfigurationError(RuntimeError):
    """Required gateway upstream configuration is unavailable."""



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
ClientFactory: TypeAlias = Callable[[str, str], Any]


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


def _upstream_configuration() -> tuple[str, str, str]:
    try:
        asset_repository_url = os.environ["ASSET_REPOSITORY_URL"]
        cmdb_url = os.environ["CMDB_URL"]
        header_value = Path(os.environ["INTERNAL_API_TOKEN_FILE"]).read_text(encoding="utf-8").strip()
    except (KeyError, OSError) as error:
        raise UpstreamConfigurationError("gateway upstream configuration is unavailable") from error
    if not asset_repository_url or not cmdb_url or not header_value:
        raise UpstreamConfigurationError("gateway upstream configuration is unavailable")
    return asset_repository_url, cmdb_url, header_value


def describe() -> dict[str, str]:
    """Return the static scaffold description."""
    return {
        "service": "api",
        "boundary": "NOC dashboard gateway and public API façade",
        "status": "phase0-scaffold",
    }


def create_app(
    pool_factory: PoolFactory | None = None,
    client_factory: ClientFactory | None = None,
):
    """Create the API application without import-time framework side effects."""
    from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    database_driver = __import__("asyncpg")
    http_client_driver = __import__("httpx")
    authentication = load_internal_token_auth()
    pool: DatabasePool | None = None
    asset_client: Any | None = None
    cmdb_client: Any | None = None

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

    def default_client_factory(base_url: str, header_value: str) -> Any:
        return http_client_driver.AsyncClient(
            base_url=base_url,
            headers={"X-Internal-Token": header_value},
            follow_redirects=True,
            timeout=http_client_driver.Timeout(connect=5.0, read=30.0, write=10.0, pool=10.0),
            limits=http_client_driver.Limits(
                max_connections=200,
                max_keepalive_connections=40,
                keepalive_expiry=30.0,
            ),
        )

    selected_client_factory = client_factory or default_client_factory

    @asynccontextmanager
    async def lifespan(_application):
        nonlocal asset_client, cmdb_client, pool
        asset_repository_url, cmdb_url, header_value = _upstream_configuration()
        asset_client = selected_client_factory(asset_repository_url, header_value)
        cmdb_client = selected_client_factory(cmdb_url, header_value)
        try:
            configuration = _database_configuration()
        except DatabaseConfigurationError:
            configuration = None
        if configuration is not None:
            pool = await selected_pool_factory(configuration)
        try:
            yield
        finally:
            if pool is not None:
                await pool.close()
            pool = None
            active_asset_client = asset_client
            active_cmdb_client = cmdb_client
            if active_asset_client is not None:
                await active_asset_client.aclose()
            if active_cmdb_client is not None:
                await active_cmdb_client.aclose()
            asset_client = None
            cmdb_client = None

    app = FastAPI(lifespan=lifespan)

    async def require_internal_token(
        x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
    ) -> None:
        if not authentication.permits(x_internal_token):
            raise HTTPException(status_code=403, detail="Forbidden")

    async def proxy_request(request: Request, client: Any | None) -> Response:
        if client is None:
            return Response(content='{"detail":"Upstream service unavailable"}', status_code=502, media_type="application/json")
        headers = {
            name: value
            for name, value in request.headers.items()
            if name.casefold() not in {"host", "content-length", "x-internal-token"}
        }
        try:
            upstream = await client.request(
                request.method,
                request.url.path,
                params=request.query_params,
                content=await request.body(),
                headers=headers,
            )
        except http_client_driver.ConnectError:
            return Response(content='{"detail":"Upstream service unavailable"}', status_code=502, media_type="application/json")
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            media_type=upstream.headers.get("content-type"),
        )

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

    @app.api_route(
        "/api/v1/assets",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        dependencies=[Depends(require_internal_token)],
        response_model=None,
    )
    @app.api_route(
        "/api/v1/assets/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        dependencies=[Depends(require_internal_token)],
        response_model=None,
    )
    async def proxy_assets(request: Request, path: str = "") -> Response:
        return await proxy_request(request, asset_client)

    @app.api_route(
        "/api/v1/cis",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        dependencies=[Depends(require_internal_token)],
        response_model=None,
    )
    @app.api_route(
        "/api/v1/cis/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        dependencies=[Depends(require_internal_token)],
        response_model=None,
    )
    async def proxy_cis(request: Request, path: str = "") -> Response:
        return await proxy_request(request, cmdb_client)

    @app.get(
        "/api/v1/dashboard/summary",
        dependencies=[Depends(require_internal_token)],
        response_model=None,
    )
    async def dashboard_summary(response: Response) -> dict[str, JsonValue]:
        if pool is None or asset_client is None or cmdb_client is None:
            response.status_code = 503
            return {"status": "unavailable"}
        try:
            asset_response = await asset_client.get("/api/v1/assets")
            ci_response = await cmdb_client.get("/api/v1/cis")
        except http_client_driver.ConnectError:
            response.status_code = 502
            return {"detail": "Upstream service unavailable"}
        asset_response.raise_for_status()
        ci_response.raise_for_status()
        priorities = await pool.fetch(
            "SELECT payload #>> '{envelope,priority}' AS priority, COUNT(*) AS count "
            "FROM phase2.noc_cards GROUP BY priority"
        )
        observed_at = await pool.fetchval(
            "SELECT MAX(payload #>> '{envelope,observed_at}') FROM phase2.noc_cards"
        )
        counts: dict[str, int] = {}
        for row in priorities:
            priority = row["priority"]
            count = row["count"]
            if isinstance(priority, str) and isinstance(count, int):
                counts[priority] = count
        return {
            "noc_cards": counts,
            "freshness": {"observed_at": observed_at},
            "assets": {"count": len(asset_response.json())},
            "cis": {"count": len(ci_response.json())},
        }

    return app
