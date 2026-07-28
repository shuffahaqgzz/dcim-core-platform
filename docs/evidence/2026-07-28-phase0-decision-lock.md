# Phase 0 Decision Lock — PASS with 1 pre-existing bare-clone test error

Date: 2026-07-28  
Commit: `872df38a4ede87d129533965b28ca335672916bc`  
Issue/PR: Task 17 of `docs/research/PHASE0-PLAN.md`; PR assembly is Task 18 and was not performed in this session. Parent context: issue #9.

Scope: Phase 0 decision lock — ADRs, governance registers, safety policy, service scaffolds, and research-doc sync. No runtime code, no connected source, no Docker operations.

Acceptance criterion: all decision-lock artifacts present in the working tree; `make phase0-check` runs to completion with each gate result recorded; `make public-safety` and `make markdown-links` PASS; new governance tests (`test_decision_records`, `test_service_scaffolds`, `test_automation_safety_boundary`) PASS; Docker-dependent gates explicitly excluded from this sandbox session.

## Environment note

This clone has `core.bare=true`. All git-dependent gates were run with the override:

```text
GIT_DIR=/home/infra/dcim-core-platform/.git \
GIT_WORK_TREE=/home/infra/dcim-core-platform \
make phase0-check
```

Without the override, `git ls-files` exits 128 and `make markdown-links` cannot run. That is a limitation of this sandbox, not a repo defect; CI runs in a normal clone.

## Gate results

| Gate | Command | Result |
|---|---|---|
| Compile | `make compile` | PASS — no output |
| Public safety | `make public-safety` | PASS — 721 files scanned |
| JSON validation | `make validate-json` | PASS — 212 files / 6 event fixtures |
| Fixture provenance | `make validate-fixtures` | PASS — 9 mandatory fixtures |
| Markdown links | `make markdown-links` | PASS — 189 links |
| Unit/adversarial tests | `make test` | 259 tests, 258 pass; 1 pre-existing error in `test_phase2_evidence_receipts.Phase2EvidenceReceiptTests.test_generate_without_approved_attestation_fails_closed` raising `NO-GO_HEAD_DRIFT` ("cannot capture Git subject state") because the receipt script's own git invocation cannot diff in this bare-configured clone. Baseline without the env override shows 5 errors in the same module; this is not a regression. New tests added by this change (`test_decision_records` 6, `test_service_scaffolds` 7, `test_automation_safety_boundary` 6) all PASS. |

## ADRs accepted / amended

| ADR | Change | Decision reference |
|---|---|---|
| [ADR-0007](../adr/0007-cmdb-implementation-for-development.md) | Status `Accepted` + 2026-07-28 addendum; custom PostgreSQL CMDB for Phase 1–2; iTop/NetBox read-only discovery sources | OD-01 |
| [ADR-0016](../adr/0016-workflow-engine-split.md) | 2026-07-28 addendum; TraceCat + Temporal for SOAR; n8n non-destructive operational only | PRD Q3 |
| [ADR-0024](../adr/0024-python-fastapi-service-language-baseline.md) | New, `Accepted` 2026-07-28; Python 3.12 + FastAPI + Pydantic v2 services; TypeScript + React + Vite frontend | OD-07 |
| [ADR-0025](../adr/0025-automation-execution-preconditions.md) | New, `Accepted` 2026-07-28; dry-run/recommendation default; five conjunctive execution preconditions | PRD Q4 |
| [ADR-0026](../adr/0026-program-technology-version-baseline.md) | New, `Accepted` 2026-07-28; ES 9.x, PostgreSQL 17.x target / 16 floor, Kafka 3.x/4.x, Redis 7 | PRD Q8 |
| [ADR-0027](../adr/0027-private-llm-serving-baseline.md) | New, `Accepted` 2026-07-28; private LLM on 2×RTX A5000 24 GB with managed-API fallback abstraction | PRD Q7 |

## Registers updated

- [`docs/governance/OPEN-DECISIONS.md`](../governance/OPEN-DECISIONS.md): OD-01 and OD-07 marked `ACCEPTED 2026-07-28` with ADR links.
- [`docs/governance/CONDITIONS-REGISTER.md`](../governance/CONDITIONS-REGISTER.md): owner-direction section for 2026-07-28 added; no C-01..C-10 status changed by this record.
- [`docs/adr/README.md`](../adr/README.md): crosswalk updated with ADR-0024–0027.

## Gates not run in this session

| Gate | Reason |
|---|---|
| `make preflight` | Docker-dependent; CI / milestone-acceptance venue per [`AGENTS.md`](../../AGENTS.md) §4 |
| All `foundation-*` targets (`foundation-images-qualify`, `foundation-supply-chain`, `foundation-smoke`, `foundation-recovery`, etc.) | Docker-dependent; same CI / milestone-acceptance venue |

## Boundary statements

- Synthetic data only; no live credentials, endpoints, source identities, topology, payloads, logs, captures, dumps, or certificates were recorded or committed.
- No Staging or Production approval is claimed. Phase 0 remains Development-entry readiness.
- [OD-05](../governance/OPEN-DECISIONS.md) (Hermes model/inference) stays `DEFERRED`.
- C-01..C-10 statuses are unchanged by this record; owner closure still required per [`CONDITIONS-REGISTER.md`](../governance/CONDITIONS-REGISTER.md).

## Non-claims

This is not evidence for connected-source integration, Staging entry, Production readiness, HA, SLA, security accreditation, infrastructure write/control paths, or full `make preflight` / foundation-lifecycle acceptance. Docker-dependent gates and independent review are out of scope for this sandbox session and remain pending PR assembly.
