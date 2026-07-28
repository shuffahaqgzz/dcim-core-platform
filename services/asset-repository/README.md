# Asset Repository Service

Owns stable physical/logical asset identity, lifecycle state, aliases, and public APIs. Native UUID is preferred; manufacturer plus serial is the fallback. IP is never the primary key.

Owning ADR: ADR-0024 (Python 3.12 + FastAPI + Pydantic v2). OD-01 custom PostgreSQL direction in ADR-0007 provides the persistence context.

Planned API group: `/api/v1/assets` (CRUD, bulk import, search).

Planned layout:
- `pyproject.toml`
- `src/dcim_asset_repository/`
- `tests/`

Local commands:
- `make phase0-check` — gate only; nothing is installed or runnable in Phase 0.

No source connection, no credentials, no runtime state in Phase 0.
