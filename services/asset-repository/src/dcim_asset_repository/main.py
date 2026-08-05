"""Side-effect-free FastAPI factory for Asset persistence and alias lookup."""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Protocol, TypeAlias
from uuid import UUID

from .auth import load_internal_token_auth
from .models import Asset, AssetCreate


@dataclass(frozen=True, slots=True)
class DatabaseConfigurationError(RuntimeError):
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
    async def fetchrow(self, query: str, *parameters: UUID) -> Mapping[str, object] | None: ...
    async def fetch(self, query: str, *parameters: object) -> Sequence[Mapping[str, object]]: ...
    async def execute(self, query: str, *parameters: object) -> str | None: ...
    async def executemany(self, query: str, parameters: Sequence[tuple[object, ...]]) -> None: ...
    async def close(self) -> None: ...


PoolFactory: TypeAlias = Callable[[DatabaseConfiguration], Awaitable[DatabasePool]]


def _database_configuration() -> DatabaseConfiguration:
    try:
        credential = Path(os.environ["PGPASSWORD_FILE"]).read_text(encoding="utf-8").strip()
        port = int(os.environ.get("PGPORT", "5432"))
    except (KeyError, OSError, ValueError) as error:
        raise DatabaseConfigurationError("asset database configuration is unavailable") from error
    if not credential:
        raise DatabaseConfigurationError("asset database password file is empty")
    return DatabaseConfiguration(os.environ.get("PGHOST", "postgres"), port, os.environ.get("PGDATABASE", "dcim_foundation"), os.environ.get("PGUSER", "dcim_assets_rw"), credential)


def _asset(row: Mapping[str, object], aliases: Sequence[Mapping[str, object]]) -> Asset:
    return Asset.model_validate({**dict(row), "aliases": [{**dict(alias), "confidence": int(alias["confidence"]) / 100} for alias in aliases]})


def create_app(pool_factory: PoolFactory | None = None):
    """Create the Asset Repository without import-time framework effects."""
    from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    root = str(Path(__file__).resolve().parents[4])
    if root not in sys.path:
        sys.path.insert(0, root)
    from scripts.phase2 import identity

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

    @asynccontextmanager
    async def lifespan(_application):
        nonlocal pool
        try:
            configuration = _database_configuration()
        except DatabaseConfigurationError:
            yield
            return
        pool = await (pool_factory or default_pool_factory)(configuration)
        try:
            yield
        finally:
            await pool.close()
            pool = None

    app = FastAPI(lifespan=lifespan)

    async def require_internal_token(x_internal_token: str | None = Header(default=None, alias="X-Internal-Token")) -> None:
        if not authentication.permits(x_internal_token):
            raise HTTPException(status_code=403, detail="Forbidden")

    async def retrieve(asset_id: UUID) -> Asset | None:
        if pool is None:
            return None
        row = await pool.fetchrow("SELECT asset_id, identity, asset_type, created_at, updated_at FROM phase2.assets WHERE asset_id = $1", asset_id)
        if row is None:
            return None
        aliases = await pool.fetch("SELECT type, value, valid_from, valid_to, source, confidence FROM phase2.aliases WHERE owner_type = 'asset' AND owner_id = $1", asset_id)
        return _asset(row, aliases)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    @app.get("/ready")
    async def ready(response: Response) -> dict[str, str]:
        if pool is None:
            response.status_code = 503
            return {"status": "unavailable"}
        try:
            probe = await pool.fetchval("SELECT 1")
        except (OSError, database_driver.PostgresError):
            response.status_code = 503
            return {"status": "unavailable"}
        if probe != 1:
            response.status_code = 503
            return {"status": "unavailable"}
        return {"status": "ready"}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/api/v1/assets", dependencies=[Depends(require_internal_token)], response_model=Asset)
    async def create(request: AssetCreate, response: Response) -> Asset:
        derived_id = identity.derive_asset_id(request.identity.model_dump(mode="json"))
        asset = Asset(asset_id=request.asset_id or derived_id, **request.model_dump(exclude={"asset_id"}))
        existing = await retrieve(asset.asset_id)
        if existing is not None:
            if existing.model_dump(mode="json") != asset.model_dump(mode="json"):
                raise HTTPException(status_code=409, detail="asset_id is already bound to a different payload")
            return existing
        if pool is None:
            raise HTTPException(status_code=503, detail="Unavailable")
        await pool.execute("INSERT INTO phase2.assets (asset_id, identity, asset_type, created_at, updated_at) VALUES ($1, $2::jsonb, $3, $4, $5)", asset.asset_id, json.dumps(asset.identity.model_dump(mode="json")), asset.asset_type, asset.created_at, asset.updated_at)
        await pool.executemany("INSERT INTO phase2.aliases (owner_type, owner_id, type, value, valid_from, valid_to, source, confidence) VALUES ('asset', $1, $2, $3, $4, $5, $6, $7)", [(asset.asset_id, alias.type.value, alias.value, alias.valid_from, alias.valid_to, alias.source, round(alias.confidence * 100)) for alias in asset.aliases])
        response.status_code = status.HTTP_201_CREATED
        return asset

    @app.get("/api/v1/assets/{asset_id}", dependencies=[Depends(require_internal_token)], response_model=Asset)
    async def get(asset_id: UUID) -> Asset:
        asset = await retrieve(asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="Asset not found")
        return asset

    @app.get("/api/v1/assets", dependencies=[Depends(require_internal_token)], response_model=list[Asset])
    async def list_assets(alias_type: str | None = Query(default=None), alias_value: str | None = Query(default=None), limit: int = Query(default=100, ge=1), offset: int = Query(default=0, ge=0)) -> list[Asset]:
        if pool is None:
            raise HTTPException(status_code=503, detail="Unavailable")
        if alias_type is not None and alias_value is not None:
            rows = await pool.fetch("SELECT s.asset_id, s.identity, s.asset_type, s.created_at, s.updated_at FROM phase2.assets s JOIN phase2.aliases a ON a.owner_id = s.asset_id WHERE a.owner_type = 'asset' AND a.type = $1 AND a.value = $2 AND a.valid_from <= now() AND (a.valid_to IS NULL OR a.valid_to > now()) ORDER BY a.confidence DESC, a.valid_from DESC", alias_type, alias_value)
        else:
            rows = await pool.fetch("SELECT asset_id, identity, asset_type, created_at, updated_at FROM phase2.assets ORDER BY created_at, asset_id LIMIT $1 OFFSET $2", limit, offset)
        return [asset for row in rows if (asset := await retrieve(UUID(str(row["asset_id"])))) is not None]

    return app
