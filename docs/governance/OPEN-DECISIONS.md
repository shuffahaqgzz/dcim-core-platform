# Open Architecture and Product Decisions

Do not silently choose or encode defaults for these items. Create a proposed ADR and obtain an explicit owner decision.

| ID | Decision | Candidate directions | Required evidence | Status |
|---|---|---|---|---|
| OD-01 | CMDB implementation | NetBox integration, custom service/model, other | relationship model fit, APIs, migration, ownership, licenses, resource profile | ACCEPTED 2026-07-28 — [ADR-0007](../adr/0007-cmdb-implementation-for-development.md) |
| OD-02 | Workflow engine | Temporal, n8n, split use | durability/idempotency, approval model, audit, operator UX, license, VM footprint | ACCEPTED 2026-07-27 — [ADR-0016](../adr/0016-workflow-engine-split.md) |
| OD-03 | Frontend framework | React, Vue | NOC UX spike, maintainability, test tooling, team/handover fit, dependency risk | ACCEPTED 2026-07-27 — [ADR-0017](../adr/0017-react-noc-dashboard-frontend.md) |
| OD-04 | Search platform | Elasticsearch, OpenSearch | license, resource profile, APIs, backup/restore, lifecycle and migration | ACCEPTED 2026-07-27 — [ADR-0018](../adr/0018-elasticsearch-search-platform.md) |
| OD-05 | Hermes model/inference | local model/server candidates | GPU fit, latency, grounding, license/provenance, offline operation, safety eval | DEFERRED — before any Hermes shadow work; GPU fit test as re-entry trigger |
| OD-06 | Repository license | permissive, copyleft, source-available, closed/no license | ownership, dependency compatibility, contribution and commercial intent | ACCEPTED 2026-07-27 — [ADR-0019](../adr/0019-apache-2-0-repository-license.md) (Apache-2.0) |
| OD-07 | Long-term service language/framework baseline | to be proposed after bounded spike | operability, type safety, libraries, performance, developer/handover fit | ACCEPTED 2026-07-28 — [ADR-0024](../adr/0024-python-fastapi-service-language-baseline.md) |

## Decision process

1. Open an `[ADR]` issue.
2. Time-box a synthetic benchmark or spike when evidence is missing.
3. Add a `Proposed` ADR under `docs/adr/`.
4. Owner records `Accepted` or `Rejected` with date and rationale.
5. Implementation follows in a separate PR unless the change is documentation-only.
6. Superseded decisions remain in history and link to the replacement.
