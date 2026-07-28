# Conditional-GO Register

Last baseline review: 2026-07-20

| ID | Priority | Condition | Development evidence required | Status |
|---|---:|---|---|---|
| C-01 | P1 | Written authorization and classification for every office/Production source | Private approval reference, owner, purpose, protocol, allowed reads, retention, and expiry | OPEN |
| C-02 | P1 | Public-repository safety baseline before substantive implementation | `.gitignore`, `.env.example`, security/data policies, CI scans, synthetic fixture policy, history review | CLOSED |
| C-03 | P1 | Mutable DEV-BUILD separated from pinned DEV-INTEGRATION-RO | Separate projects/networks/volumes/env files; artifact promotion and rollback proof | OPEN |
| C-04 | P1 | Dedicated read-only credentials and negative write tests | Private credential-control record plus public synthetic tests proving prohibited methods unavailable | OPEN |
| C-05 | P1 | Demo uses synthetic or approved sanitized data only | Fixture provenance and sanitization/evidence checklist | OPEN |
| C-06 | P2 | Identity aliases, validity, confidence, and collision tests | Asset/CI schemas, alias model, conflict fixtures and deterministic resolution tests | OPEN |
| C-07 | P2 | Compose resource limits, retention, disk watermarks, and headroom | Versioned profile, capacity assumptions, alerts, load/smoke evidence | OPEN |
| C-08 | P2 | Hermes read-only allowlist, egress/memory policy, audit, limits, kill switch | Policy, threat model, test/eval evidence and disable procedure | DEFERRED |
| C-09 | P2 | Connector polling/source-impact controls | Per-source ceilings, timeout/retry policy, metrics and stop test | OPEN |
| C-10 | P2 | Cost ceiling before any paid external service | Owner-approved budget, account/usage controls and exit plan | DEFERRED |

## Auto NO-GO

Stop and escalate on any of the following:

1. Secret or live/suspected-live operational data appears in public Git, issue, PR, CI, prompt, or evidence.
2. A connected-source credential can write/control without an approved exception.
3. SNMP SET, Redfish/ISAPI write/action, power/reset, PTZ, firmware, raw shell, or similar operation is reachable without governed controls.
4. Office data can egress to an unapproved external AI, CI, logging, or telemetry service.
5. Source authorization/classification is absent or expired.
6. A collector or Hermes access path cannot be stopped quickly.
7. A Critical quality/security/recovery gate fails.

## Status rules

- Only the owner or named future authority changes a condition to `CLOSED`.
- Public evidence links may be recorded here; private authorization references remain outside Git.
- `COMPENSATING CONTROL` requires owner acceptance, expiry, and a follow-up closure date.

## Owner dispositions

### C-02

- Disposition: `CLOSED`
- Date: 2026-07-20
- Owner: `shuffahaqgzz`
- Basis: PR #2, #4, #6; current-main [full-history scan run 29716219940](https://github.com/shuffahaqgzz/dcim-core-platform/actions/runs/29716219940) against `4ea16f287864e2c44044fcb12c0c1e2fd450b85c`; Phase 0 preflight PASS; exact-head security and governance reviews PASS.
- Scope: public repository safety and Development entry.
- Boundary: does not authorize Production connection, connector activation, Staging entry, or Production approval.

### C-05

- Disposition: remains `OPEN`
- Reason: synthetic fixtures, provenance validation, and sanitizer controls pass, but no executable DEV-DEMO path has been deployed or accepted.
- Phase 0 treatment: not blocking repository-safety completion.
- Closure trigger: executable demo path uses synthetic or separately approved sanitized data and passes provenance, sanitization, and public-safety gates.

## Owner direction 2026-07-27

Owner: `shuffahaqgzz`. Recorded from the governance review session on 2026-07-27.
No condition below is marked `CLOSED` by this section; closure still requires the
registered evidence per row.

### C-01 — direction recorded

- `dev-v0.1.0` exit is **synthetic-only**; no office/Production source connection
  is required for this milestone.
- C-01 remains `OPEN` and is blocking **only** for the first activation of the
  `DEV-INTEGRATION-RO` runtime plane.
- First candidate source class when integration is activated: Redfish read-only
  against server BMC (server health, a P1 candidate in the baseline).
- The authorization register template already exists at
  [`docs/templates/private-source-authorization-register.template.md`](../templates/private-source-authorization-register.template.md);
  filled records stay in the owner-managed private store outside Git.

### C-03 — direction recorded

- The current structural separation (separate Compose profiles; `dcim-build`
  runnable; `dcim-integration-ro` and `dcim-demo` contract-only and non-runnable)
  is accepted as sufficient for Development.
- Closure path: public design evidence plus a negative test proving the
  integration plane cannot start without manual promotion. Remains `OPEN` until
  that evidence artifact is recorded.

### C-04 — direction recorded

- Public synthetic negative tests proving write/control methods are unavailable
  are accepted as the public-side evidence.
- The credential-control record is held and reviewed by the owner in a private
  store outside Git. The store location is deliberately not recorded in this
  public repository.

### C-05 — direction recorded

- The executable DEV-DEMO path must be a **dedicated demo profile**, separate
  from the test pipeline.
- Evidence: automated provenance, sanitization, and public-safety gates only; no
  owner witness session required. Keep the demo path as simple as possible.

### C-06 — direction recorded

- Closure path: a final ADR fixing identity alias/conflict resolution rules
  (ADR-0020, **Accepted 2026-07-27**), followed by deterministic
  conflict/collision tests. Remains `OPEN` until the tests pass and the run is
  linked as evidence.

### C-07 — direction recorded

- Owner-set values: Kafka retention **30 days**; disk watermark thresholds
  **low 85% / high 90% / flood-stage 95%**.
- Per-service memory/CPU caps: engineer-recommended, accepted via ADR-0021
  (**Accepted 2026-07-27**). Remains `OPEN` until the Compose caps, alerts,
  and load/smoke usage evidence are recorded and linked.

### C-08 — DEFERRED

- Disposition: `DEFERRED`
- Date: 2026-07-27
- Owner: `shuffahaqgzz`
- Basis: Hermes is out of scope for `dev-v0.1.0`; OD-05 (Hermes model/inference)
  is likewise deferred.
- Closure trigger: before any Hermes shadow work starts — allowlist, egress and
  memory policy, audit, resource limits, kill switch, and GPU fit evidence.

### C-09 — direction recorded

- Closure path: engineer-researched default polling/source-impact controls,
  accepted via ADR-0023 (**Accepted 2026-07-27**). Remains `OPEN` until the
  connector policy schema, ceiling negative tests, and stop test pass and are
  linked as evidence.

## Owner direction 2026-07-28

Owner: `shuffahaqgzz`. Recorded from the 2026-07-28 decision lock.
No condition below is marked `CLOSED` by this section; closure still requires the
registered evidence per row.

### Decision lock recorded

- OD-01 → [ADR-0007](../adr/0007-cmdb-implementation-for-development.md)
  (Accepted 2026-07-28): custom PostgreSQL CMDB service for Phase 1–2;
  iTop/NetBox are read-only discovery sources behind the canonical adapter.
- OD-07 → [ADR-0024](../adr/0024-python-fastapi-service-language-baseline.md)
  (Accepted 2026-07-28): Python 3.12 + FastAPI + Pydantic v2 core services;
  TypeScript + React + Vite frontend per [ADR-0017](../adr/0017-react-noc-dashboard-frontend.md).
- PRD Q3 (SOAR platform roles) recorded via ADR-0016 addendum.
- PRD Q4 (automation execution preconditions) recorded via
  [ADR-0025](../adr/0025-automation-execution-preconditions.md).
- PRD Q8 (program technology version baseline) recorded via
  [ADR-0026](../adr/0026-program-technology-version-baseline.md).
- PRD Q7 (private LLM serving baseline) recorded via
  [ADR-0027](../adr/0027-private-llm-serving-baseline.md).

### Condition status

None of the C-0x rows change status due to this section. Each remains in its
registered state and still needs its registered evidence before the owner or
named authority may mark it `CLOSED`.
