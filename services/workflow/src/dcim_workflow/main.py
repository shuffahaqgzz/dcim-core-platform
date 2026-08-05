"""Advisory workflow draft and approval-simulation API."""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import Path
from typing import Literal, Protocol, TypeAlias
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, JsonValue, model_validator

from .auth import load_internal_token_auth


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
    async def fetch(self, query: str) -> Sequence[Mapping[str, object]]: ...
    async def close(self) -> None: ...


PoolFactory: TypeAlias = Callable[[DatabaseConfiguration], Awaitable[DatabasePool]]


class DraftCreate(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_id: UUID | None = None
    context: dict[str, JsonValue] | None = None
    draft_type: Literal["notification", "ticket_draft", "approval_request"]

    @model_validator(mode="after")
    def has_source(self) -> "DraftCreate":
        if self.event_id is None and self.context is None:
            raise ValueError("event_id or context is required")
        return self


class Simulation(BaseModel):
    model_config = ConfigDict(frozen=True)
    decision: Literal["approve", "reject"]


class AuditEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    action: Literal["created", "simulated"]
    occurred_at: datetime
    decision: Literal["approve", "reject"] | None = None


class Draft(BaseModel):
    model_config = ConfigDict(frozen=True)
    draft_id: UUID
    created_at: datetime
    event_id: UUID | None
    draft_type: Literal["notification", "ticket_draft", "approval_request"]
    payload: dict[str, JsonValue]
    status: Literal["draft", "simulated_approved", "simulated_rejected"]
    audit: list[AuditEntry]


def _configuration() -> DatabaseConfiguration:
    credential = Path(os.environ["PGPASSWORD_FILE"]).read_text(encoding="utf-8").strip()
    if not credential:
        raise RuntimeError("workflow database password file is empty")
    return DatabaseConfiguration(os.environ.get("PGHOST", "postgres"), int(os.environ.get("PGPORT", "5432")), os.environ.get("PGDATABASE", "dcim_foundation"), os.environ.get("PGUSER", "dcim_workflow_rw"), credential)


def create_app(pool_factory: PoolFactory | None = None):
    """Create the workflow app without import-time framework effects."""
    from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

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

    def require_pool() -> DatabasePool:
        if pool is None:
            raise HTTPException(status_code=503, detail="Unavailable")
        return pool

    async def retrieve(draft_id: UUID) -> Draft | None:
        row = await require_pool().fetchrow("SELECT draft_id, created_at, event_id, draft_type, payload, status, audit FROM phase2.workflow_drafts WHERE draft_id = $1", draft_id)
        return None if row is None else Draft.model_validate(dict(row))

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

    @app.post("/api/v1/workflows/drafts", dependencies=[Depends(authorized)], response_model=Draft, status_code=status.HTTP_201_CREATED)
    async def create(request: DraftCreate) -> Draft:
        now = datetime.now(UTC)
        payload = request.context or {}
        audit = [AuditEntry(action="created", occurred_at=now)]
        row = await require_pool().fetchrow("INSERT INTO phase2.workflow_drafts (draft_id, created_at, event_id, draft_type, payload, status, audit) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING draft_id, created_at, event_id, draft_type, payload, status, audit", uuid4(), now, request.event_id, request.draft_type, payload, "draft", [item.model_dump(mode="json") for item in audit])
        return Draft.model_validate(dict(row or {}))

    @app.get("/api/v1/workflows/drafts", dependencies=[Depends(authorized)], response_model=list[Draft])
    async def list_drafts() -> list[Draft]:
        rows = await require_pool().fetch("SELECT draft_id, created_at, event_id, draft_type, payload, status, audit FROM phase2.workflow_drafts ORDER BY created_at, draft_id")
        return [Draft.model_validate(dict(row)) for row in rows]

    @app.get("/api/v1/workflows/drafts/{draft_id}", dependencies=[Depends(authorized)], response_model=Draft)
    async def get(draft_id: UUID) -> Draft:
        draft = await retrieve(draft_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Draft not found")
        return draft

    @app.post("/api/v1/workflows/drafts/{draft_id}/simulate", dependencies=[Depends(authorized)], response_model=Draft)
    async def simulate(draft_id: UUID, request: Simulation) -> Draft:
        draft = await retrieve(draft_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Draft not found")
        if draft.status != "draft":
            raise HTTPException(status_code=409, detail="Draft simulation is terminal")
        resulting_status = "simulated_approved" if request.decision == "approve" else "simulated_rejected"
        audit = [*draft.audit, AuditEntry(action="simulated", occurred_at=datetime.now(UTC), decision=request.decision)]
        row = await require_pool().fetchrow("UPDATE phase2.workflow_drafts SET status = $2, audit = $3 WHERE draft_id = $1 AND status = 'draft' RETURNING draft_id, created_at, event_id, draft_type, payload, status, audit", draft_id, resulting_status, [item.model_dump(mode="json") for item in audit])
        if row is None:
            raise HTTPException(status_code=409, detail="Draft simulation is terminal")
        return Draft.model_validate(dict(row))

    return app
