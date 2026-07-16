# Open Architecture and Product Decisions

Do not silently choose or encode defaults for these items. Create a proposed ADR and obtain an explicit owner decision.

| ID | Decision | Candidate directions | Required evidence | Status |
|---|---|---|---|---|
| OD-01 | CMDB implementation | NetBox integration, custom service/model, other | relationship model fit, APIs, migration, ownership, licenses, resource profile | OPEN |
| OD-02 | Workflow engine | Temporal, n8n, split use | durability/idempotency, approval model, audit, operator UX, license, VM footprint | OPEN |
| OD-03 | Frontend framework | React, Vue | NOC UX spike, maintainability, test tooling, team/handover fit, dependency risk | OPEN |
| OD-04 | Search platform | Elasticsearch, OpenSearch | license, resource profile, APIs, backup/restore, lifecycle and migration | OPEN |
| OD-05 | Hermes model/inference | local model/server candidates | GPU fit, latency, grounding, license/provenance, offline operation, safety eval | OPEN |
| OD-06 | Repository license | permissive, copyleft, source-available, closed/no license | ownership, dependency compatibility, contribution and commercial intent | OPEN |
| OD-07 | Long-term service language/framework baseline | to be proposed after bounded spike | operability, type safety, libraries, performance, developer/handover fit | OPEN |

## Decision process

1. Open an `[ADR]` issue.
2. Time-box a synthetic benchmark or spike when evidence is missing.
3. Add a `Proposed` ADR under `docs/adr/`.
4. Owner records `Accepted` or `Rejected` with date and rationale.
5. Implementation follows in a separate PR unless the change is documentation-only.
6. Superseded decisions remain in history and link to the replacement.
