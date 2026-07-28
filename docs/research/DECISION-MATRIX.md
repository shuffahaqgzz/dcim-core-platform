# Decision Matrix — DCIM Core Platform Program

**Tanggal:** 2026-07-28
**Purpose:** Single view of every open/accepted/deferred decision and condition across the program, as recommended by `DECISION-LOG-REVIEW.md` §7.5.
**Source of truth:** The authoritative registers (`docs/governance/OPEN-DECISIONS.md`, `docs/governance/CONDITIONS-REGISTER.md`, `docs/research/PRD.md` §7) win on any conflict with this document.

---

## Open Decisions (OD-01 … OD-07)

| ID | Decision | Status | Owning ADR/doc | Owner Role | Deadline | Evidence Pointer |
|---|---|---|---|---|---|---|
| OD-01 | CMDB implementation | ACCEPTED 2026-07-28 | [ADR-0007](../adr/0007-cmdb-implementation-for-development.md) | Architect | 2026-07-31 | `docs/adr/0007-cmdb-implementation-for-development.md` §Addendum 2026-07-28; `docs/governance/OPEN-DECISIONS.md` row OD-01 |
| OD-02 | Workflow engine | ACCEPTED 2026-07-27 | [ADR-0016](../adr/0016-workflow-engine-split.md) | Architect | — | `docs/adr/0016-workflow-engine-split.md`; `docs/governance/OPEN-DECISIONS.md` row OD-02 |
| OD-03 | Frontend framework | ACCEPTED 2026-07-27 | [ADR-0017](../adr/0017-react-noc-dashboard-frontend.md) | Dev | — | `docs/adr/0017-react-noc-dashboard-frontend.md`; `docs/governance/OPEN-DECISIONS.md` row OD-03 |
| OD-04 | Search platform | ACCEPTED 2026-07-27 | [ADR-0018](../adr/0018-elasticsearch-search-platform.md) | Architect | — | `docs/adr/0018-elasticsearch-search-platform.md`; `docs/governance/OPEN-DECISIONS.md` row OD-04 |
| OD-05 | Hermes model/inference | DEFERRED | [ADR-0009](../adr/0009-hermes-read-only-shadow-after-gate.md) | Owner | — | `docs/governance/OPEN-DECISIONS.md` row OD-05; GPU fit test as re-entry trigger |
| OD-06 | Repository license | ACCEPTED 2026-07-27 | [ADR-0019](../adr/0019-apache-2-0-repository-license.md) | Owner | — | `docs/adr/0019-apache-2-0-repository-license.md`; `docs/governance/OPEN-DECISIONS.md` row OD-06 |
| OD-07 | Service language/framework baseline | ACCEPTED 2026-07-28 | [ADR-0024](../adr/0024-python-fastapi-service-language-baseline.md) | Architect | 2026-07-31 | `docs/adr/0024-python-fastapi-service-language-baseline.md`; `docs/governance/OPEN-DECISIONS.md` row OD-07 |

---

## Conditional-GO Register (C-01 … C-10)

| ID | Condition | Status | Owning ADR/doc | Owner Role | Deadline | Evidence Pointer |
|---|---|---|---|---|---|---|
| C-01 | Written authorization and classification for every office/Production source | OPEN | `docs/governance/CONDITIONS-REGISTER.md` C-01 | Owner | — | `docs/governance/CONDITIONS-REGISTER.md` §C-01; `docs/templates/private-source-authorization-register.template.md` |
| C-02 | Public-repository safety baseline | CLOSED 2026-07-20 | `docs/governance/CONDITIONS-REGISTER.md` C-02 | Owner | 2026-07-20 | PR #2, #4, #6; CI run 29716219940; Phase 0 preflight PASS |
| C-03 | Mutable DEV-BUILD separated from pinned DEV-INTEGRATION-RO | OPEN | `docs/governance/CONDITIONS-REGISTER.md` C-03 | Dev | — | `docs/governance/CONDITIONS-REGISTER.md` §C-03; negative-promotion test still needed |
| C-04 | Dedicated read-only credentials and negative write tests | OPEN | `docs/governance/CONDITIONS-REGISTER.md` C-04 | Security Lead | — | `docs/governance/CONDITIONS-REGISTER.md` §C-04; private credential-control record outside Git |
| C-05 | Demo uses synthetic or approved sanitized data only | OPEN | `docs/governance/CONDITIONS-REGISTER.md` C-05 | Dev | — | `docs/governance/CONDITIONS-REGISTER.md` §C-05; executable demo path not yet deployed |
| C-06 | Identity aliases, validity, confidence, and collision tests | OPEN | `docs/governance/CONDITIONS-REGISTER.md` C-06 | Architect | — | `docs/governance/CONDITIONS-REGISTER.md` §C-06; ADR-0020 accepted; collision tests still needed |
| C-07 | Compose resource limits, retention, disk watermarks, and headroom | OPEN | `docs/governance/CONDITIONS-REGISTER.md` C-07 | Dev | — | `docs/governance/CONDITIONS-REGISTER.md` §C-07; ADR-0021 accepted; load/smoke evidence still needed |
| C-08 | Hermes read-only allowlist, egress/memory policy, audit, limits, kill switch | DEFERRED | `docs/governance/CONDITIONS-REGISTER.md` C-08 | Owner | — | `docs/governance/CONDITIONS-REGISTER.md` §C-08; deferred until Hermes re-entry |
| C-09 | Connector polling/source-impact controls | OPEN | `docs/governance/CONDITIONS-REGISTER.md` C-09 | Dev | — | `docs/governance/CONDITIONS-REGISTER.md` §C-09; ADR-0023 accepted; policy schema and stop test still needed |
| C-10 | Cost ceiling before any paid external service | DEFERRED | `docs/governance/CONDITIONS-REGISTER.md` C-10 | Owner | — | `docs/governance/CONDITIONS-REGISTER.md` §C-10; revisit at staging |

---

## PRD Owner-Confirmed Decisions (Q1 … Q10)

| ID | Decision | Status | Owning ADR/doc | Owner Role | Deadline | Evidence Pointer |
|---|---|---|---|---|---|---|
| Q1 | CMDB implementation — custom PostgreSQL for Phase 1–2; iTop/NetBox as read-only discovery sources | Confirmed 2026-07-28 | [ADR-0007](../adr/0007-cmdb-implementation-for-development.md) | Architect | — | `docs/research/PRD.md` §7 Q1; `docs/adr/0007-cmdb-implementation-for-development.md` §Addendum 2026-07-28 |
| Q2 | Service language/framework — Python/FastAPI core; TypeScript/React frontend | Confirmed 2026-07-28 | [ADR-0024](../adr/0024-python-fastapi-service-language-baseline.md) | Architect | — | `docs/research/PRD.md` §7 Q2; `docs/adr/0024-python-fastapi-service-language-baseline.md` |
| Q3 | SOAR platform — TraceCat + Temporal for SOAR; n8n for non-destructive operational workflows | Confirmed 2026-07-28 | [ADR-0016](../adr/0016-workflow-engine-split.md) (addendum) | Architect | — | `docs/research/PRD.md` §7 Q3; `docs/adr/0016-workflow-engine-split.md` §Addendum 2026-07-28 |
| Q4 | Safety boundary — dry-run/recommendation default; execution requires human approval + maintenance window + blast-radius check | Confirmed 2026-07-28 | [ADR-0025](../adr/0025-automation-execution-preconditions.md) + `docs/security/automation-safety-boundary.md` | Security Lead | — | `docs/research/PRD.md` §7 Q4; `docs/adr/0025-automation-execution-preconditions.md`; `docs/security/automation-safety-boundary.md` |
| Q5 | Satellite repo governance — keep repos separate; mandatory CI/CD + contract compatibility gate | Confirmed 2026-07-28 | Cross-repo governance (no ADR) | Tech Lead | — | `docs/research/PRD.md` §7 Q5; owning workstream: satellite CI/CD tickets |
| Q6 | iTop vs custom CMDB — refactor iTop consumer to generic CMDB adapter; iTop as discovery source only | Confirmed 2026-07-28 | Cross-repo follow-up (no ADR in core) | Dev | — | `docs/research/PRD.md` §7 Q6; iTop consumer refactor in satellite repo `DCIM_SRV_DATA_COLLECTION` |
| Q7 | AI model serving — private host on 2×RTX A5000 24 GB VRAM; managed-API fallback via abstraction layer | Confirmed 2026-07-28 | [ADR-0027](../adr/0027-private-llm-serving-baseline.md) | Architect | — | `docs/research/PRD.md` §7 Q7; `docs/adr/0027-private-llm-serving-baseline.md` |
| Q8 | Elasticsearch version — align to ES 9.x across the program | Confirmed 2026-07-28 | [ADR-0026](../adr/0026-program-technology-version-baseline.md) | Architect | — | `docs/research/PRD.md` §7 Q8; `docs/adr/0026-program-technology-version-baseline.md` |
| Q9 | Frontend framework — follow ADR-0017: React + TypeScript + Vite | Confirmed 2026-07-28 | [ADR-0017](../adr/0017-react-noc-dashboard-frontend.md) | Dev | — | `docs/research/PRD.md` §7 Q9; `docs/adr/0017-react-noc-dashboard-frontend.md` |
| Q10 | Phase 2 scope — minimal P1 server health → dashboard end-to-end vertical slice | Confirmed 2026-07-28 | Phase 2 scope freeze (issue/workstream, no ADR) | Tech Lead | — | `docs/research/PRD.md` §7 Q10; GitHub issue #21 |

---

## Notes

- **Status authority:** `OPEN-DECISIONS.md` governs OD statuses. `CONDITIONS-REGISTER.md` governs C statuses. `PRD.md` §7 governs Q statuses. Where this matrix conflicts, the register wins.
- **No condition was closed by the 2026-07-28 decision lock.** C-02 was already closed on 2026-07-20 by the owner. All other conditions remain in their registered state.
- **Deadlines** are recorded only where the authoritative source specifies one. OD-01 and OD-07 carry a 2026-07-31 deadline per `DECISION-LOG-REVIEW.md` §2. All others show `—`.
- **Q5, Q6, and Q10** have no owning ADR in the core repo. Q5 and Q10 are cross-repo workstream items. Q6 is a satellite-repo refactor tracked outside this repository.

---

*Lihat juga: `docs/governance/OPEN-DECISIONS.md`, `docs/governance/CONDITIONS-REGISTER.md`, `docs/research/PRD.md`, `docs/research/DECISION-LOG-REVIEW.md`.*
