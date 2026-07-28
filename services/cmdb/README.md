# CMDB Service

Owns configuration-item identity, relationships, history, and context APIs.

OD-01 is resolved via ADR-0007: custom PostgreSQL CMDB service for Phase 1–2; iTop and NetBox are read-only discovery sources behind a canonical adapter. Stack reaffirmed by ADR-0024 (Python 3.12 + FastAPI + Pydantic v2).

Planned API group: `/api/v1/cis` (CRUD, topology, impact).

Planned layout:
- `pyproject.toml`
- `src/dcim_cmdb/`
- `tests/`

Local commands:
- `make phase0-check` — gate only; nothing is installed or runnable in Phase 0.

No source connection, no credentials, no runtime state in Phase 0.
