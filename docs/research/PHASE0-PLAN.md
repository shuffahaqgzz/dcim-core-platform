# Phase 0 Decision-Lock Implementation Plan — DCIM Core Platform

## Context

### User Request Summary
Produce a ready-to-execute Phase 0 plan (delivered as `docs/research/PHASE0-PLAN.md` by the executing session) that locks the owner decisions confirmed 2026-07-28 (`docs/research/PRD.md` §7, `docs/research/DECISION-LOG-REVIEW.md`) into ADRs, governance registers, safety policy, service scaffolds, and research-doc sync — so Phase 1 (foundation hardening) and Phase 2 (first vertical slice) start without architecture churn. Governance/docs/scaffold only; no runtime-executing code, no commits, no PRs during planning.

### Decisions being locked
| Ref | Decision | Landing place |
|---|---|---|
| OD-01 / Q1 | Custom PostgreSQL CMDB service for Phase 1–2; iTop/NetBox read-only discovery sources | ADR-0007 → Accepted + addendum |
| OD-07 / Q2 | Python/FastAPI core services; TypeScript/React frontend | new ADR-0024 |
| Q4 | Dry-run/recommendation default; execution needs approval + maintenance window + blast-radius + rollback + audit | new ADR-0025 + `docs/security/automation-safety-boundary.md` |
| Q3 | TraceCat + Temporal for SOAR; n8n non-destructive operational only | ADR-0016 addendum |
| Q8 (+PG 16) | Program version baseline: ES 9.x, PostgreSQL 16 floor, Kafka 3.x/4.x, Redis 7 | new ADR-0026 |
| Q7 | Private LLM serving on 2×RTX A5000 24 GB + managed-API fallback abstraction | new ADR-0027 |
| Q5/Q6/Q9/Q10 | Already covered by ADR-0017 / cross-repo tickets / Phase 2 scope freeze | research doc sync + cross-repo backlog |

### Repo facts verified by reading
- ADRs `0001`–`0023` exist; `0022` is explicitly reserved (`docs/adr/README.md:29`) for a CMDB replacement doc; next free numbers are **0024+**. ADR-0007 is `Status: Proposed` (`docs/adr/0007-cmdb-implementation-for-development.md:3`).
- `OPEN-DECISIONS.md:7,13` still shows OD-01 and OD-07 as `OPEN` — must flip to `ACCEPTED 2026-07-28` with ADR links.
- Gate entry point is `make phase0-check` = `compile public-safety validate-json validate-fixtures markdown-links test` (`Makefile`). `make preflight` adds Docker-dependent foundation targets — CI/milestone only, not for an agent session.
- **No ruff target exists in the Makefile**, but `AGENTS.md` §4 claims phase0-check includes "ruff lint". `ruff.toml` exists (py312, line-length 120). Documented gate and real gate disagree → reconcile (see Task 12).
- **Hard scanner constraint**: `scripts/check_public_repo_safety.py` `FORBIDDEN_SUFFIXES` blocks `.sql`, `.log`, `.db`, `.zip`, archives, certs — and `forbidden-extension` is **not allowlistable** (`ALLOWLISTABLE_RULES` is empty). So CMDB/asset migrations may never be committed as `.sql` files; DDL must live in Python migration modules or JSON/YAML. Plan records this as a durable constraint in ADR-0024.
- `make markdown-links` resolves every repo-relative Markdown link and fails on a missing target → **each commit must be self-consistent** (link and target land together). Cross-repo (wiki) references must be `https://` URLs, never relative paths.
- `make compile` only compiles `scripts` and `tests`, so `services/**` placeholder modules are not compiled/imported by the gate; `make test` is stdlib `unittest` discovery over `tests/` (no third-party deps installed).
- `tests/test_repo_structure.py` hard-codes required-file lists → the natural TDD hook for new governance files.
- `services/{cmdb,asset-repository,api,analytics,workflow}/README.md` and `web/README.md` are 1–3 line boundary stubs that still say "remains OD-01/OD-02/OD-03"; there is no `services/README.md`.
- Wiki is a **separate repo**: `/home/infra/dcim-wiki`, branch `master`, remote `https://github.com/shuffahaqgzz/dcim-wiki.git`, files `reference-designs/block1-…`, `block5-web-dashboard.md`, `block7-analytics-ai-engine.md`, `siem-soar.md`.
- Core `deploy/compose/images.json` pins `postgres:17.10-bookworm`, while the confirmed decision says "align to PostgreSQL 16" → conflict, see Owner Clarification D-1.

### Owner clarifications needed (defaults assumed so work is not blocked)
| ID | Question | Default assumed | Blocks |
|---|---|---|---|
| D-1 | "PostgreSQL 16" vs core's pinned `postgres:17.10` | ✅ **Resolved via Context7:** PostgreSQL 17 is the program target (current stable, latest security patches incl. CVE-2025-8713); PostgreSQL 16 is the **minimum floor** for legacy/satellite components; core stays pinned `postgres:17.10-bookworm` | Task 8 (ADR-0026) |
| D-2 | Amend ADR-0007 to Accepted (vs writing reserved ADR-0022) | ✅ **Owner confirmed** — amend ADR-0007 + dated addendum; keep 0022 reserved | Task 4 |
| D-3 | Does `web/` get `package.json` now? | **No** — README + target layout only; avoid a dependency surface with zero code until Phase 2 | Task 11 |
| D-4 | Python toolchain: declare deps in `pyproject.toml` now, and wire `ruff` into `make`? | Declare pinned deps in `pyproject.toml` (nothing installed by phase0-check); wire an **optional** `make lint` target, do not add to `phase0-check` in Phase 0 | Tasks 10, 12 |
| D-5 | iTop→generic-CMDB-adapter refactor (satellite repo `DCIM_SRV_DATA_COLLECTION`) | Out of this repo's Phase 0 scope; recorded as cross-repo follow-up ticket | Task 13 |
| D-6 | Credential rotation plan (`P0-T4`) scope here | Phase 0 delivers an inventory/rotation **template + procedure doc only**, no secret values | Task 13 |
| D-7 | Wiki README license statement ("Private — internal use only") | Wiki license is the wiki's own decision; plan a note, not a relicense | Task W5 |

---

## Task Dependency Graph

| Task | Depends On | Reason |
|---|---|---|
| T1 Write `PHASE0-PLAN.md` | None | Self-contained planning artifact |
| T2 Red tests: decision-record invariants | None | TDD guard; fails until T4–T9/T14 land |
| T3 Red tests: automation safety boundary | None | TDD guard; fails until T9 lands |
| T4 ADR-0007 → Accepted (OD-01) | None (D-2) | Own file |
| T5 ADR-0024 service language baseline (OD-07) | None (D-4) | Own file |
| T6 ADR-0025 automation execution preconditions (Q4) | None | Own file; extends accepted ADR-0005 |
| T7 ADR-0016 addendum: SOAR roles (Q3) | None | Own file |
| T8 ADR-0026 version baseline (Q8, PG 16) | D-1 answer | Needs floor-vs-pin ruling |
| T9 `docs/security/automation-safety-boundary.md` | T6 | Doc links ADR-0025; markdown-links must resolve |
| T10 Service scaffolds `services/**` | T5, T2b | Stack + layout defined by ADR-0024; scaffold test defines shape |
| T2b Red tests: service scaffold structure | None | TDD guard for T10 |
| T11 `web/` README + target layout | T5 (D-3) | Frontend stack recorded in ADR-0024/0017 |
| T12 ADR-0027 private LLM serving (Q7) | None | Own file |
| T13 Registry + gate sync (`docs/adr/README.md`, `OPEN-DECISIONS.md`, `AGENTS.md` ruff wording, optional `make lint`) | T4–T8, T12 | Crosswalk rows need final ADR numbers/filenames |
| T14 Research doc sync (PRD, DECISION-LOG-REVIEW, IMPLEMENTATION-PLAN, ARCHITECTURE) | T13 | Must cite accepted ADR IDs and register statuses |
| T15 `docs/research/DECISION-MATRIX.md` | T13 | Aggregates final statuses |
| T16 Credential-rotation procedure + private-source template wiring (doc only) | None (D-6) | Independent doc |
| T17 Phase 0 evidence record + gate run | T1–T16 | Evidence is the gate result of everything |
| W1 Wiki B5 → React | T13 | Cross-links core ADR-0017/0024 URLs |
| W2 Wiki B1 → ES 9.x + PG 16 | T8, T13 | Cites ADR-0026 |
| W3 Wiki SIEM/SOAR → TraceCat+Temporal+n8n | T7, T13 | Cites ADR-0016 addendum |
| W4 Wiki B7 → 2×RTX A5000 sizing | T12, T13 | Cites ADR-0027 |
| W5 Wiki license/ownership statement note | T13 (D-7) | Cites ADR-0019 |
| T18 PR assembly + evidence checklist | T17, W1–W5 | Final packaging |

---

## Parallel Execution Graph

```
Wave 1 (start immediately — no dependencies):
├── T1  Write docs/research/PHASE0-PLAN.md
├── T2  Red tests: tests/test_decision_records.py
├── T2b Red tests: tests/test_service_scaffolds.py
├── T3  Red tests: tests/test_automation_safety_boundary.py
├── T4  ADR-0007 → Accepted (OD-01)
├── T5  ADR-0024 Python/FastAPI + TS/React baseline (OD-07)
├── T6  ADR-0025 automation execution preconditions (Q4)
├── T7  ADR-0016 addendum (Q3 SOAR roles)
├── T12 ADR-0027 private LLM serving (Q7)
└── T16 Credential rotation procedure doc

Wave 2 (after its blockers):
├── T8  ADR-0026 version baseline            (needs D-1 answer)
├── T9  automation-safety-boundary.md        (depends T6)
├── T10 services/** scaffolds                (depends T5, T2b)
└── T11 web/ README + target layout          (depends T5)

Wave 3 (after Wave 2):
└── T13 Registry + gate sync (adr/README.md, OPEN-DECISIONS.md, AGENTS.md, make lint)

Wave 4 (after T13 — all parallel):
├── T14 Research doc sync (PRD, DECISION-LOG-REVIEW, IMPLEMENTATION-PLAN, ARCHITECTURE)
├── T15 docs/research/DECISION-MATRIX.md
├── W1  Wiki B5 → React
├── W2  Wiki B1 → ES 9.x + PG 16
├── W3  Wiki SIEM/SOAR → TraceCat + Temporal + n8n
├── W4  Wiki B7 → 2×RTX A5000
└── W5  Wiki license/ownership note

Wave 5:
└── T17 Phase 0 evidence record + full `make phase0-check` run

Wave 6:
└── T18 PR assembly (4 core PRs + 1 wiki PR) + evidence checklist

Critical path: T5 → T10 → T13 → T14 → T17 → T18
Estimated parallel speedup: ~55% vs sequential (≈3.0 days sequential → ≈1.3 days wall clock)
```

---

## Tasks

### Task 1: Write `docs/research/PHASE0-PLAN.md`
**Description**: Author the Phase 0 plan document itself: scope, decision table, task table (IDs `P0-D1…P0-D18`), file-level change list, dependency/wave graph, gates, owner roles, durations, out-of-scope statement, and the D-1…D-7 clarification register. English. Links only to files that already exist (or land in the same commit) so `make markdown-links` stays green.
**Files**: create `docs/research/PHASE0-PLAN.md`.
**Delegation Recommendation**:
- Category: `writing` — long-form governance prose, no code reasoning.
- Skills: [`dcim-baseline`, `public-repo-safety`] — baseline keeps scope/gate wording authoritative; public-repo-safety keeps the doc free of endpoints/identifiers.
**Skills Evaluation**: INCLUDED `dcim-baseline` (Phase 0 scope and gate vocabulary), `public-repo-safety` (doc is public). OMITTED `tdd`/`programming` (no code), `adr-decision` (this task records no decision), `schema-change`/`readonly-connector` (no contracts or connectors), `to-tickets`/`triage`/`wayfinder` (no tracker mutation asked), `git-master` (no commits in this task), all browser/frontend/debug skills (irrelevant).
**Depends On**: None
**Owner role**: Tech Lead / Architect · **Estimate**: 3 h
**Acceptance Criteria**: file exists; contains all seven decisions with ADR targets, wave graph, per-task acceptance criteria, gate definition, and D-1…D-7; `make markdown-links` and `make public-safety` PASS.

### Task 2: Red tests — decision-record invariants
**Description**: New `tests/test_decision_records.py` (stdlib `unittest`, matching existing test style) asserting: every `docs/adr/00*.md` has a `- Status:` line with a value in {Proposed, Accepted, Rejected, Superseded}; ADR-0007 is `Accepted`; `docs/adr/README.md` crosswalk references every ADR file except explicitly reserved numbers; `OPEN-DECISIONS.md` rows OD-01 and OD-07 contain `ACCEPTED` and a link to an existing ADR file; no ADR filename gap collides with the reserved 0022. Also extend `tests/test_repo_structure.py` required lists with `docs/security/automation-safety-boundary.md`, `services/README.md`, and the new ADR paths. Tests are expected RED until Waves 2–3.
**Files**: create `tests/test_decision_records.py`; modify `tests/test_repo_structure.py`.
**Delegation Recommendation**:
- Category: `unspecified-low` — small, well-specified stdlib test module.
- Skills: [`tdd`, `programming`] — red-first discipline; Python strictness/style rules for `.py` edits.
**Skills Evaluation**: INCLUDED `tdd`, `programming`. OMITTED `adr-decision` (writes no ADR), `dcim-baseline` (no scope judgement), `debugging`/`diagnosing-bugs` (nothing broken yet), `code-review` (separate phase), `remove-ai-slops` (new small file).
**Depends On**: None
**Owner role**: Dev · **Estimate**: 1.5 h
**Acceptance Criteria**: `python3 -m unittest tests.test_decision_records -v` runs and fails **only** on the not-yet-written artifacts (assertion messages name the missing file/status); `make compile` PASS; no other test regresses.

### Task 2b: Red tests — service scaffold structure
**Description**: New `tests/test_service_scaffolds.py` asserting for each of `services/{cmdb,asset-repository,api,analytics,workflow}`: `README.md` exists and no longer contains "remains OD-0"; `pyproject.toml` parses via `tomllib` with `requires-python` ≥3.12 and a `[project] name` matching `dcim-<service>`; a placeholder module path exists; **no** `.sql`, `.log`, `.env*`, or archive files anywhere under `services/` or `web/`; placeholder modules contain no top-level executable statements other than imports/assignments/defs (AST check) and no socket/HTTP/DB client construction. Plus `services/README.md` exists.
**Files**: create `tests/test_service_scaffolds.py`.
**Delegation Recommendation**:
- Category: `unspecified-low` — bounded AST/structure test.
- Skills: [`tdd`, `programming`, `public-repo-safety`] — red-first; Python rules; the forbidden-extension/no-secret invariants come straight from the public-safety scanner.
**Skills Evaluation**: INCLUDED `tdd`, `programming`, `public-repo-safety`. OMITTED `readonly-connector` (scaffolds make no source connection — the test asserts exactly that), `frontend`/`visual-qa` (no UI code), `codebase-design` (structure is fixed by ADR-0024).
**Depends On**: None
**Owner role**: Dev · **Estimate**: 2 h
**Acceptance Criteria**: test module runs, fails listing every missing scaffold artifact; contains an explicit assertion that no `.sql` file exists under `services/`; `make compile` PASS.

### Task 3: Red tests — automation safety boundary doc
**Description**: New `tests/test_automation_safety_boundary.py` asserting `docs/security/automation-safety-boundary.md` exists and contains all five execution preconditions (human approval, maintenance window, blast-radius check, rollback plan, audit record), states dry-run/recommendation as the default mode, names the prohibited operation classes (SNMP SET, Redfish/ISAPI write/action, power/reset, firmware, PTZ, network config, raw shell, privileged SQL), links ADR-0005 and ADR-0025, and states that no execution capability exists before the Phase 6 safety layer.
**Files**: create `tests/test_automation_safety_boundary.py`.
**Delegation Recommendation**:
- Category: `quick` — single small assertion-style test file.
- Skills: [`tdd`, `programming`] — red-first; Python conventions.
**Skills Evaluation**: INCLUDED `tdd`, `programming`. OMITTED `adr-decision` (ADR authored in T6), `readonly-connector` (policy text is T9's job), `security-review` (over-scoped for a doc-content test).
**Depends On**: None
**Owner role**: Dev · **Estimate**: 1 h
**Acceptance Criteria**: test fails with "missing docs/security/automation-safety-boundary.md" before T9 and passes after; `make compile` PASS.

### Task 4: ADR-0007 → Accepted (OD-01, custom PostgreSQL CMDB)
**Description**: Amend `docs/adr/0007-cmdb-implementation-for-development.md`: `Status: Accepted`, `Date: 2026-07-17 (accepted 2026-07-28)`, `Owner: shuffahaqgzz`, decision reference OD-01, issue/PR fields filled or marked with the linking issue. Add `## Addendum 2026-07-28: owner decision` recording: custom PostgreSQL CMDB service for Phase 1–2; iTop and NetBox demoted to **read-only discovery sources** behind the canonical adapter; the previously-required comparative spike is **converted** from a selection mechanism into Phase 3 implementation acceptance evidence (canonical semantics, security negative tests, recovery/round-trip, VM headroom all still required); ADR-0022 stays reserved and unused; the satellite iTop-consumer refactor is a cross-repo follow-up (D-5). Do not delete the historical option analysis.
**Files**: modify `docs/adr/0007-cmdb-implementation-for-development.md`.
**Delegation Recommendation**:
- Category: `unspecified-high` — governance-critical amendment that must not weaken existing acceptance gates.
- Skills: [`adr-decision`, `dcim-baseline`, `public-repo-safety`] — ADR format/authority rules; baseline precedence; public-safety for a public ADR.
**Skills Evaluation**: INCLUDED `adr-decision`, `dcim-baseline`, `public-repo-safety`. OMITTED `schema-change` (no schema edits here), `programming`/`tdd` (docs only), `research` (decision already owner-confirmed; no new sources needed), `grilling` (decision is settled, not being stress-tested).
**Depends On**: None (assumes D-2 default)
**Owner role**: Architect (owner countersign) · **Estimate**: 2 h
**Acceptance Criteria**: `Status: Accepted` present; addendum dated 2026-07-28 names custom PostgreSQL + iTop/NetBox as discovery-only + spike-as-Phase-3-evidence; historical sections intact; `make markdown-links` and `make public-safety` PASS; `tests/test_decision_records.py` ADR-0007 assertion goes green.

### Task 5: ADR-0024 — Python/FastAPI service baseline (OD-07)
**Description**: Create `docs/adr/0024-python-fastapi-service-language-baseline.md`, Status Accepted 2026-07-28, decision reference OD-07, related ADR-0017 (frontend), ADR-0019 (license), ADR-0007. Record: Python 3.12 + FastAPI + Pydantic v2 for `services/{cmdb,asset-repository,api,analytics,workflow}`; TypeScript + React + Vite for `web/` (per ADR-0017); ruff as linter (`ruff.toml`, py312, line-length 120); stdlib `unittest` remains the repo gate runner, service-level `pytest` allowed once dependencies are installable outside `phase0-check`; standard service layout (`pyproject.toml`, `src/<pkg>/__init__.py`, `src/<pkg>/main.py`, `README.md`, `tests/`); pinned exact dependency versions, no version ranges; **migrations expressed as Python modules or JSON/YAML — never `.sql`**, because the public-safety scanner's `forbidden-extension` rule blocks `.sql` and is not allowlistable; no runtime code, no network client, and no DB connection in Phase 0 scaffolds; options considered (Go, TypeScript/NestJS) rejected with reasons; license, resource, migration/rollback, acceptance-evidence, revalidation-trigger sections in the house style.
**Files**: create `docs/adr/0024-python-fastapi-service-language-baseline.md`.
**Delegation Recommendation**:
- Category: `unspecified-high` — new durable architecture record with downstream scaffold consequences.
- Skills: [`adr-decision`, `dcim-baseline`, `programming`, `public-repo-safety`] — ADR authority/format; baseline gates; Python/TS stack conventions the ADR must state precisely; public-safety for a public ADR.
**Skills Evaluation**: INCLUDED `adr-decision`, `dcim-baseline`, `programming`, `public-repo-safety`. OMITTED `frontend` (frontend framework already decided in ADR-0017; no UI built), `schema-change` (no contract edits), `research` (owner-confirmed), `codebase-design` (module design deferred to Phase 2–3).
**Depends On**: None (assumes D-4 default)
**Owner role**: Architect · **Estimate**: 3 h
**Acceptance Criteria**: ADR exists, Accepted, cites OD-07 and the confirmed PRD Q2; states the `.sql` prohibition with the scanner rationale; states the exact scaffold layout T10 will create; `make phase0-check` PASS.

### Task 6: ADR-0025 — automation execution preconditions (Q4)
**Description**: Create `docs/adr/0025-automation-execution-preconditions.md`, Status Accepted 2026-07-28, explicitly **extending** (not superseding) ADR-0005. Record: dry-run/recommendation is the default and only currently available mode; any future execution path requires all five preconditions simultaneously (explicit human approval with recorded actor, active maintenance window, blast-radius report on affected CIs, documented rollback action per step, immutable audit record); execution capability may not exist before the Phase 6 safety layer; the n8n `systemctl restart` prototype workflow in the satellite repo stays suspended until hardened; negative tests (execute without approval → blocked; outside window → blocked; missing rollback → blocked) are acceptance evidence; prohibited operation classes remain prohibited regardless of approval.
**Files**: create `docs/adr/0025-automation-execution-preconditions.md`.
**Delegation Recommendation**:
- Category: `unspecified-high` — safety-boundary decision; wording errors create a write-path risk.
- Skills: [`adr-decision`, `dcim-baseline`, `readonly-connector`, `public-repo-safety`] — ADR authority; baseline safety boundary; readonly-connector carries the write/control denylist vocabulary; public-safety for publication.
**Skills Evaluation**: INCLUDED `adr-decision`, `dcim-baseline`, `readonly-connector`, `public-repo-safety`. OMITTED `security-review`/`security-research` (multi-agent exploit hunt is disproportionate for a policy ADR), `tdd` (no code), `prototype` (nothing to prototype).
**Depends On**: None
**Owner role**: Security Lead + Architect · **Estimate**: 2.5 h
**Acceptance Criteria**: ADR exists and Accepted; all five preconditions listed as conjunctive; ADR-0005 referenced as extended; prohibited classes enumerated; `make phase0-check` PASS.

### Task 7: ADR-0016 addendum — SOAR platform roles (Q3)
**Description**: Append `## Addendum 2026-07-28: owner decision on SOAR platform roles` to `docs/adr/0016-workflow-engine-split.md`: TraceCat + Temporal is the SOAR/security-automation path; n8n is retained **only** for non-destructive operational workflows and is not the SOAR platform; TraceCat license/footprint verification remains a precondition to activation (unchanged from the accepted body); Wazuh → Kafka `dcim.siem.events` producer stays the SIEM output design; phasing unchanged and bounded by C-07.
**Files**: modify `docs/adr/0016-workflow-engine-split.md`.
**Delegation Recommendation**:
- Category: `unspecified-low` — bounded addendum to an already-accepted ADR.
- Skills: [`adr-decision`, `dcim-baseline`] — amendment conventions; baseline precedence.
**Skills Evaluation**: INCLUDED `adr-decision`, `dcim-baseline`. OMITTED `public-repo-safety` (no new data/fixtures/endpoints introduced), `research` (owner-confirmed), `programming` (docs only).
**Depends On**: None
**Owner role**: Architect · **Estimate**: 1 h
**Acceptance Criteria**: addendum present and dated; accepted body unmodified; TraceCat license precondition preserved; `make phase0-check` PASS.

### Task 8: ADR-0026 — program technology version baseline (Q8 + PG target)
**Description**: Create `docs/adr/0026-program-technology-version-baseline.md`, Status Accepted 2026-07-28, related ADR-0018 (Elasticsearch), ADR-0003 (Kafka), ADR-0013/0014 (image provenance). Record the program-wide targets: Elasticsearch **9.x** (supersedes the wiki's 8.x target; ADR-0018's license constraints unchanged), **PostgreSQL 17.x as the program target** with the core dev-build's pinned `postgres:17.10-bookworm` remaining authoritative for the foundation plane; **PostgreSQL 16 as the minimum floor** for satellite components that cannot upgrade immediately (D-1 resolved via Context7: 17 is current stable and contains the latest security fixes, e.g., CVE-2025-8713; 16 is the safe floor). Redis 7, Kafka per ADR-0003/images.json. State that concrete digests stay in `deploy/compose/images.json` and are not duplicated in the ADR, and that a version bump is a pinned-image change under ADR-0014, not a doc edit.
**Files**: create `docs/adr/0026-program-technology-version-baseline.md`.
**Delegation Recommendation**:
- Category: `unspecified-high` — must resolve a real 16-vs-17 inconsistency without contradicting pinned-image ADRs.
- Skills: [`adr-decision`, `dcim-baseline`, `public-repo-safety`] — ADR authority; baseline platform section; public-safety since version/image text is scanned.
**Skills Evaluation**: INCLUDED `adr-decision`, `dcim-baseline`, `public-repo-safety`. OMITTED `schema-change` (no contract/Avro change), `readonly-connector` (no connector behavior), `research` (facts already in-repo).
**Depends On**: D-1 owner answer
**Owner role**: Architect (owner countersign on D-1) · **Estimate**: 2 h
**Acceptance Criteria**: ADR exists and Accepted; ES 9.x recorded; PG statement is explicit about floor vs pinned 17.x and flags D-1; no image digests duplicated; `make phase0-check` PASS.

### Task 9: `docs/security/automation-safety-boundary.md`
**Description**: Create the operational policy doc implementing ADR-0025: default mode (notification, recommendation, ticket draft, approval simulation, dry-run); the five conjunctive execution preconditions with what evidence each requires; prohibited operation classes (SNMP SET, Redfish/ISAPI write/action, power/reset, firmware, PTZ, network configuration, raw shell, privileged SQL); enforcement expectations (policy gate service, dry-run simulator, approval service, rollback stubs, append-only audit) mapped to Phase 6; required negative tests; escalation/stop path cross-linking `docs/security/emergency-collector-kill-switch.md`; explicit statement that Phase 0 documents the boundary and ships **no** executable control. Match the terse Indonesian-or-English house style of the neighbouring `docs/security/*.md` files (English per this request) and keep links repo-relative to existing files only.
**Files**: create `docs/security/automation-safety-boundary.md`.
**Delegation Recommendation**:
- Category: `unspecified-high` — security policy text that a later gate is tested against.
- Skills: [`readonly-connector`, `dcim-baseline`, `public-repo-safety`, `adr-decision`] — denylist vocabulary; baseline safety scope; public-safety; adr-decision keeps doc/ADR wording aligned.
**Skills Evaluation**: INCLUDED `readonly-connector`, `dcim-baseline`, `public-repo-safety`, `adr-decision`. OMITTED `security-research` (no code to exploit), `tdd` (test authored in T3), `writing` category-skill overlap not needed.
**Depends On**: T6
**Owner role**: Security Lead · **Estimate**: 2.5 h
**Acceptance Criteria**: `tests/test_automation_safety_boundary.py` goes GREEN; doc links ADR-0005 and ADR-0025 and the kill-switch doc; `make phase0-check` PASS.

### Task 10: Service scaffolds under `services/`
**Description**: Create `services/README.md` (index: the five service boundaries, the ADR-0024 stack, the "no runtime code in Phase 0" rule, the `.sql` prohibition, how to run the repo gate). For each of `services/{cmdb,asset-repository,api,analytics,workflow}`: rewrite `README.md` (purpose, owning ADRs with the OD language now resolved, planned API group per `docs/research/ARCHITECTURE.md` §9.1, planned layout, local commands, explicit "no source connection, no credentials, no runtime state" statement); add `pyproject.toml` (`[project] name = "dcim-<service>"`, `requires-python = ">=3.12"`, pinned exact deps, `[tool.ruff] extend = "../../ruff.toml"` or equivalent); add `src/<pkg>/__init__.py` and `src/<pkg>/main.py` containing **only** a module docstring plus a `create_app()`/`describe()` placeholder that returns a static dict and raises `NotImplementedError` for any behavior — no FastAPI app instantiation at import, no network/DB client, no `if __name__ == "__main__"` server start. Update `services/cmdb/README.md` to record the accepted custom-PostgreSQL direction and iTop/NetBox as discovery-only. No `.sql`, no `.env*`, no fixtures.
**Files**: create `services/README.md`; create `services/<svc>/pyproject.toml`, `services/<svc>/src/<pkg>/__init__.py`, `services/<svc>/src/<pkg>/main.py` (×5); modify `services/<svc>/README.md` (×5).
**Delegation Recommendation**:
- Category: `unspecified-high` — many coordinated files that must keep every gate green and stay side-effect-free.
- Skills: [`programming`, `tdd`, `public-repo-safety`, `dcim-baseline`] — Python/pyproject conventions and the 250-LOC/strict-typing philosophy; tdd to drive T2b green; public-safety for extension/endpoint rules; baseline for the no-runtime-code boundary.
**Skills Evaluation**: INCLUDED `programming`, `tdd`, `public-repo-safety`, `dcim-baseline`. OMITTED `frontend` (that's T11 and README-only), `codebase-design` (deep-module design belongs to Phase 2–3 implementation), `readonly-connector` (no connector created — asserted absent), `refactor`/`remove-ai-slops` (new minimal files).
**Depends On**: T5, T2b
**Owner role**: Dev · **Estimate**: 4 h
**Acceptance Criteria**: `tests/test_service_scaffolds.py` GREEN; `python3 -m compileall -q services` succeeds; importing any placeholder module performs no I/O (AST assertion enforces it); `make phase0-check` PASS; no `.sql`/`.env`/archive files added.

### Task 11: `web/` README + target layout
**Description**: Rewrite `web/README.md`: OD-03 resolved (ADR-0017 React + TypeScript + Vite, reaffirmed by ADR-0024), first-slice view scope (component health, data freshness, P1/P2 events, capacity, quality/DLQ, Asset/CI context, workflow drafts — synthetic data only), planned directory layout, the explicit decision that **no `package.json`/lockfile lands in Phase 0** (D-3 rationale: avoid a dependency-review surface with zero code; Phase 2 introduces it with pinned versions), and a statement that API types will be generated from `schemas/*.schema.json`.
**Files**: modify `web/README.md`.
**Delegation Recommendation**:
- Category: `quick` — single documentation file.
- Skills: [`dcim-baseline`, `public-repo-safety`] — scope wording; public-safety (no endpoints/URLs).
**Skills Evaluation**: INCLUDED `dcim-baseline`, `public-repo-safety`. OMITTED `frontend`/`visual-qa` (no UI is built or rendered — README only), `programming` (no code file), `tdd` (structure covered by T2b).
**Depends On**: T5
**Owner role**: Dev · **Estimate**: 1 h
**Acceptance Criteria**: README no longer says "remains OD-03"; states the Phase 0 no-`package.json` decision with rationale; `make phase0-check` PASS.

### Task 12: ADR-0027 — private LLM serving baseline (Q7)
**Description**: Create `docs/adr/0027-private-llm-serving-baseline.md`, Status Accepted 2026-07-28, related ADR-0009 (Hermes deferred) and OD-05. Record: private hosting on 2×RTX A5000 24 GB VRAM with Ollama/llama.cpp-class serving; a provider abstraction layer permitting managed-API fallback only under an explicit data-boundary review (no office/Production data to external AI, per the auto-NO-GO list); this decision covers the analytics/RAG explanation layer and does **not** re-open OD-05 or authorize Hermes; note the baseline's "24 GB VRAM GPU" single-GPU statement versus the confirmed 2×A5000 sizing and record the sizing as a Phase 4 capacity item; no GPU workload, model weight, or inference endpoint enters this repository.
**Files**: create `docs/adr/0027-private-llm-serving-baseline.md`.
**Delegation Recommendation**:
- Category: `unspecified-high` — touches the AI/data-egress boundary; must not imply Hermes re-entry.
- Skills: [`adr-decision`, `dcim-baseline`, `public-repo-safety`] — ADR authority; baseline GPU/Hermes boundary; public-safety for egress language.
**Skills Evaluation**: INCLUDED `adr-decision`, `dcim-baseline`, `public-repo-safety`. OMITTED `research` (owner-confirmed hardware), `readonly-connector` (no source connector), `programming` (docs only).
**Depends On**: None
**Owner role**: Architect + Security Lead · **Estimate**: 2 h
**Acceptance Criteria**: ADR exists and Accepted; states OD-05/Hermes remains deferred; states no weights/endpoints in repo; records the 1-GPU-vs-2-GPU baseline discrepancy; `make phase0-check` PASS.

### Task 13: Registry + gate sync
**Description**: (a) `docs/adr/README.md`: add crosswalk rows for ADR-0024, 0025, 0026, 0027; update the trailing note so ADR-0007 is listed as the accepted OD-01 decision and ADR-0022 is stated as reserved-and-unused. (b) `docs/governance/OPEN-DECISIONS.md`: OD-01 → `ACCEPTED 2026-07-28 — ADR-0007`; OD-07 → `ACCEPTED 2026-07-28 — ADR-0024`; leave OD-05 DEFERRED untouched. (c) `docs/governance/CONDITIONS-REGISTER.md`: add an `## Owner direction 2026-07-28` section recording the decision lock and stating **no condition is closed** by it. (d) `AGENTS.md` §4: reconcile the "ruff lint" claim with the actual `phase0-check` target list. (e) Optionally add a `lint` target to the `Makefile` running `ruff check` when available (not added to `phase0-check`, so the zero-dependency gate stays intact) — per D-4.
**Files**: modify `docs/adr/README.md`, `docs/governance/OPEN-DECISIONS.md`, `docs/governance/CONDITIONS-REGISTER.md`, `AGENTS.md`, `Makefile`.
**Delegation Recommendation**:
- Category: `unspecified-high` — register edits are the authority surface; a wrong status here misleads every later agent.
- Skills: [`adr-decision`, `dcim-baseline`, `public-repo-safety`] — decision-status conventions; baseline precedence; public-safety scan on modified docs.
**Skills Evaluation**: INCLUDED `adr-decision`, `dcim-baseline`, `public-repo-safety`. OMITTED `programming` (the Makefile edit is a two-line target, no language work), `git-master` (commits handled in T18), `tdd` (guard already written in T2).
**Depends On**: T4, T5, T6, T7, T8, T12
**Owner role**: Architect · **Estimate**: 2 h
**Acceptance Criteria**: `tests/test_decision_records.py` fully GREEN; `AGENTS.md` gate description matches the Makefile; `make phase0-check` PASS; no condition status changed to CLOSED.

### Task 14: Research doc sync
**Description**: (a) `docs/research/PRD.md`: header Status → `v1.0 — owner-confirmed 2026-07-28`; §7 table rows gain ADR links; §9 action items 1–2 marked done with ADR references, 3–7 re-pointed at their owning workstream. (b) `docs/research/DECISION-LOG-REVIEW.md`: move OD-01 and OD-07 into §1 Accepted ADRs (with ADR-0007/0024); add rows for ADR-0025/0026/0027 and the ADR-0016 addendum; §4 table gains ADR links; §6 close-condition checkboxes ticked where now true (ADR updated, scaffold created) and left unticked for cross-repo items; wiki backlog items become `https://github.com/shuffahaqgzz/dcim-wiki/...` links with a note that the wiki is a separate repo/workstream. (c) `docs/research/IMPLEMENTATION-PLAN.md` §3: mark P0-T1/T2/T3/T5 complete with evidence pointers, restate P0-T4 as the doc-only rotation procedure (T16), P0-T6/P0-T7 as next actionable (Phase 2 scope freeze issue; wiki workstream), and rewrite §3.3 Gate to the Phase 0 gate defined below. (d) `docs/research/ARCHITECTURE.md` §8 and §10: add ADR-0024/0025/0026/0027 references and the PG-floor-vs-pin clarification.
**Files**: modify `docs/research/PRD.md`, `docs/research/DECISION-LOG-REVIEW.md`, `docs/research/IMPLEMENTATION-PLAN.md`, `docs/research/ARCHITECTURE.md`.
**Delegation Recommendation**:
- Category: `writing` — multi-file prose/table sync, low logic risk once ADRs are fixed.
- Skills: [`dcim-baseline`, `public-repo-safety`, `adr-decision`] — keep gate/scope wording authoritative; public-safety on edited docs; adr-decision to cite statuses correctly.
**Skills Evaluation**: INCLUDED `dcim-baseline`, `public-repo-safety`, `adr-decision`. OMITTED `programming`/`tdd` (no code), `to-spec`/`to-tickets` (no tracker publication requested in this task), `handoff` (session handoff not requested).
**Depends On**: T13
**Owner role**: Product Owner / Tech Lead · **Estimate**: 3 h
**Acceptance Criteria**: no research doc still calls OD-01 or OD-07 open; every wiki reference is an absolute URL (no repo-relative link into another repo); `make markdown-links` PASS; `make phase0-check` PASS.

### Task 15: `docs/research/DECISION-MATRIX.md`
**Description**: Create the decision matrix recommended by `DECISION-LOG-REVIEW.md` §7.5: one row per OD-01…OD-07, C-01…C-10, and PRD Q1…Q10 with status, owning ADR, owner role, deadline, and evidence pointer. Read-only aggregation — no status invented; anything unresolved is listed as open with its blocker.
**Files**: create `docs/research/DECISION-MATRIX.md`.
**Delegation Recommendation**:
- Category: `writing` — tabular aggregation.
- Skills: [`dcim-baseline`, `public-repo-safety`] — status vocabulary; public-safety.
**Skills Evaluation**: INCLUDED `dcim-baseline`, `public-repo-safety`. OMITTED `adr-decision` (records no new decision), `domain-modeling` (no glossary change), `programming` (no code).
**Depends On**: T13
**Owner role**: Tech Lead · **Estimate**: 1.5 h
**Acceptance Criteria**: every OD/C/Q row present with a status matching the authoritative register; no row upgrades a condition status; `make phase0-check` PASS.

### Task 16: Credential-rotation procedure (doc only, D-6)
**Description**: Create `docs/security/credential-rotation-procedure.md`: scope statement (satellite repos are separate workstreams), the inventory procedure (what to enumerate, by key name only — never values), rotation ordering, revocation, verification, and the record location **outside Git**, cross-linking `DATA-HANDLING.md`, `SECURITY.md`, `docs/templates/private-source-authorization-register.template.md`, and C-04. Contains no secret, no endpoint, no identifier, and no scan output — only procedure and a template shape.
**Files**: create `docs/security/credential-rotation-procedure.md`.
**Delegation Recommendation**:
- Category: `unspecified-high` — security procedure with a strict no-value rule.
- Skills: [`public-repo-safety`, `dcim-baseline`, `readonly-connector`] — public-safety is the governing constraint; baseline for C-04 wording; readonly-connector for least-privilege identity vocabulary.
**Skills Evaluation**: INCLUDED `public-repo-safety`, `dcim-baseline`, `readonly-connector`. OMITTED `security-research` (no target system), `adr-decision` (procedure, not a durable architecture choice), `programming` (no code).
**Depends On**: None
**Owner role**: Security Lead · **Estimate**: 2 h
**Acceptance Criteria**: doc contains zero credential values and zero real endpoints; references C-04 without closing it; `make public-safety` and `make phase0-check` PASS.

### Task 17: Phase 0 evidence record + gate run
**Description**: Run the gate and record it: create `docs/evidence/2026-07-28-phase0-decision-lock.md` following the existing evidence-file style (dated filename, gate/command/result table, scope and boundary statements, explicit "this is not Staging or Production approval"). Record `make phase0-check` output summary (counts, PASS), the individual gate results, the list of ADRs accepted, and the Docker-dependent gates explicitly marked **not run in this session** (`make preflight`, `foundation-*`) with the reason. Update `docs/phase0/evidence-index.md` with a row pointing to the new record.
**Files**: create `docs/evidence/2026-07-28-phase0-decision-lock.md`; modify `docs/phase0/evidence-index.md`.
**Delegation Recommendation**:
- Category: `unspecified-high` — evidence claims must be exactly what was executed, no inflation.
- Skills: [`pr-evidence`, `dcim-baseline`, `public-repo-safety`] — pr-evidence defines the evidence discipline and forbids unverified claims; baseline for gate list; public-safety for redaction.
**Skills Evaluation**: INCLUDED `pr-evidence`, `dcim-baseline`, `public-repo-safety`. OMITTED `code-review`/`review-work` (review is T18's PR step), `tdd` (tests already written), `git-master` (no commits here).
**Depends On**: T1–T16
**Owner role**: Tech Lead · **Estimate**: 1.5 h
**Acceptance Criteria**: `make phase0-check` PASS recorded verbatim-summarized; every non-run gate explicitly labelled not-run with reason; no raw scanner output or secret value; `make markdown-links` PASS.

### Task W1: Wiki B5 → React (separate repo)
**Description**: In `/home/infra/dcim-wiki` (branch off `master`), update `reference-designs/block5-web-dashboard.md`: replace the Vue 3 target with React + TypeScript + Vite, TanStack Query for server state, and add a cross-repo reference block citing `https://github.com/shuffahaqgzz/dcim-core-platform/blob/main/docs/adr/0017-react-noc-dashboard-frontend.md` and the ADR-0024 URL. Keep the wiki's own conventions and language; do not import core-repo relative links.
**Delegation Recommendation**:
- Category: `writing` — reference-design prose edit.
- Skills: [`public-repo-safety`, `dcim-baseline`] — provenance/secrecy discipline carries to the wiki; baseline for decision wording.
**Skills Evaluation**: INCLUDED `public-repo-safety`, `dcim-baseline`. OMITTED `frontend` (no UI implemented, doc only), `programming` (no code), `adr-decision` (ADR lives in the core repo).
**Depends On**: T13
**Owner role**: Wiki Lead · **Estimate**: 1.5 h
**Acceptance Criteria**: no remaining Vue 3 target statement in B5; every core-repo reference is an absolute URL; wiki change isolated to its own branch/PR.

### Task W2: Wiki B1 → ES 9.x + PostgreSQL 16
**Description**: Update `reference-designs/block1-infrastructure-provisioning.md` to Elasticsearch 9.x and PostgreSQL 16 (stating the floor-vs-pinned nuance from ADR-0026), citing the ADR-0018 and ADR-0026 URLs.
**Delegation Recommendation**: Category `writing`; Skills [`public-repo-safety`, `dcim-baseline`].
**Skills Evaluation**: INCLUDED `public-repo-safety`, `dcim-baseline`. OMITTED `schema-change` (no contract), `adr-decision` (core-repo artifact), `programming`.
**Depends On**: T8, T13 · **Owner role**: Wiki Lead · **Estimate**: 1.5 h
**Acceptance Criteria**: version table shows ES 9.x and PG 16 floor with the pinned-17 note; ADR URLs present.

### Task W3: Wiki SIEM/SOAR → TraceCat + Temporal + n8n role
**Description**: Update `reference-designs/siem-soar.md` (and `siem-soar-actual-architecture.md` if it contradicts) so TraceCat + Temporal is the SOAR path and n8n is limited to non-destructive operational workflows; add the safety-boundary statement (dry-run default, five execution preconditions) citing the ADR-0016 addendum, ADR-0025, and `docs/security/automation-safety-boundary.md` URLs.
**Delegation Recommendation**: Category `writing`; Skills [`public-repo-safety`, `dcim-baseline`, `readonly-connector`].
**Skills Evaluation**: INCLUDED `public-repo-safety`, `dcim-baseline`, `readonly-connector` (safety wording must match the denylist). OMITTED `security-research`, `programming`, `adr-decision`.
**Depends On**: T7, T9, T13 · **Owner role**: Wiki Lead + Security Lead · **Estimate**: 2 h
**Acceptance Criteria**: no wiki text presents n8n as the SOAR platform or implies unattended remediation; ADR/policy URLs present.

### Task W4: Wiki B7 → private LLM 2×RTX A5000 sizing
**Description**: Update `reference-designs/block7-analytics-ai-engine.md` (and the private-LLM plan page if present) with 2×RTX A5000 24 GB VRAM sizing, the provider abstraction layer, and the data-boundary rule for managed-API fallback, citing the ADR-0027 URL. No endpoints, no model weights, no credentials.
**Delegation Recommendation**: Category `writing`; Skills [`public-repo-safety`, `dcim-baseline`].
**Skills Evaluation**: INCLUDED `public-repo-safety` (egress/AI-boundary language), `dcim-baseline`. OMITTED `research` (owner-confirmed hardware), `programming`.
**Depends On**: T12, T13 · **Owner role**: Wiki Lead · **Estimate**: 1.5 h
**Acceptance Criteria**: sizing and fallback rule recorded; ADR-0027 URL present; no endpoint or credential text added.

### Task W5: Wiki license/ownership statement note
**Description**: Update the wiki `README.md` license/ownership statement so it no longer implies the core repository is private: state that `dcim-core-platform` is Apache-2.0 (ADR-0019 URL) and that the wiki's own license/visibility is a separate owner decision (D-7). Do not relicense the wiki.
**Delegation Recommendation**: Category `quick`; Skills [`public-repo-safety`].
**Skills Evaluation**: INCLUDED `public-repo-safety` (publication boundary). OMITTED `adr-decision` (no ADR authored in the wiki), `dcim-baseline` (single-sentence edit), `programming`.
**Depends On**: T13, D-7 · **Owner role**: Owner + Wiki Lead · **Estimate**: 0.5 h
**Acceptance Criteria**: statement no longer contradicts ADR-0019; wiki's own license left to the owner.

### Task 18: PR assembly + evidence checklist
**Description**: Assemble the work into the PR set below, each with the repo PR template completed (linked issue/ADR, scope/out-of-scope, verification commands and results, data-boundary checklist, risk/rollback). Do **not** open PRs or push until the owner approves. Verify `git status` shows only intended files, no `.env*`, no `.sql`, no archives, no `__pycache__` additions.
**Delegation Recommendation**:
- Category: `unspecified-high` — packaging correctness and evidence honesty.
- Skills: [`pr-evidence`, `git-master`, `public-repo-safety`, `code-review`] — evidence discipline; atomic-commit/branch mechanics; final data-boundary sweep; code-review for a last standards pass over the diff.
**Skills Evaluation**: INCLUDED `pr-evidence`, `git-master`, `public-repo-safety`, `code-review`. OMITTED `review-work` (5-agent orchestration is disproportionate for a docs/scaffold change), `tdd` (tests already green), `resolving-merge-conflicts` (no conflict expected on a fresh branch).
**Depends On**: T17, W1–W5
**Owner role**: Tech Lead (owner approves) · **Estimate**: 2 h
**Acceptance Criteria**: PR bodies complete; `make phase0-check` result pasted; no unintended file staged; nothing pushed without owner approval.

---

## Commit Strategy

Branch (core repo), cut from current `docs/issue-9-closure` base or fresh from `main` per owner preference: `docs/phase0-decision-lock`. Wiki work uses `docs/align-core-decisions-2026-07-28` in `/home/infra/dcim-wiki`.

Atomic conventional commits, one coherent concern each, in this order (each commit must independently keep `make phase0-check` green — except the deliberate red-test commits, which are immediately followed by their green commit in the same PR):

| # | Commit | Contents |
|---|---|---|
| 1 | `docs(phase0): add Phase 0 decision-lock plan` | T1 |
| 2 | `test(governance): add failing decision-record invariants` | T2 (red) |
| 3 | `test(services): add failing service scaffold invariants` | T2b (red) |
| 4 | `test(security): add failing automation safety boundary checks` | T3 (red) |
| 5 | `docs(adr): accept ADR-0007 custom PostgreSQL CMDB for OD-01` | T4 |
| 6 | `docs(adr): add ADR-0024 Python/FastAPI service baseline for OD-07` | T5 |
| 7 | `docs(adr): add ADR-0025 automation execution preconditions` | T6 |
| 8 | `docs(adr): record SOAR platform roles in ADR-0016 addendum` | T7 |
| 9 | `docs(adr): add ADR-0026 program technology version baseline` | T8 |
| 10 | `docs(adr): add ADR-0027 private LLM serving baseline` | T12 |
| 11 | `docs(security): add automation safety boundary policy` | T9 (turns commit 4 green) |
| 12 | `feat(services): add public-safe service scaffolds` | T10 (turns commit 3 green) |
| 13 | `docs(web): record React frontend scope and Phase 0 layout` | T11 |
| 14 | `docs(governance): record OD-01 and OD-07 acceptance` | T13 (turns commit 2 green) |
| 15 | `docs(security): add credential rotation procedure` | T16 |
| 16 | `docs(research): sync PRD, decision log, plan, and architecture` | T14 |
| 17 | `docs(research): add program decision matrix` | T15 |
| 18 | `docs(evidence): record Phase 0 decision-lock gate results` | T17 |

PR grouping (owner may squash-merge each):
- **PR A — decision records**: commits 2, 5–10, 14 (`tests/test_decision_records.py` + ADRs + registers).
- **PR B — safety boundary**: commits 4, 11, 15.
- **PR C — scaffolds**: commits 3, 12, 13.
- **PR D — research/plan/evidence**: commits 1, 16, 17, 18.
- **PR E — wiki (separate repo)**: W1–W5 as one PR with per-file commits.

Rules: never force-push, never commit `.sql`/`.log`/`.env*`/archives/`__pycache__`, stage explicit paths (no `git add .`), no commit or push until the owner approves.

---

## Success Criteria (Phase 0 Gate)

1. `make phase0-check` PASS on the final branch head — no new failures versus the pre-change baseline (`compile`, `public-safety`, `validate-json`, `validate-fixtures`, `markdown-links`, `test`).
2. All new/amended ADRs carry `Status: Accepted`, a 2026-07-28 date, an owner line, and a decision reference; `docs/adr/README.md` crosswalk covers them; ADR-0022 remains reserved.
3. `docs/governance/OPEN-DECISIONS.md` shows OD-01 and OD-07 `ACCEPTED` with ADR links; no condition in `CONDITIONS-REGISTER.md` moved to `CLOSED`.
4. New tests (`test_decision_records`, `test_service_scaffolds`, `test_automation_safety_boundary`) all GREEN, plus the pre-existing suite unchanged in pass count except the additions.
5. No hardcoded secret, credential, endpoint, non-documentation IP/FQDN, `.sql`, `.log`, `.env*`, or archive file added (`make public-safety` PASS).
6. All repo-relative Markdown links resolve; all cross-repo (wiki) references are absolute URLs (`make markdown-links` PASS).
7. `services/**` contains no runtime-executing code: no network client, no DB connection, no server start, no import-time side effects (AST-asserted).
8. Docker-dependent gates (`make preflight`, `foundation-*`) explicitly recorded as **not run** in the agent session, with CI/milestone as their venue.
9. Evidence record `docs/evidence/2026-07-28-phase0-decision-lock.md` exists and claims only what was executed.
10. Wiki workstream branch covers B5, B1, SIEM/SOAR, B7, and the license statement, referencing core ADRs by URL.
11. Owner countersign obtained on D-1 (PG 16 vs pinned 17.10) and D-2 (ADR-0007 amendment vs reserved ADR-0022) before PR A merges.

**Total effort estimate**: ≈39 h of task work; ≈3.0 days sequential solo, ≈1.3 days wall clock with the wave parallelism above.

---

## TODO List (ADD THESE)

> CALLER: Add these TODOs using TodoWrite/TaskCreate and execute by wave. Get owner answers on D-1 and D-2 before Wave 2 completes.

### Wave 1 (Start Immediately — No Dependencies)

- [ ] **1. `docs/research/PHASE0-PLAN.md`: write Phase 0 decision-lock plan to give the executor a single source of truth — expect a doc covering 7 decisions, waves, gates, D-1…D-7**
  - What: Author the plan doc per Task 1 (scope, decision table, task table, wave graph, gates, owner roles, durations, clarification register). Links only to existing files.
  - Depends: None · Blocks: 18
  - Category: `writing` · Skills: [`dcim-baseline`, `public-repo-safety`]
  - QA: `make markdown-links && make public-safety`

- [ ] **2. `tests/test_decision_records.py`: add red tests for ADR status/crosswalk/OD invariants — expect failures naming missing ADRs and OPEN OD rows**
  - What: Task 2 — new stdlib unittest module + extend `tests/test_repo_structure.py` required lists.
  - Depends: None · Blocks: 14
  - Category: `unspecified-low` · Skills: [`tdd`, `programming`]
  - QA: `python3 -m unittest tests.test_decision_records -v` fails only on missing artifacts; `make compile` PASS

- [ ] **3. `tests/test_service_scaffolds.py`: add red tests for services/ layout and no-side-effect rule — expect failures listing every missing scaffold file**
  - What: Task 2b — README/pyproject/module assertions, `.sql`/`.env`/archive prohibition, AST no-import-side-effect check.
  - Depends: None · Blocks: 12
  - Category: `unspecified-low` · Skills: [`tdd`, `programming`, `public-repo-safety`]
  - QA: `python3 -m unittest tests.test_service_scaffolds -v` fails with named missing paths; `make compile` PASS

- [ ] **4. `tests/test_automation_safety_boundary.py`: add red test for the safety policy doc — expect failure "missing docs/security/automation-safety-boundary.md"**
  - What: Task 3 — assert five preconditions, dry-run default, prohibited classes, ADR-0005/0025 links.
  - Depends: None · Blocks: 11
  - Category: `quick` · Skills: [`tdd`, `programming`]
  - QA: `python3 -m unittest tests.test_automation_safety_boundary -v` fails on the missing doc

- [ ] **5. `docs/adr/0007-cmdb-implementation-for-development.md`: set Accepted + 2026-07-28 addendum to close OD-01 — expect custom PostgreSQL CMDB recorded, iTop/NetBox discovery-only**
  - What: Task 4. Keep historical analysis; convert the spike into Phase 3 acceptance evidence; note ADR-0022 stays reserved.
  - Depends: None (confirm D-2) · Blocks: 14
  - Category: `unspecified-high` · Skills: [`adr-decision`, `dcim-baseline`, `public-repo-safety`]
  - QA: `make phase0-check`; ADR-0007 assertion in `tests/test_decision_records.py` green

- [ ] **6. `docs/adr/0024-python-fastapi-service-language-baseline.md`: create Accepted ADR to close OD-07 — expect Python/FastAPI + TS/React, scaffold layout, `.sql` prohibition**
  - What: Task 5. Full house-style ADR incl. rejected Go/NestJS, pinned-deps rule, no-runtime-code-in-Phase-0 rule.
  - Depends: None (confirm D-4) · Blocks: 12, 13, 14
  - Category: `unspecified-high` · Skills: [`adr-decision`, `dcim-baseline`, `programming`, `public-repo-safety`]
  - QA: `make phase0-check`

- [ ] **7. `docs/adr/0025-automation-execution-preconditions.md`: create Accepted ADR extending ADR-0005 for Q4 — expect five conjunctive preconditions and Phase 6 gating**
  - What: Task 6.
  - Depends: None · Blocks: 11, 14
  - Category: `unspecified-high` · Skills: [`adr-decision`, `dcim-baseline`, `readonly-connector`, `public-repo-safety`]
  - QA: `make phase0-check`

- [ ] **8. `docs/adr/0016-workflow-engine-split.md`: append 2026-07-28 addendum for Q3 — expect TraceCat+Temporal as SOAR, n8n non-destructive only**
  - What: Task 7, accepted body untouched.
  - Depends: None · Blocks: 14, W3
  - Category: `unspecified-low` · Skills: [`adr-decision`, `dcim-baseline`]
  - QA: `make phase0-check`

- [ ] **9. `docs/adr/0027-private-llm-serving-baseline.md`: create Accepted ADR for Q7 — expect 2×RTX A5000 sizing, fallback abstraction, OD-05 still deferred**
  - What: Task 12.
  - Depends: None · Blocks: 14, W4
  - Category: `unspecified-high` · Skills: [`adr-decision`, `dcim-baseline`, `public-repo-safety`]
  - QA: `make phase0-check`

- [ ] **10. `docs/security/credential-rotation-procedure.md`: add doc-only rotation procedure for C-04 progress — expect zero credential values and zero endpoints**
  - What: Task 16.
  - Depends: None (confirm D-6) · Blocks: 18
  - Category: `unspecified-high` · Skills: [`public-repo-safety`, `dcim-baseline`, `readonly-connector`]
  - QA: `make public-safety && make phase0-check`

### Wave 2 (After Wave 1)

- [ ] **11. `docs/security/automation-safety-boundary.md`: write the Q4 policy doc to turn TODO 4 green — expect five preconditions, prohibited classes, Phase 6 gating**
  - What: Task 9, links ADR-0005/0025 and the kill-switch doc.
  - Depends: 7 · Blocks: 18, W3
  - Category: `unspecified-high` · Skills: [`readonly-connector`, `dcim-baseline`, `public-repo-safety`, `adr-decision`]
  - QA: `python3 -m unittest tests.test_automation_safety_boundary -v` GREEN; `make phase0-check`

- [ ] **12. `services/**`: create README index + 5 service scaffolds to turn TODO 3 green — expect pyproject + placeholder module with no import side effects**
  - What: Task 10 — `services/README.md`, per-service `README.md`/`pyproject.toml`/`src/<pkg>/{__init__,main}.py`; no `.sql`, no `.env`, no network/DB clients.
  - Depends: 3, 6 · Blocks: 18
  - Category: `unspecified-high` · Skills: [`programming`, `tdd`, `public-repo-safety`, `dcim-baseline`]
  - QA: `python3 -m unittest tests.test_service_scaffolds -v` GREEN; `python3 -m compileall -q services`; `make phase0-check`

- [ ] **13. `web/README.md`: record React scope and Phase 0 no-package.json decision — expect OD-03 language removed and layout documented**
  - What: Task 11.
  - Depends: 6 (confirm D-3) · Blocks: 18, W1
  - Category: `quick` · Skills: [`dcim-baseline`, `public-repo-safety`]
  - QA: `make phase0-check`

- [ ] **14. `docs/adr/0026-program-technology-version-baseline.md`: create Accepted ADR for Q8 — expect ES 9.x and PG 16 floor vs pinned 17.10 stated explicitly**
  - What: Task 8; needs the D-1 ruling.
  - Depends: D-1 owner answer · Blocks: 15, W2
  - Category: `unspecified-high` · Skills: [`adr-decision`, `dcim-baseline`, `public-repo-safety`]
  - QA: `make phase0-check`

### Wave 3 (After Wave 2)

- [ ] **15. Registers + gates: sync `docs/adr/README.md`, `OPEN-DECISIONS.md`, `CONDITIONS-REGISTER.md`, `AGENTS.md`, `Makefile` — expect TODO 2 fully green and gate docs matching reality**
  - What: Task 13 — crosswalk rows 0024–0027, OD-01/OD-07 ACCEPTED, owner-direction note (no closures), AGENTS.md ruff wording fixed, optional `make lint` target.
  - Depends: 5, 6, 7, 8, 9, 14 · Blocks: 16, 17, W1–W5
  - Category: `unspecified-high` · Skills: [`adr-decision`, `dcim-baseline`, `public-repo-safety`]
  - QA: `python3 -m unittest tests.test_decision_records -v` GREEN; `make phase0-check`

### Wave 4 (After Wave 3 — all parallel)

- [ ] **16. `docs/research/{PRD,DECISION-LOG-REVIEW,IMPLEMENTATION-PLAN,ARCHITECTURE}.md`: sync to accepted ADRs — expect no doc still calling OD-01/OD-07 open and Phase 0 tasks marked complete**
  - What: Task 14; wiki items become absolute URLs.
  - Depends: 15 · Blocks: 18
  - Category: `writing` · Skills: [`dcim-baseline`, `public-repo-safety`, `adr-decision`]
  - QA: `make markdown-links && make phase0-check`; grep shows no remaining "OD-01 ... OPEN"

- [ ] **17. `docs/research/DECISION-MATRIX.md`: create the OD/C/Q matrix — expect one row per decision with status, ADR, owner, deadline, evidence**
  - What: Task 15.
  - Depends: 15 · Blocks: 18
  - Category: `writing` · Skills: [`dcim-baseline`, `public-repo-safety`]
  - QA: `make phase0-check`; statuses match the authoritative registers

- [ ] **W1. `dcim-wiki/reference-designs/block5-web-dashboard.md`: replace Vue 3 with React to match ADR-0017/0024 — expect core ADRs cited as absolute URLs**
  - Depends: 15 · Blocks: 18 · Category: `writing` · Skills: [`public-repo-safety`, `dcim-baseline`]
  - QA: grep finds no Vue 3 target statement; all core links are `https://`

- [ ] **W2. `dcim-wiki/reference-designs/block1-infrastructure-provisioning.md`: set ES 9.x + PG 16 floor per ADR-0026 — expect pinned-17 nuance recorded**
  - Depends: 14, 15 · Blocks: 18 · Category: `writing` · Skills: [`public-repo-safety`, `dcim-baseline`]
  - QA: version table shows ES 9.x, PG 16 floor + note

- [ ] **W3. `dcim-wiki/reference-designs/siem-soar.md` (+ actual-architecture page): set TraceCat+Temporal SOAR and n8n non-destructive — expect safety preconditions stated**
  - Depends: 8, 11, 15 · Blocks: 18 · Category: `writing` · Skills: [`public-repo-safety`, `dcim-baseline`, `readonly-connector`]
  - QA: grep finds no "n8n as SOAR platform" claim; ADR-0025 URL present

- [ ] **W4. `dcim-wiki/reference-designs/block7-analytics-ai-engine.md`: record 2×RTX A5000 private LLM sizing per ADR-0027 — expect fallback data-boundary rule included**
  - Depends: 9, 15 · Blocks: 18 · Category: `writing` · Skills: [`public-repo-safety`, `dcim-baseline`]
  - QA: sizing + abstraction layer present; no endpoints or weights

- [ ] **W5. `dcim-wiki/README.md`: fix license/ownership statement to stop implying the core repo is private — expect ADR-0019 cited, wiki license left to owner**
  - Depends: 15, D-7 · Blocks: 18 · Category: `quick` · Skills: [`public-repo-safety`]
  - QA: statement no longer contradicts ADR-0019

### Wave 5 (After Wave 4)

- [ ] **18. `docs/evidence/2026-07-28-phase0-decision-lock.md` + `docs/phase0/evidence-index.md`: record gate results — expect PASS summary and explicit not-run list for Docker gates**
  - What: Task 17.
  - Depends: 1–17, W1–W5 · Blocks: 19
  - Category: `unspecified-high` · Skills: [`pr-evidence`, `dcim-baseline`, `public-repo-safety`]
  - QA: `make phase0-check` PASS recorded; `make markdown-links` PASS; no raw scanner output

### Wave 6 (Final)

- [ ] **19. PR assembly: build PRs A–D (core) + E (wiki) with completed templates — expect no push or PR creation before owner approval**
  - What: Task 18 — atomic commits per the Commit Strategy table, template sections filled, `git status` clean of unintended files.
  - Depends: 18 · Blocks: None
  - Category: `unspecified-high` · Skills: [`pr-evidence`, `git-master`, `public-repo-safety`, `code-review`]
  - QA: `git status --porcelain` shows only intended paths; no `.env*`/`.sql`/archive/`__pycache__`; owner approval recorded before any push

## Execution Instructions

1. **Get owner answers on D-1 and D-2 first** (they gate TODO 14 and TODO 5's form). D-3/D-4/D-6 have safe defaults; proceed on defaults and flag in the PR.

2. **Wave 1** — fire in parallel:
   ```
   task(category="writing",          load_skills=["dcim-baseline","public-repo-safety"], run_in_background=false, prompt="Task 1: write docs/research/PHASE0-PLAN.md ...")
   task(category="unspecified-low",  load_skills=["tdd","programming"], run_in_background=false, prompt="Task 2: red tests tests/test_decision_records.py ...")
   task(category="unspecified-low",  load_skills=["tdd","programming","public-repo-safety"], run_in_background=false, prompt="Task 2b: red tests tests/test_service_scaffolds.py ...")
   task(category="quick",            load_skills=["tdd","programming"], run_in_background=false, prompt="Task 3: red test tests/test_automation_safety_boundary.py ...")
   task(category="unspecified-high", load_skills=["adr-decision","dcim-baseline","public-repo-safety"], run_in_background=false, prompt="Task 4: accept ADR-0007 ...")
   task(category="unspecified-high", load_skills=["adr-decision","dcim-baseline","programming","public-repo-safety"], run_in_background=false, prompt="Task 5: create ADR-0024 ...")
   task(category="unspecified-high", load_skills=["adr-decision","dcim-baseline","readonly-connector","public-repo-safety"], run_in_background=false, prompt="Task 6: create ADR-0025 ...")
   task(category="unspecified-low",  load_skills=["adr-decision","dcim-baseline"], run_in_background=false, prompt="Task 7: ADR-0016 addendum ...")
   task(category="unspecified-high", load_skills=["adr-decision","dcim-baseline","public-repo-safety"], run_in_background=false, prompt="Task 12: create ADR-0027 ...")
   task(category="unspecified-high", load_skills=["public-repo-safety","dcim-baseline","readonly-connector"], run_in_background=false, prompt="Task 16: credential rotation procedure ...")
   ```

3. **Wave 2** — after Wave 1: TODOs 11, 12, 13, 14 in parallel (14 only once D-1 is answered).

4. **Wave 3** — TODO 15 alone (single-writer on the registers; never parallelize register edits).

5. **Wave 4** — TODOs 16, 17, W1, W2, W3, W4, W5 in parallel. Wiki tasks run in `/home/infra/dcim-wiki` on its own branch.

6. **Wave 5** — TODO 18: run `make phase0-check` and write the evidence record. Do not run `make preflight`/`foundation-*` in an agent session (Docker-dependent).

7. **Wave 6** — TODO 19: assemble PRs. Stop before pushing; wait for owner approval.

8. **Final QA**: all 11 Success Criteria verified; `make phase0-check` PASS; three new test modules green; `git status` clean of unintended files.

