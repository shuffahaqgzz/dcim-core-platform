# Todo 9 evidence — live NOC read model and Phase 3 scaffolding

Date: 2026-08-04  
Baseline commit tested: `8ef2691` plus the Todo 9 working-tree change  
Classification: dashboard/API and foundation scaffolding  
Boundary: synthetic Development evidence only; no Production connection, least-privilege claim, milestone security acceptance, or Production-readiness claim.

## Acceptance results

| Command or check | Exit/result |
| --- | --- |
| `make phase3-deps` | `0`; all seven exact pins already present |
| `make phase3-test` | `0`; 10 tests passed |
| `make phase0-check` | `0`; 267 tests passed and all Phase 0 gates passed |
| `python3 -m compileall -q services` | `0` |
| `make public-safety` | `0`; 308 files scanned |
| `test $(find services/api/src -name '*.py' -exec cat {} + \| wc -l) -le 500` | `0`; 230 lines |
| `test ! -e tests/phase3/__init__.py` | `0` |
| no `.sql` files under `services/` | `0` |
| dependency inventory contains `asyncpg==0.30.0` exactly once | `0`; count `1` |

`phase3-deps` installed or confirmed these exact pins: `pydantic==2.9.2`,
`fastapi==0.115.0`, `uvicorn[standard]==0.30.6`, `asyncpg==0.30.0`,
`httpx==0.28.1`, `prometheus-client==0.26.0`, and
`confluent-kafka==2.15.0`.

## ADR-0007 acceptance greps

All required expressions were present; the command exited `0`.

| Expression | Count |
| --- | ---: |
| `dcim_assets_rw` | 1 |
| `dcim_cmdb_rw` | 1 |
| `dcim_api_ro` | 1 |
| `dcim_analytics_ro` | 1 |
| `dcim_workflow_rw` | 1 |
| `deny-by-default` | 3 |
| `/api/*` | 1 |
| `/health` | 2 |
| `/ready` | 1 |
| `/metrics` | 2 |
| `static shared internal token` | 1 |
| `TTL/rotation/revocation` | 2 |
| `audit attribution` | 3 |
| `horizontal escalation` | 1 |
| `vertical escalation` | 2 |
| `NOT least privilege` | 1 |
| `NOT milestone security acceptance` | 1 |

## Live manual QA

The exact factory command was started on port `18090` with no database
configuration. With `DCIM_AUTH_REQUIRED=false`, `GET /health` returned `200`.
The process was stopped successfully.

A mode-`0600` temporary file containing the synthetic fixture token `tok123`
was then created at `/tmp/dcim-todo9-tok`. The factory was restarted with
`DCIM_AUTH_REQUIRED=true` and `INTERNAL_API_TOKEN_FILE` pointing to that file.

| Request | HTTP code |
| --- | ---: |
| `GET /api/v1/dashboard/noc-cards` without token header | 403 |
| same request with the matching synthetic header | 503 |
| `GET /health` without token header | 200 |

The authenticated API result is intentionally non-403 and reports read-model
unavailability because no database was configured for this bounded QA run.

## Failure mutation and restoration

The unauthenticated protected request is the required failure mutation and
returned `403`, proving deny-by-default behavior. Both Uvicorn processes were
terminated after their checks, and `/tmp/dcim-todo9-tok` was removed. No live
credential, endpoint, payload, topology, or operational log was recorded.

## Limitations

This evidence proves the bounded Development shared-token boundary, health
exemption, read-only SQL seam, and dependency scaffolding. It does not prove
token TTL, rotation, revocation, actor attribution, horizontal/vertical
authorization controls, full database integration, HA, SLA, hardening,
Staging entry, or Production readiness. Open conditions remain unchanged.
