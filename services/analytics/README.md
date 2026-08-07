# Analytics Service

Owns transparent Development analytics for health, capacity, freshness, completeness, and quality. Every output links to source lineage and measurement assumptions; no unsupported AI/Production claim.

Owning ADR: ADR-0024 (Python 3.12 + FastAPI + Pydantic v2).

Planned API group: `/api/v1/analytics` (anomaly, predictions, rca, capacity, energy, models).

Implemented pure Development capabilities:

- strict Pydantic incident and lineage contracts;
- deterministic feature-to-domain scoring;
- bounded-window anomaly/drift aggregation and cross-domain correlation;
- topology-aware reactive and forward RCA;
- explicit `unknown` result when active-domain evidence is absent.

These modules are calculation-only. Importing them opens no socket, database,
message bus, file-backed registry, or model runtime. API/runtime activation
remains outside this change.

Local commands:

- `make phase0-check` — repository compatibility and public-safety gate.
- `PYTHONPATH=services/analytics/src:contracts/python .venv/bin/python -m unittest discover -s services/analytics/tests -p 'test_*.py' -v` — service tests after installing the pinned `pyproject.toml` dependencies in an isolated venv.

No source connection, credentials, runtime state, operational endpoint, model
weight, or infrastructure action is included. Topology is a deterministic
Development prior, not observed Production topology. Outputs are advisory and
must not be treated as an automated remediation decision.
