# Workflow Service

Owns notifications, ticket drafts, approval simulations, audit and dry-run actions.

OD-02 is resolved via ADR-0016: TraceCat + Temporal for durable/SOAR security automation; n8n is retained only for non-destructive operational workflows. Execution preconditions and the dry-run default are defined in ADR-0025. Stack reaffirmed by ADR-0024 (Python 3.12 + FastAPI + Pydantic v2).

Planned API group: `/api/v1/workflows` (create, execute, approve, state).

Planned layout:
- `pyproject.toml`
- `src/dcim_workflow/`
- `tests/`

Local commands:
- `make phase0-check` — gate only; nothing is installed or runnable in Phase 0.

No source connection, no credentials, no runtime state in Phase 0.
