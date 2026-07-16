---
name: pr-evidence
description: Use before opening or completing a pull request, declaring a task done, marking DEV-APPROVED, or preparing Development handover evidence.
---

# Pull Request and Evidence Gate

1. Compare the branch with its base and map every change to acceptance criteria.
2. Run `make preflight` and component-specific lint, unit, contract, integration, E2E, migration, and recovery checks as applicable.
3. Delegate read-only reviews to reviewer and security_reviewer for non-trivial changes; reconcile their findings before completion.
4. Inspect dependencies and licenses; pin versions and container digests when introduced.
5. Ensure the PR body contains commands/results, public-data declaration, rollback behavior, limitations, and linked issue/ADR.
6. Store only concise public-safe evidence. Do not attach raw logs, payloads, screenshots, or environment exports.
7. Never mark `DEV-APPROVED` when a critical gate or P1 condition is open for the claimed scope.
8. A Development approval is not Staging or Production authorization.
