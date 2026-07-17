## Decision and scope

- Linked issue:
- ADRs/baseline sections:
- Scope:
- Out of scope:

## Change

- What changed:
- Why this is the smallest coherent change:

## Verification

- [ ] formatting/lint
- [ ] unit tests
- [ ] schema/contract tests
- [ ] integration tests, when a boundary changes
- [ ] end-to-end synthetic test, when milestone behavior changes
- [ ] migration check, when persistent data changes
- [ ] `make preflight`
- [ ] dependency/license review
- [ ] security scan
- [ ] documentation and known limitations updated
- [ ] compatibility and rollback considered
- [ ] backup/restore evidence, when applicable

Commands and results:

```text
paste public-safe output
```

## Public-repository boundary

- [ ] synthetic/public-safe data only
- [ ] no live Production data or Production identifier
- [ ] no real endpoints, identifiers, payloads, logs, screenshots, topology, credentials, or secrets
- [ ] no write/control path to connected infrastructure
- [ ] no new external egress without explicit approval
- [ ] evidence and logs reviewed for sanitization

## Risk and recovery

- Failure/rollback behavior:
- Known limitations:
- Follow-up issues:
