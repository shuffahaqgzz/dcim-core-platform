# Phase 1 Development Handover

Date: 2026-07-21
Status: PR-ready
Issue: #12
Parent: #9
Branch: `feat/issue-12`

## What was delivered

The reproducible Development acceptance package for the qualified synthetic
foundation. This handover turns the verified lifecycle (issue #11) into
reviewable evidence and handover material.

## Acceptance criterion mapping

| # | Issue #12 AC | Artifact | Verification |
|---|---|---|---|
| 1 | Clean runtime root completes full lifecycle on Ubuntu 24.04 | `make preflight` target; `scripts/foundation_evidence_summary.py` | `make preflight` exits 0; evidence summary generated |
| 2 | All gates pass with no critical failure | `make preflight` (phase0-check + foundation-supply-chain + foundation-recovery + foundation-evidence-summary) | Exit code 0; 155+ tests pass |
| 3 | Code review confirms standards and security boundary | This PR; code review against `origin/main` | No connector, control, privileged, or bridge paths introduced |
| 4 | Public-safe evidence records allowlisted fields only | `scripts/foundation_evidence_summary.py`; `tests/test_foundation_evidence_summary.py` | 13 tests validate allowlist enforcement |
| 5 | Runbooks document lifecycle, recovery, failure, Grafana, limitations | `docs/phase1/FOUNDATION-RUNBOOK.md` | Covers all required sections |
| 6 | Handover PR-ready; C-03, C-05, C-07, OD-06 unchanged | This document; conditions register unchanged | No condition status modified |

## Changed files

| File | Change |
|---|---|
| `scripts/foundation_evidence_summary.py` | New: public-safe evidence summary generator |
| `tests/test_foundation_evidence_summary.py` | New: 13 tests for evidence summary |
| `Makefile` | Extended: added `foundation-evidence-summary` target and included it in `preflight` |
| `docs/phase1/FOUNDATION-RUNBOOK.md` | New: lifecycle, recovery, failure handling, Grafana access, limitations, non-claims |
| `docs/phase1/DEVELOPMENT-HANDOVER.md` | New: this document |

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
| `make compile` | Python compileall | exit 0 |
| `make test` | 155+ unit tests | exit 0 |
| `make public-safety` | Public repo safety scan | exit 0 |
| `make validate-json` | Schema validation | exit 0 |
| `make validate-fixtures` | Fixture inventory | exit 0 |
| `make markdown-links` | Link checker | exit 0 |

## Evidence

- Raw evidence: `${DCIM_RUNTIME_ROOT}/dev-build/evidence/` (external, not in Git)
- Summary: `make foundation-evidence-summary` (stdout or file)
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

1. Owner reviews this PR and evidence;
2. Owner decides whether to mark issue #12 closed;
3. Subsequent issues address remaining Phase 1 breadth as governed.
