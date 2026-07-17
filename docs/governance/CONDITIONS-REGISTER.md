# Conditional-GO Register

Last baseline review: 2026-07-16

| ID | Priority | Condition | Development evidence required | Status |
|---|---:|---|---|---|
| C-01 | P1 | Written authorization and classification for every office/Production source | Private approval reference, owner, purpose, protocol, allowed reads, retention, and expiry | OPEN |
| C-02 | P1 | Public-repository safety baseline before substantive implementation | `.gitignore`, `.env.example`, security/data policies, CI scans, synthetic fixture policy, history review | IN PROGRESS |
| C-03 | P1 | Mutable DEV-BUILD separated from pinned DEV-INTEGRATION-RO | Separate projects/networks/volumes/env files; artifact promotion and rollback proof | OPEN |
| C-04 | P1 | Dedicated read-only credentials and negative write tests | Private credential-control record plus public synthetic tests proving prohibited methods unavailable | OPEN |
| C-05 | P1 | Demo uses synthetic or approved sanitized data only | Fixture provenance and sanitization/evidence checklist | OPEN |
| C-06 | P2 | Identity aliases, validity, confidence, and collision tests | Asset/CI schemas, alias model, conflict fixtures and deterministic resolution tests | OPEN |
| C-07 | P2 | Compose resource limits, retention, disk watermarks, and headroom | Versioned profile, capacity assumptions, alerts, load/smoke evidence | OPEN |
| C-08 | P2 | Hermes read-only allowlist, egress/memory policy, audit, limits, kill switch | Policy, threat model, test/eval evidence and disable procedure | OPEN |
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
