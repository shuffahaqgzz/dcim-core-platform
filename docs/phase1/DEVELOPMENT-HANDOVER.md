# Phase 1 Development Handover

Date: 2026-07-21
Status: Closure candidate with clean-runtime and local preflight candidate
evidence captured; final pushed-head binding, remote evidence, final review, and
owner disposition remain pending
Issue: #12; closure package for parent #9
Parent: #9
Branch: PR #16 draft branch; exact final pushed head remains commit-bound at
publication time

## What was delivered

The reproducible Development acceptance package for the qualified synthetic
foundation. This handover now includes candidate reused-state baseline evidence
and isolated clean-runtime evidence. Exact final pushed-head binding remains
pending at publication time.

## Acceptance criterion mapping

| # | Issue #12 AC | Artifact | Verification |
|---|---|---|---|
| 1 | Clean runtime root completes full lifecycle on Ubuntu 24.04 | `make foundation-clean-acceptance DCIM_RUNTIME_ROOT=<new-protected-root>`; `scripts/foundation_acceptance.py` | Candidate isolated clean-runtime summary recorded; rebind to exact final pushed head remains pending if the branch changes |
| 2 | All gates pass with no critical failure | `make preflight` plus clean acceptance summary | Candidate/local evidence captured; final pushed-head remote/Docker gate evidence remains pending |
| 3 | Code review confirms standards and security boundary | Candidate review evidence; exact final issue #9 diff/head review pending | No connector, control, privileged, or bridge paths identified in the candidate; final pushed-head review remains required |
| 4 | Public-safe evidence records allowlisted fields only | `scripts/foundation_evidence_summary.py`; `tests/test_foundation_evidence_summary.py` | 13 tests validate allowlist enforcement |
| 5 | Runbooks document lifecycle, recovery, failure, Grafana, limitations | `docs/phase1/FOUNDATION-RUNBOOK.md` | Covers all required sections |
| 6 | Handover PR-ready candidate; C-03, C-05, C-07, OD-06 unchanged | This document; conditions register unchanged | No condition status modified; owner disposition remains pending |

## Changed files

| File | Change |
|---|---|
| `scripts/foundation_evidence_summary.py` | New: public-safe evidence summary generator |
| `scripts/foundation_acceptance.py` | New: isolated clean-runtime acceptance orchestrator |
| `tests/test_foundation_evidence_summary.py` | Evidence summary safety and acceptance-gate tests |
| `tests/test_foundation_acceptance.py` | Clean-runtime guardrail tests |
| `Makefile` | Extended: added `foundation-evidence-summary` and `foundation-clean-acceptance` targets; `preflight` remains the normal Development gate |
| `docs/phase1/FOUNDATION-RUNBOOK.md` | New: lifecycle, recovery, failure handling, Grafana access, limitations, non-claims |
| `docs/phase1/DEVELOPMENT-HANDOVER.md` | New: this document |
| `docs/phase1/ISSUE-9-ACCEPTANCE-MATRIX.md` | New: parent issue #9 row-level closure tracker |
| `docs/phase1/ISSUE-9-CLOSURE-PACKAGE.md` | New: PR body and issue closure comment draft |

## Conditions and open decisions

| ID | Status | Impact of this work |
|---|---|---|
| C-03 | OPEN | Structural separation advanced by foundation design; not closed |
| C-05 | OPEN | Demo plane remains non-executable; not affected |
| C-07 | OPEN | Resource/retention evidence advanced by smoke and recovery; not closed |
| OD-06 | OPEN | Repository license decision unchanged |

No condition status was changed by this work. Only the owner may change
condition status.

## Tests and exit codes

| Command | Tests | Result |
|---|---|---|
| `make compile` | Python compileall | candidate evidence exit 0 |
| `make test` | 210 unit tests | candidate evidence PASS |
| `make public-safety` | Public repo safety scan | candidate evidence exit 0 |
| `make validate-json` | Schema validation | candidate evidence exit 0 |
| `make validate-fixtures` | Fixture inventory | candidate evidence exit 0 |
| `make markdown-links` | Link checker | candidate evidence PASS |
| `make preflight` | 210 tests + foundation gate outputs | candidate/local evidence captured; final pushed-head CI/milestone-host Docker gate evidence pending |

## Evidence

- Candidate raw evidence: `${DCIM_RUNTIME_ROOT}/dev-build/evidence/` (external,
  not in Git), including `phase1-clean-acceptance-summary.json` and acceptance
  smoke/recovery records. Exact final pushed-head rebinding remains pending.
- Normal reused-state summary: `make foundation-evidence-summary` (stdout or file)
- Clean-runtime summary: `make foundation-clean-acceptance DCIM_RUNTIME_ROOT=<new-protected-root>`
- Evidence fields: commit, image digests, capability profiles, UTC timestamp,
  duration, assertion result, synthetic run ID
- Prohibited fields: hostname, runtime_root, environment, credential, container,
  password, secret, token, key

## Limitations

- Single-broker Kafka KRaft: no HA, durability, or Production claim;
- No P1 or P2 vertical slice demonstrated;
- No application-layer behavior (normalize, validate, DLQ, enrichment, Asset/CI,
  analytics, workflow, SIEM/SOAR, NOC);
- No event-to-dashboard latency measurement under workload;
- No Kafka backup claim;
- No continuous host-level telemetry;
- No office or Production source access;
- No Staging or Production readiness.

## Explicit non-claims

This handover does not claim:

- HA, SLA, scalability, or durability;
- Staging entry or Production readiness;
- Connected-source integration or Hermes access;
- Write or control operations against any infrastructure;
- Remote or network access to any service;
- Closure of any condition or open decision.

## Unresolved risks

1. Derived hardened images (ADR-0013/0014) remain local Development artifacts.
   Clean official upstream images are preferred replacements.
2. OD-06 (repository license) remains OPEN. No publication, distribution, or
   release claim is permitted.
3. Grafana OSS AGPL obligations require explicit review before any distribution.
4. Docker Desktop and remote-daemon behavior are not claimed.

## Next steps

1. Fix and publish the exact final branch head, then bind closure text to that
   SHA outside the committed draft;
2. Rerun or explicitly reclassify commit-bound local candidate checks, including
   clean-runtime acceptance and `make preflight`, for the exact final head on an
   authorized CI or milestone host;
3. Obtain remote PR checks and Docker-dependent gate evidence on the exact final
   pushed head;
4. Complete standards, spec, and security review against the exact final issue
   #9 diff/head;
5. Fill the PR and issue closure drafts in
   [`ISSUE-9-CLOSURE-PACKAGE.md`](ISSUE-9-CLOSURE-PACKAGE.md) with exact final
   evidence;
6. Owner reviews the issue #9 closure package and decides whether to approve any
   GitHub mutation or close #9;
7. Subsequent issues address remaining Development baseline breadth as governed.
