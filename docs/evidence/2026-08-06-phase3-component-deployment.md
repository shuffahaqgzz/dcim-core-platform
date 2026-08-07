# Phase 3 component deployment evidence

Date: `2026-08-06` (UTC)

## Scope note

This record covers the first five-service component slice only. All cited
results use synthetic fixtures and the local Development runtime; no live
connector or external target is involved. Phase 3 remains in progress and is
limited to this first component slice, not a promotion or release assertion.

Owner override for Todo 21: this task updates this evidence document and
`ROADMAP.md` only. The plan's requested `PLAN-DISPOSITIONS.md` row is explicitly
out of scope, and `README.md` is not changed.

## Service inventory

Every service below is internal to the Compose network: each binds port 8000 in
its container, has no published host port, and has the same `0.5` CPU / `512M`
limit. The Compose contract and no-host-port assertion are recorded in
[the five-service Compose test](../../tests/phase3/test_compose_core.py) and
[the Compose definition](../../deploy/compose/dev-build/compose.yaml).

| Service | Actual endpoints | Capability profile (Compose) | Database role |
| --- | --- | --- | --- |
| Asset Repository | `/health`, `/ready`, `/metrics`, `POST /api/v1/assets`, `GET /api/v1/assets`, `GET /api/v1/assets/{asset_id}` ([route source](../../services/asset-repository/src/dcim_asset_repository/main.py)) | `core` ([Compose block](../../deploy/compose/dev-build/compose.yaml)) | `dcim_assets_rw` ([Compose block](../../deploy/compose/dev-build/compose.yaml)) |
| CMDB | `/health`, `/ready`, `/metrics`, `POST`/`GET /api/v1/cis`, `GET /api/v1/cis/{ci_id}`, `POST`/`GET /api/v1/relationships`, `GET /api/v1/impact` ([route source](../../services/cmdb/src/dcim_cmdb/main.py)) | `core` ([Compose block](../../deploy/compose/dev-build/compose.yaml)) | `dcim_cmdb_rw` ([Compose block](../../deploy/compose/dev-build/compose.yaml)) |
| API gateway | `/health`, `/ready`, `/metrics`, `/api/v1/dashboard/noc-cards`, `/api/v1/dashboard/summary`, and authenticated asset/CI proxy routes ([route source](../../services/api/src/dcim_api/main.py)) | `dashboard` ([Compose block](../../deploy/compose/dev-build/compose.yaml)) | `dcim_api_ro` ([Compose block](../../deploy/compose/dev-build/compose.yaml)) |
| Analytics | `/health`, `/ready`, `/metrics`, `/api/v1/analytics/health`, `/api/v1/analytics/freshness`, `/api/v1/analytics/capacity`, `/api/v1/analytics/quality` ([route source](../../services/analytics/src/dcim_analytics/main.py)) | `core` ([Compose block](../../deploy/compose/dev-build/compose.yaml)) | `dcim_analytics_ro` ([Compose block](../../deploy/compose/dev-build/compose.yaml)) |
| Workflow | `/health`, `/ready`, `/metrics`, `POST`/`GET /api/v1/workflows/drafts`, `GET /api/v1/workflows/drafts/{draft_id}`, `POST /api/v1/workflows/drafts/{draft_id}/simulate` ([route source](../../services/workflow/src/dcim_workflow/main.py)) | `workflow` ([Compose block](../../deploy/compose/dev-build/compose.yaml)) | `dcim_workflow_rw` ([Compose block](../../deploy/compose/dev-build/compose.yaml)) |

## Smoke and end-to-end receipts

- [Todo 18 smoke evidence](../../.omo/evidence/phase2-closure-phase3-start/task-18.md)
  records the Docker-host `make service-smoke` result: five health and `/ready`
  checks, non-empty metrics, and five unauthenticated API denials.
- [Todo 19 end-to-end evidence](../../.omo/evidence/phase2-closure-phase3-start/task-19.md)
  records Docker-host `make service-check` and `make phase2-check` results,
  including the synthetic topic-to-dashboard flow, zero-silent-loss checks,
  bounded latency assertion, failure mutation, restoration, and cleanup.

These are prior Docker-host receipts; this documentation task runs only the
local documentation gates named below.

## Contract parity

- Asset Repository: a synthetic full-field payload crosses
  [`asset.schema.json`](../../schemas/asset.schema.json) into the
  [`Asset`/`Alias` model test](../../tests/phase3/test_asset_repository.py),
  which asserts that the serialized model field set equals the schema's
  required field set and validates alias confidence. [Todo 12](../../.omo/evidence/phase2-closure-phase3-start/task-12.md)
  records this Pydantic model-to-schema boundary.
- CMDB: the synthetic canonical CI payload is accepted by the typed
  [`CI` model test](../../tests/phase3/test_cmdb.py), whose fields correspond
  to [`ci.schema.json`](../../schemas/ci.schema.json); the same test rejects an
  invalid relationship type through the typed model. [Todo 13](../../.omo/evidence/phase2-closure-phase3-start/task-13.md)
  records the bounded CI/relationship contract result.

## Negative-test inventory

- [Workflow safety test](../../tests/phase3/test_workflow_safety.py): AST scan
  rejects execution and network-capability imports/calls in the workflow
  package.
- [Analytics test](../../tests/phase3/test_analytics.py): AST scan rejects
  mutating SQL terms; protected analytics calls deny missing and wrong tokens.
- [Redfish adapter test](../../tests/phase2/test_redfish_adapter_readonly.py)
  and [SNMP adapter test](../../tests/phase2/test_snmpv3_adapter_readonly.py):
  AST checks reject write/control surfaces in the synthetic read-only adapters.
- [Compose contract test](../../tests/phase3/test_compose_core.py) and
  [smoke test](../../tests/phase3/test_smoke.py): each of the five service
  blocks is checked for no `ports:` entry; the smoke contract requires 403 for
  unauthenticated API probes.
- [Todo 18 smoke receipt](../../.omo/evidence/phase2-closure-phase3-start/task-18.md)
  and [Todo 19 E2E receipt](../../.omo/evidence/phase2-closure-phase3-start/task-19.md)
  provide the Docker-host five-of-five authentication-denial observations.

## Owner-disposition verification

The bounded first-slice closure was reverified on **2026-08-07** against
`main` commit `423b063bf960850c1c1b9624a84305d34e071a7f`:

| Gate | Command | Result |
|---|---|---|
| Phase 3 unit tests | `make phase3-test` | 64 tests OK |
| Service smoke | `make service-smoke` | services=5/5, auth-denials=5/5 |
| Bounded E2E | `make e2e` | zero-loss=True, dashboard=True, p95-ms≈1.6 s |
| Service check | `make service-check` | PASS |

Evidence artifacts:

- `dev-build/evidence/service-smoke/evidence.json`
- `dev-build/evidence/e2e/evidence-e2e.json`

These are Docker-host receipts using synthetic fixtures only; no live connector
or Production target was involved.

## Remaining scope and bounded status

The larger P3-T1 through P3-T7 scope remains only partly represented by this
slice: full reference-design CRUD parity, reconciliation, Redis enrichment,
and deeper audit-trail work remain. The implementation plan's full task list
is [P3-T1–P3-T7](../research/IMPLEMENTATION-PLAN.md). Pending owner and
security evidence includes the actor/role boundary, token lifecycle,
cross-service grants, egress/disable controls, recovery proof, and
second-operator handover described by [ADR-0007](../adr/0007-cmdb-implementation-for-development.md).

`STAGING-HANDOVER.md` is deliberately unchanged; its own status remains the
authoritative record. This document does not alter any condition, handover, or
release decision.
