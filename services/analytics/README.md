# Analytics Service

Owns transparent Development analytics for health, capacity, freshness, completeness, and quality. Every output must link to source lineage and measurement assumptions; no unsupported AI/Production claim.

Owning ADR: ADR-0024 (Python 3.12 + FastAPI + Pydantic v2).

Planned API group: `/api/v1/analytics` (anomaly, predictions, rca, capacity, energy, models).

Planned layout:
- `pyproject.toml`
- `src/dcim_analytics/`
- `tests/`

Local commands:
- `make phase0-check` — gate only; nothing is installed or runnable in Phase 0.

No source connection, no credentials, no runtime state in Phase 0.
