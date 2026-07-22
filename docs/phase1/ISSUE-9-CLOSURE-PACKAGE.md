# Issue #9 Closure Package Draft

Date: 2026-07-22
Status: draft; do not post or use for issue closure until remote checks, owner
disposition, and GitHub mutation are complete
Scope: synthetic `dcim-build` Runtime Plane only
Parent issue: #9
Governing ADRs: ADR-0013, ADR-0014, and ADR-0015

This file is a public-safe PR and issue-closure draft for the Phase 1 compact
infrastructure foundation. It intentionally separates closure-candidate evidence
from the owner-approved closure action. It does not close #9, mark Phase 1
owner-accepted, or claim Staging or Production readiness.

## Current disposition

Implementation status: closure candidate with clean-runtime and preflight evidence
captured.

Blocking closure gates:

1. isolated clean-runtime acceptance from a brand-new protected external root
   (PASS);
2. final `make preflight` on the exact final commit (PASS);
3. remote PR checks on the exact final head;
4. explicit owner disposition approving Phase 1 compact infrastructure
   foundation closure;
5. approved GitHub mutation to post the closure comment and close #9.

The issue #9 acceptance matrix remains the authoritative row-level tracker:
[`ISSUE-9-ACCEPTANCE-MATRIX.md`](ISSUE-9-ACCEPTANCE-MATRIX.md).

## PR action draft

Proposed GitHub action before owner-approved closure:

- open a draft PR from the closure-candidate branch to `main`;
- link #9 but do not use `Closes #9` until the clean-runtime, preflight, remote
  checks, and owner disposition gates are satisfied;
- do not change labels unless the owner explicitly approves exact label changes;
- do not mark `DEV-APPROVED`.

### PR body draft

````markdown
## Summary

Implements the issue #9 closure candidate for the Phase 1 compact infrastructure
foundation. The change adds an isolated clean-runtime acceptance entrypoint,
guardrail tests, corrected evidence semantics, and a PR-ready closure package
for the synthetic-only `dcim-build` Development foundation.
The acceptance entrypoint refuses both stale normal `dcim-build` Docker state
and stale generated acceptance namespace state before it mutates the new root.

This PR does not close #9 by itself. Parent issue closure remains pending:

- isolated clean-runtime acceptance from a brand-new protected external root;
- final `make preflight` on the exact final commit;
- remote checks on the exact final PR head;
- explicit owner disposition approving closure;
- approved GitHub issue closure action.

## Scope

- Synthetic `dcim-build` Runtime Plane only.
- `dcim-integration-ro` and `dcim-demo` remain contract-only and non-runnable.
- No connected source, connector activation, Hermes, workflow execution,
  infrastructure write/control path, P1/P2 vertical slice, HA, SLA, Staging, or
  Production readiness claim.

## Governing decisions

- ADR-0013 supersedes the original official-upstream-only parent requirement by
  allowing constrained local Development-only derived hardened images.
- ADR-0014 clarifies that PostgreSQL and Kafka use immutable official release
  binaries with checksum-verified source provenance for this scope.
- ADR-0015 accepts the full-source Prometheus v3.13.1 derivative required to
  preserve exact remediated dependency metadata in SBOM and vulnerability scans.
- Grafana OSS, Prometheus, and PostgreSQL exporter are full source builds.
- The JMX exporter Java runtime remains a qualified pinned upstream image.
- OD-06 remains OPEN; derived images are not published or distributed.

## Acceptance mapping

See `docs/phase1/ISSUE-9-ACCEPTANCE-MATRIX.md`.

Current classification before owner-approved runtime closure:

- verified by current evidence: 20;
- verified by isolated clean-runtime run: 25;
- superseded by accepted ADR: 2;
- out of scope according to issue #9: 1;
- owner disposition required: 1;
- pending remote-hosted runner evidence: 1;
- remaining issue #9 closure blockers: 2;
- unresolved implementation defects in this candidate: 0.

## Verification

Replace these placeholders in the GitHub PR body after the branch head is fixed
and all commit-bound checks have been rerun. Do not try to store the final
commit SHA in this committed draft; the commit would change when the draft is
amended.

```text
git diff --check 3a92960314df11d68152dc59244d31b93eaa9a57...<final-head>
PASS (no conflicts, no trailing whitespace issues)

python3 -m unittest tests.test_foundation_acceptance tests.test_foundation_smoke tests.test_foundation_policy tests.test_foundation_evidence_summary -q
98 tests passed

make phase0-check
210 tests passed

make foundation-clean-acceptance DCIM_RUNTIME_ROOT=<new-protected-root>
PASS
bootstrap: PASS
qualification/build: PASS
policy: PASS
supply-chain: PASS
startup: PASS
fast smoke: PASS
recovery and PostgreSQL restore: PASS
bounded stop: PASS
public-safe summary: PASS
Evidence: phase1-clean-acceptance-summary.json (external runtime evidence)

make preflight
exit 0
210 tests
foundation supply-chain: PASS
foundation recovery: PASS
foundation evidence summary: PASS
```

Remote checks on exact final PR head:

```text
preflight: <pending>
dependency-review: <pending>
public-safety: <pending>
synthetic foundation fast smoke: <pending>
pinned image SBOM, license, and vulnerability gate: <pending>
```

Read-only reviews on exact final diff/head:

```text
Standards review: <pending>
Spec review: <pending>
Security review: <pending>
```

## Public data declaration

This PR contains only public-safe code, configuration, tests, documentation, and
synthetic evidence summaries. It does not add live or suspected-live endpoints,
credentials, source identities, topology, raw payloads, logs, captures, dumps,
screenshots, operational prompts, image IDs, scanner reports, SBOMs, runtime
state, or private authorization records.

Raw runtime evidence remains under the protected external runtime root and is
not committed.

## Dependency, license, and supply-chain result

- No Python package dependency is added by this closure package.
- No repository license decision is made; OD-06 remains OPEN.
- The governed effective six-image set remains the ADR-0013/0014 set:
  PostgreSQL, Kafka, Prometheus, Grafana OSS, PostgreSQL exporter, and JMX
  exporter Java runtime.
- Final closure requires the supply-chain gate to report zero Critical, zero
  fixable High, and zero undispositioned unfixable High findings on the exact
  final commit.
- Derived hardened images remain local Development artifacts and must not be
  published or distributed.

## Migration review

No database schema, persisted application contract, or repository data migration
is introduced by this closure package. Runtime volumes are preserved by stop and
down. Any runtime cleanup requires a separate owner-approved allowlist.

## Rollback

Revert this PR to remove the issue #9 clean-runtime acceptance guardrails and
closure-package documentation. Runtime state is external and is not deleted by
rollback. If a derived image or supply-chain input needs rollback, re-pin the
last qualified compatible reference and rerun qualification, policy, smoke,
recovery, and preflight gates.

## Limitations and non-claims

- Single-broker Development-only Kafka; no HA, SLA, durability, scalability, or
  Production hardening claim.
- No P1/P2 vertical slice, ingestion, normalization, validation, DLQ,
  enrichment, Asset/CI context, analytics, workflow, SIEM/SOAR, or NOC
  application behavior.
- No Kafka backup claim.
- No office or Production source access.
- No Staging or Production readiness.
- C-03, C-05, C-07, and OD-06 remain unchanged unless the owner separately
  approves exact status changes.
````

## Issue #9 closure action draft

Proposed GitHub action after every closure gate passes:

- post the public-safe comment below to issue #9;
- close issue #9;
- do not change condition-register or open-decision statuses unless the same
  owner disposition explicitly authorizes each exact change;
- no label change is proposed by default.

### Issue comment draft

````markdown
Phase 1 compact infrastructure foundation closure evidence is complete for the
synthetic-only `dcim-build` Development scope.

Final commit: `<final-head-sha>`

Acceptance matrix:

- verified by current evidence: 20;
- verified by isolated clean-runtime run: 25;
- superseded by accepted ADR: 2;
- out of scope according to issue #9: 1;
- owner disposition required: 1;
- pending remote-hosted runner evidence: 1;
- unresolved/blocking rows: 2.

Clean-runtime acceptance:

```text
make foundation-clean-acceptance DCIM_RUNTIME_ROOT=<new-protected-root>
exit 0
bootstrap: PASS
qualification/build: PASS
policy: PASS
supply-chain: PASS
startup: PASS
fast smoke: PASS
recovery and PostgreSQL restore: PASS
bounded stop: PASS
public-safe summary: PASS
```

Final preflight:

```text
make preflight
exit 0
<total test count>
foundation supply-chain: PASS
foundation recovery: PASS
foundation evidence summary: PASS
```

Remote checks on the exact final PR head:

```text
preflight: <pending>
dependency-review: <pending>
public-safety: <pending>
synthetic foundation fast smoke: <pending>
pinned image SBOM, license, and vulnerability gate: <pending>
```

Reviews:

```text
Standards review: <pending>
Spec review: <pending>
Security review: <pending>
```

Public-data declaration: repository and issue content contain only public-safe
code, configuration, tests, documentation, and concise synthetic evidence
summaries. Raw runtime evidence, scanner reports, SBOMs, dumps, runtime IDs,
secrets, and mutable state remain under protected external runtime storage and
outside Git.

ADR reconciliation: ADR-0013, ADR-0014, and ADR-0015 supersede the original
official-upstream-only image requirement for five local Development-only derived
hardened images. Only the JMX exporter Java runtime remains a qualified upstream
image. The original official-only NO-GO evidence is preserved.

Limitations and non-claims: this closes only the Phase 1 compact infrastructure
foundation for synthetic `dcim-build`. It does not claim P1/P2 vertical slices,
connected-source integration, Hermes, workflow execution, Kafka backup, HA, SLA,
Staging readiness, Production authorization, or Production hardening.

Conditions/open decisions: C-03, C-05, C-07, and OD-06 remain unchanged unless
separately approved by the owner.

Owner disposition: `<owner approval text/date>`
````

Do not post this comment or close #9 until the placeholders are replaced with
the exact final evidence and the owner explicitly approves the closure action.
