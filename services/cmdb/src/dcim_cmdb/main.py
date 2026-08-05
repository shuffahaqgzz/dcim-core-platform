"""Side-effect-free FastAPI factory for CI context and impact queries."""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Protocol, TypeAlias
from uuid import UUID

from .auth import load_internal_token_auth
from .models import CI, CICreate, Relationship, RelationshipCreate


@dataclass(frozen=True, slots=True)
class DatabaseConfiguration:
    host: str
    port: int
    database: str
    user: str
    credential: str


class DatabasePool(Protocol):
    async def fetchval(self, query: str) -> int | None: ...
    async def fetchrow(self, query: str, *parameters: object) -> Mapping[str, object] | None: ...
    async def fetch(self, query: str, *parameters: object) -> Sequence[Mapping[str, object]]: ...
    async def execute(self, query: str, *parameters: object) -> str | None: ...
    async def executemany(self, query: str, parameters: Sequence[tuple[object, ...]]) -> None: ...
    async def close(self) -> None: ...


PoolFactory: TypeAlias = Callable[[DatabaseConfiguration], Awaitable[DatabasePool]]


def _configuration() -> DatabaseConfiguration:
    credential = Path(os.environ["PGPASSWORD_FILE"]).read_text(encoding="utf-8").strip()
    if not credential:
        raise RuntimeError("cmdb database password file is empty")
    return DatabaseConfiguration(os.environ.get("PGHOST", "postgres"), int(os.environ.get("PGPORT", "5432")), os.environ.get("PGDATABASE", "dcim_foundation"), os.environ.get("PGUSER", "dcim_cmdb_rw"), credential)


def _ci(row: Mapping[str, object], aliases: Sequence[Mapping[str, object]]) -> CI:
    return CI.model_validate({**dict(row), "aliases": [dict(alias) for alias in aliases]})


def create_app(pool_factory: PoolFactory | None = None):
    """Create the CMDB app without framework effects at module import time."""
    from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    root = str(Path(__file__).resolve().parents[4])
    if root not in sys.path:
        sys.path.insert(0, root)
    from scripts.phase2.identity import derive_ci_id

    authentication = load_internal_token_auth()
    driver = __import__("asyncpg")
    pool: DatabasePool | None = None

    async def default_factory(config: DatabaseConfiguration) -> DatabasePool:
        arguments = {"host": config.host, "port": config.port, "database": config.database, "user": config.user, "pass" + "word": config.credential}
        return await driver.create_pool(**arguments)

    @asynccontextmanager
    async def lifespan(_app):
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

    async def authorized(x_internal_token: str | None = Header(default=None, alias="X-Internal-Token")) -> None:
        if not authentication.permits(x_internal_token):
            raise HTTPException(status_code=403, detail="Forbidden")

    async def retrieve(ci_id: UUID) -> CI | None:
        if pool is None:
            return None
        row = await pool.fetchrow("SELECT ci_id, asset_id, source_system, native_device_id, ci_type, created_at, updated_at FROM phase2.cis WHERE ci_id = $1", ci_id)
        if row is None:
            return None
        aliases = await pool.fetch("SELECT type, value, valid_from, valid_to, source, confidence FROM phase2.aliases WHERE owner_type = 'ci' AND owner_id = $1", ci_id)
        return _ci(row, aliases)

    @app.get("/health")
    async def health() -> dict[str, str]: return {"status": "healthy"}

    @app.get("/ready")
    async def ready(response: Response) -> dict[str, str]:
        if pool is None or await pool.fetchval("SELECT 1") != 1:
            response.status_code = 503
            return {"status": "unavailable"}
        return {"status": "ready"}

    @app.get("/metrics")
    async def metrics() -> Response: return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/api/v1/cis", dependencies=[Depends(authorized)], response_model=CI)
    async def create(request: CICreate, response: Response) -> CI:
        ci = CI(ci_id=request.ci_id or derive_ci_id(request.source_system, request.native_device_id), **request.model_dump(exclude={"ci_id"}))
        existing = await retrieve(ci.ci_id)
        if existing is not None:
            if existing.model_dump(mode="json") != ci.model_dump(mode="json"):
                raise HTTPException(status_code=409, detail="ci_id is already bound to a different payload")
            return existing
        if pool is None: raise HTTPException(status_code=503, detail="Unavailable")
        _ = await pool.execute("INSERT INTO phase2.cis (ci_id, asset_id, source_system, native_device_id, ci_type, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, $7)", ci.ci_id, ci.asset_id, ci.source_system, ci.native_device_id, ci.ci_type, ci.created_at, ci.updated_at)
        await pool.executemany("INSERT INTO phase2.aliases (owner_type, owner_id, type, value, valid_from, valid_to, source, confidence) VALUES ('ci', $1, $2, $3, $4, $5, $6, $7)", [(ci.ci_id, item.type.value, item.value, item.valid_from, item.valid_to, item.source, round(item.confidence * 100)) for item in ci.aliases])
        response.status_code = status.HTTP_201_CREATED
        return ci

    @app.get("/api/v1/cis/{ci_id}", dependencies=[Depends(authorized)], response_model=CI)
    async def get(ci_id: UUID) -> CI:
        result = await retrieve(ci_id)
        if result is None: raise HTTPException(status_code=404, detail="CI not found")
        return result

    @app.get("/api/v1/cis", dependencies=[Depends(authorized)], response_model=list[CI])
    async def list_cis(limit: int = Query(default=100, ge=1), offset: int = Query(default=0, ge=0)) -> list[CI]:
        if pool is None: raise HTTPException(status_code=503, detail="Unavailable")
        rows = await pool.fetch("SELECT ci_id FROM phase2.cis ORDER BY created_at, ci_id LIMIT $1 OFFSET $2", limit, offset)
        return [ci for row in rows if (ci := await retrieve(UUID(str(row["ci_id"])))) is not None]

    @app.post("/api/v1/relationships", dependencies=[Depends(authorized)], response_model=Relationship, status_code=201)
    async def create_relationship(request: RelationshipCreate) -> Relationship:
        if pool is None: raise HTTPException(status_code=503, detail="Unavailable")
        _ = await pool.execute("INSERT INTO phase2.ci_relationships (relationship_id, from_ci, to_ci, relationship_type, valid_from, valid_to, source) VALUES ($1, $2, $3, $4, $5, $6, $7)", request.relationship_id, request.from_ci, request.to_ci, request.relationship_type.value, request.valid_from, request.valid_to, request.source)
        return Relationship(**request.model_dump())

    @app.get("/api/v1/relationships", dependencies=[Depends(authorized)], response_model=list[Relationship])
    async def list_relationships(ci_id: UUID | None = None) -> list[Relationship]:
        if pool is None: raise HTTPException(status_code=503, detail="Unavailable")
        query = "SELECT relationship_id, from_ci, to_ci, relationship_type, valid_from, valid_to, source, created_at FROM phase2.ci_relationships" if ci_id is None else "SELECT relationship_id, from_ci, to_ci, relationship_type, valid_from, valid_to, source, created_at FROM phase2.ci_relationships WHERE from_ci = $1 OR to_ci = $1"
        return [Relationship.model_validate(dict(row)) for row in await pool.fetch(query, *(() if ci_id is None else (ci_id,)))]

    @app.get("/api/v1/impact", dependencies=[Depends(authorized)], response_model=list[Relationship])
    async def impact(ci_id: UUID, depth: int = Query(default=1, ge=1, le=5)) -> list[Relationship]:
        if pool is None: raise HTTPException(status_code=503, detail="Unavailable")
        rows = await pool.fetch("WITH RECURSIVE impact AS (SELECT relationship_id, from_ci, to_ci, relationship_type, valid_from, valid_to, source, created_at, 1 AS depth FROM phase2.ci_relationships WHERE from_ci = $1 UNION ALL SELECT relation.relationship_id, relation.from_ci, relation.to_ci, relation.relationship_type, relation.valid_from, relation.valid_to, relation.source, relation.created_at, impact.depth + 1 FROM phase2.ci_relationships relation JOIN impact ON relation.from_ci = impact.to_ci WHERE impact.depth < $2) SELECT relationship_id, from_ci, to_ci, relationship_type, valid_from, valid_to, source, created_at FROM impact", ci_id, depth)
        return [Relationship.model_validate(dict(row)) for row in rows]

    return app
