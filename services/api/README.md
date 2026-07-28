# API Service

Presents versioned Asset, CI, event, health, freshness, data-quality, workflow-draft, and evidence-safe interfaces to the NOC dashboard and authorized consumers.

Owning ADRs: ADR-0017 (React + TypeScript + Vite frontend context) and ADR-0024 (Python 3.12 + FastAPI + Pydantic v2 backend language baseline). ADR-0024 also defines the gateway role for the dashboard API.

Planned API group: `/api/v1/dashboard` plus gateway routing to Asset, CMDB, Analytics, and Workflow services.

Planned layout:
- `pyproject.toml`
- `src/dcim_api/`
- `tests/`

Local commands:
- `make phase0-check` — gate only; nothing is installed or runnable in Phase 0.

No source connection, no credentials, no runtime state in Phase 0.
