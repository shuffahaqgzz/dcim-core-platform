# Todo 2 Evidence — PR #19 Closure Disposition

Date: `2026-08-04` (UTC)
Scope: close PR #19 with the owner disposition comment and map its coverage in
`docs/governance/PLAN-DISPOSITIONS.md`.

## Happy path

The following commands were run exactly as shown. `rtk` is the repository's
required command proxy.

```text
$ rtk gh pr view 19 --json state --jq .state
exit_code=0
OPEN

$ rtk gh pr close 19 --comment "Closed per owner decision 2026-08-03 (plan phase2-closure-phase3-start). Intent (synthetic fixture contract compatibility / transport-enum parity across schema and validators) is superseded by the merged phase2-check gate and re-covered by service contract-parity tests in tests/phase3/ (todos 12, 13)."
exit_code=0
✓ Closed pull request #19 (feat(contracts): add synthetic fixture contract compatibility gate)

$ rtk gh pr view 19 --json state --jq .state
exit_code=0
CLOSED

$ rtk gh pr view 19 --json comments --jq '.comments[-1].body'
exit_code=0
Closed per owner decision 2026-08-03 (plan phase2-closure-phase3-start). Intent (synthetic fixture contract compatibility / transport-enum parity across schema and validators) is superseded by the merged phase2-check gate and re-covered by service contract-parity tests in tests/phase3/ (todos 12, 13).

$ rtk gh pr list --state open
exit_code=0
Pull Requests
  [open] #18 chore(actions): bump actions/checkout from 7.0.0 to 7.0.1 (app/dependabot)
  [open] #17 chore(actions): bump actions/setup-python from 6.3.0 to 7... (app/dependabot)

$ rtk grep -q "PR #19" docs/governance/PLAN-DISPOSITIONS.md
exit_code=0

$ rtk make markdown-links
exit_code=0
python3 scripts/check_markdown_links.py
Markdown local-link check passed (239 links).

$ rtk git diff --quiet -- docs/governance/CONDITIONS-REGISTER.md
exit_code=0
```

PR #19 is closed with the required comment. Only the two expected Dependabot
pull requests remain open; neither was modified.

## Failure mutation and restore

Mutation: a temporary `<!-- todo-2-failure-mutation -->` line was appended to
the disposition register with `apply_patch`.

```text
$ rtk git status --short -- docs/governance/PLAN-DISPOSITIONS.md
exit_code=0
 M docs/governance/PLAN-DISPOSITIONS.md
```

Restore: the temporary line was removed with the inverse `apply_patch`
operation (tool result successful; `apply_patch` has no shell exit code).
The PR comment and remote PR state were not mutated during this local failure
test.

```text
$ rtk git diff --check
exit_code=0
```
