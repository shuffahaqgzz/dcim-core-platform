# Contributing

The project is in owner-led prototype/alpha Development. External contribution terms remain limited until a license is selected.

## Before starting

1. Read `AGENTS.md`, `DATA-HANDLING.md`, the development baseline, and relevant ADRs.
2. Create or link a GitHub issue with explicit acceptance criteria.
3. Confirm that the task does not require live office/Production data.
4. For an unresolved architectural choice, submit an ADR before implementation.

## Local verification

```bash
./scripts/bootstrap-dev.sh
make preflight
```

Component-specific test commands must be documented in the nearest README and in the pull request.

## Pull requests

Keep one coherent concern per pull request. Include scope/out-of-scope, linked issue or ADR, commands and results, data-handling declaration, migration/recovery impact, and known limitations.

The owner may mark a Development result `DEV-APPROVED` only after required evidence exists. That status is not Staging or Production approval.
