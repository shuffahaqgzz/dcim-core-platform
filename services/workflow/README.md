# Workflow Service

Owns notifications, ticket drafts, approval simulations, and append-only audit entries.

OD-02 is resolved via ADR-0016: TraceCat + Temporal for durable/SOAR security automation; n8n is retained only for non-destructive operational workflows. Execution preconditions and the dry-run default are defined in ADR-0025. Stack reaffirmed by ADR-0024 (Python 3.12 + FastAPI + Pydantic v2).

API group: `/api/v1/workflows/drafts` supports draft creation, retrieval, listing,
and one terminal approval/rejection simulation. The service has no execute route.

## Safety conformance

ADR-0005 and ADR-0025 constrain this service to advisory drafts and simulation.
It contains no shell/process, socket, outbound HTTP, infrastructure write, or
privileged SQL capability. Simulation only updates the local draft status and
appends its audit entry; it cannot trigger an external action. Any future
execution proposal remains gated behind the separately accepted Phase 6 safety
layer and all five ADR-0025 preconditions.

Planned layout:
- `pyproject.toml`
- `src/dcim_workflow/`
- `tests/`

Local commands:
- `make phase3-test`
- `make phase0-check`

Persistence uses only the `dcim_workflow_rw` role and `phase2.workflow_drafts`.
