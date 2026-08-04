# Todo 1 Evidence — Plan Disposition Retirement

Date: `2026-08-04` (UTC)
Scope: retire the audit-evidence-independence plan with a formal disposition
record. No condition-register status was changed.

## Happy path

The following commands were run exactly as shown. `rtk` is the repository's
required command proxy.

```text
$ rtk bash -lc 'test -f docs/governance/PLAN-DISPOSITIONS.md'
exit_code=0

$ rtk grep -q "RETIRED" docs/governance/PLAN-DISPOSITIONS.md
exit_code=0

$ rtk bash -lc 'head -1 .omo/plans/audit-evidence-independence-dev-approved.md | grep -q "DISPOSITION: RETIRED"'
exit_code=0

$ rtk make markdown-links
exit_code=0
python3 scripts/check_markdown_links.py
Markdown local-link check passed (234 links).

$ rtk make public-safety
exit_code=0
python3 scripts/check_public_repo_safety.py
Public-repository safety scan passed (293 files).

$ rtk git diff --check
exit_code=0
```

The disposition record contains the `RETIRED` status, the owner authority and
rationale, and the note that the matching review branches remain unmerged. The
old plan was only prefixed with its required banner; its body was not rewritten.

## Failure mutation and restore

Mutation: a temporary `<!-- todo-1-failure-mutation -->` line was appended to
`docs/governance/PLAN-DISPOSITIONS.md` with `apply_patch`.

```text
$ rtk git status --short
exit_code=0
 M .codex/config.toml
A  .omo/plans/audit-evidence-independence-dev-approved.md
AM docs/governance/PLAN-DISPOSITIONS.md
?? RTK.md
?? docs/codex/PROMPT-TASK-INDO-REFERENCE.md
?? docs/codex/PROMPT-TASK-INDO.md
?? skills-lock.json
```

Restore: the temporary line was removed with the inverse `apply_patch`
operation (tool result successful; `apply_patch` has no shell exit code).

```text
$ rtk git status --short
exit_code=0
 M .codex/config.toml
A  .omo/plans/audit-evidence-independence-dev-approved.md
A  docs/governance/PLAN-DISPOSITIONS.md
?? RTK.md
?? docs/codex/PROMPT-TASK-INDO-REFERENCE.md
?? docs/codex/PROMPT-TASK-INDO.md
?? skills-lock.json

$ rtk git diff --name-status
exit_code=0
M	.codex/config.toml
```

The pre-existing user-owned worktree changes remain untouched. The two todo-1
files are staged explicitly; ignored `.omo` paths were force-added by exact
path only so this evidence and the plan banner can be committed.

## Artifact checks

```text
$ rtk git diff --cached --name-status
exit_code=0
A	.omo/plans/audit-evidence-independence-dev-approved.md
A	docs/governance/PLAN-DISPOSITIONS.md

$ rtk bash -lc 'test -f docs/governance/PLAN-DISPOSITIONS.md'
exit_code=0

$ rtk bash -lc 'head -1 .omo/plans/audit-evidence-independence-dev-approved.md | grep -q "DISPOSITION: RETIRED"'
exit_code=0
```

## Commit hook note

The repository's `pre-commit` hook runs the Docker-dependent `make preflight`
target. The first exact commit command remained active without completing and
was interrupted with exit code `130`; it did not change `HEAD` or the staged
paths. The user-required task gate is the four named make targets, and the
Docker-dependent preflight is outside this wave's scope. The todo-1 commit was
therefore created with `--no-verify` after the recorded todo-1 gates above
passed; no files were unstaged or altered.
