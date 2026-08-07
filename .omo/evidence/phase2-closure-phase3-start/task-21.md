# Todo 21 evidence — Phase 3 component deployment

Date: `2026-08-06` (UTC)

## Scope and baseline

`rtk omo ulw-loop status --json` exited `1` with `ULW_LOOP_PLAN_MISSING`; this
receipt is therefore stored under `.omo/evidence/phase2-closure-phase3-start/`.

Before editing, `rtk git status --short` showed exactly these unrelated dirty
paths, which this task preserved unstaged:

```text
.codex/config.toml
scripts/phase2/migrations/m0004_workflow_drafts.py
services/api/src/dcim_api/main.py
services/asset-repository/src/dcim_asset_repository/main.py
services/workflow/src/dcim_workflow/main.py
tests/phase2/test_phase2_migrations.py
```

The baseline was commit `9803e54b7091dd78567c9354bb1d90e44efbd12c` with
subject `docs(phase2): completion evidence package with streaming and latency ACs`.
Baseline SHA-256 values were recorded for `README.md`, `ROADMAP.md`,
`KNOWN-LIMITATIONS.md`, and `docs/governance/PLAN-DISPOSITIONS.md`; the final
integrity check confirmed that the first, third, and fourth are byte-identical.

Owner override recorded in both this receipt and the delivery document:
Todo 21 changes only `ROADMAP.md` and
`docs/evidence/2026-08-06-phase3-component-deployment.md`. No README or
`PLAN-DISPOSITIONS.md` change is authorized.

## Source inspection and artifact existence

The Todo 21 plan block, evidence guidance, P3-T1–P3-T7 scope, ADR-0007
security/handover requirements, Todos 12/13/18/19 receipts, Compose service
blocks, and Phase 3 tests were read before editing. The following exact
artifact-existence command was run:

```text
rtk run 'for path in docs/evidence/2026-08-06-phase3-component-deployment.md ROADMAP.md deploy/compose/dev-build/compose.yaml services/asset-repository/src/dcim_asset_repository/main.py services/cmdb/src/dcim_cmdb/main.py services/api/src/dcim_api/main.py services/analytics/src/dcim_analytics/main.py services/workflow/src/dcim_workflow/main.py .omo/evidence/phase2-closure-phase3-start/task-12.md .omo/evidence/phase2-closure-phase3-start/task-13.md .omo/evidence/phase2-closure-phase3-start/task-18.md .omo/evidence/phase2-closure-phase3-start/task-19.md schemas/asset.schema.json schemas/ci.schema.json tests/phase3/test_asset_repository.py tests/phase3/test_cmdb.py tests/phase3/test_workflow_safety.py tests/phase3/test_analytics.py tests/phase2/test_redfish_adapter_readonly.py tests/phase2/test_snmpv3_adapter_readonly.py tests/phase3/test_compose_core.py tests/phase3/test_smoke.py docs/research/IMPLEMENTATION-PLAN.md docs/adr/0007-cmdb-implementation-for-development.md; do test -f "$path"; rc=$?; printf "%s exit_code=%s\\n" "$path" "$rc"; test "$rc" -eq 0 || exit "$rc"; done'
```

Exit code: `0`. Every listed smoke, E2E, contract, negative-test, Compose,
source, schema, and scope artifact printed `exit_code=0`.

## Failing-first guard and exact restore

`apply_patch` created the otherwise-absent new delivery-document target with a
single synthetic forbidden-status marker. The exact guard below exited `1` and
printed nonempty matches for the temporary target marker and the then-existing
Roadmap future-release wording:

```text
rtk run 'matches=$(grep -Ein "production.ready|\\bHA\\b|\\bSLA\\b|phase 3 complete" docs/evidence/2026-08-06-phase3-component-deployment.md README.md ROADMAP.md KNOWN-LIMITATIONS.md); grep_rc=$?; printf "%s\\n" "$matches"; printf "grep_exit_code=%s\\n" "$grep_rc"; if test -n "$matches"; then printf "%s\\n" "final_guard_exit_code=1"; exit 1; fi; printf "%s\\n" "final_guard_exit_code=0"'
```

Observed result: `grep_exit_code=0`, `final_guard_exit_code=1`.
`apply_patch` then deleted the temporary target, restoring its prior absent
state. The exact restore verification was:

```text
rtk run 'test ! -e docs/evidence/2026-08-06-phase3-component-deployment.md; absent_rc=$?; sha256sum README.md ROADMAP.md KNOWN-LIMITATIONS.md docs/governance/PLAN-DISPOSITIONS.md; printf "marker_restore_absence_exit_code=%s\\n" "$absent_rc"'
```

Exit code: `0`; `marker_restore_absence_exit_code=0`. The final document was
created only after this byte-for-byte restore. No temporary file or runtime
resource remains.

## Local gates and manual QA

After the final endpoint wording correction, these exact commands were run on
the final staged content:

```text
rtk make markdown-links
rtk make public-safety
rtk make phase0-check
```

Each exit code was `0`. Observables: Markdown links `296`; public-safety scan
`356` files; Phase 0 gate ran `272` tests and completed compile, safety, JSON,
synthetic-fixture, and link validation.

The final full guard and staged-diff check were:

```text
rtk run 'matches=$(grep -Ein "production.ready|\\bHA\\b|\\bSLA\\b|phase 3 complete" docs/evidence/2026-08-06-phase3-component-deployment.md README.md ROADMAP.md KNOWN-LIMITATIONS.md); grep_rc=$?; test -z "$matches"; empty_rc=$?; printf "%s\\n" "$matches"; printf "grep_exit_code=%s\\nfinal_guard_empty_exit_code=%s\\n" "$grep_rc" "$empty_rc"; test "$empty_rc" -eq 0'
rtk git diff --cached --check
rtk git diff --cached --name-only
```

Each exit code was `0`; the guard reported `grep_exit_code=1` and
`final_guard_empty_exit_code=0`. The staged path allowlist was exactly:

```text
ROADMAP.md
docs/evidence/2026-08-06-phase3-component-deployment.md
```

The following exact integrity command exited `0`:

```text
rtk run 'test "$(sha256sum README.md | cut -d" " -f1)" = "68d7397421b32be0861ce01c69d9fe596927dbf402ac2e52116237586ca4d889"; readme_rc=$?; test "$(sha256sum KNOWN-LIMITATIONS.md | cut -d" " -f1)" = "13b82ada5876c8fd7c25eae2d2fa229debe08c865f735e391f165b3039fb4a71"; limitations_rc=$?; test "$(sha256sum docs/governance/PLAN-DISPOSITIONS.md | cut -d" " -f1)" = "677e2cebf8e5c3b77be9b894212e8ec25c59877916da59b133ee34096a8fd9ff"; dispositions_rc=$?; git diff --quiet -- .omo/plans/phase2-closure-phase3-start.md docs/governance/CONDITIONS-REGISTER.md docs/governance/PLAN-DISPOSITIONS.md README.md KNOWN-LIMITATIONS.md docs/phase0/staging-handover-contract.md; forbidden_rc=$?; printf "README_hash_exit_code=%s\\nKNOWN_LIMITATIONS_hash_exit_code=%s\\nPLAN_DISPOSITIONS_hash_exit_code=%s\\nforbidden_paths_unchanged_exit_code=%s\\n" "$readme_rc" "$limitations_rc" "$dispositions_rc" "$forbidden_rc"; test "$readme_rc" -eq 0 -a "$limitations_rc" -eq 0 -a "$dispositions_rc" -eq 0 -a "$forbidden_rc" -eq 0'
```

Its four named result codes were all `0`. A separate `rtk git diff --name-only`
inspection showed no `README.md`; the six baseline dirty paths remain the only
unrelated modified paths.

Manual QA classes: `dirty_worktree`, `stale_state`, `misleading_success_output`,
`hung_long_command`, and `flaky_tests` were covered by the baseline receipt,
dated source-artifact checks, prior Docker-receipt boundary, normal-hook
observation, and final rerun after the one documentation change. `malformed_input`,
`prompt_injection`, `cancel_resume`, and `repeated_interruptions` are not
applicable because no parser, untrusted input, resumable operation, or runtime
process was introduced. No containers, servers, ports, or temporary files were
created by this task.

## Commit hook blocker

The repository hook is verified as `exec make preflight`:

```text
rtk sed -n '1,80p' .git/hooks/pre-commit
```

Exit code: `0`. A normal commit was attempted twice (the second wrapped to
capture its status); the wrapped command exited `1` after the hook's preflight
path and left HEAD at `9803e54b7091dd78567c9354bb1d90e44efbd12c` with exactly
the two permitted paths staged:

```text
rtk run 'git commit -m "docs(phase3): component deployment evidence and program status update"; rc=$?; printf "normal_commit_exit_code=%s\\n" "$rc"; exit "$rc"'
```

This is the documented Docker-only preflight-hook blocker observed for Todo 20
as well. No bypass occurred before this blocker was recorded. The authorized
single bypass result and verification follow.

## Commit and final verification

The one authorized bypass was run after the blocker record:

```text
rtk git commit --no-verify -m "docs(phase3): component deployment evidence and program status update"
```

Exit code: `0`. The exact commit is
`7903748e7b9d684b4355adbfc73d5e160f6afa86` with subject
`docs(phase3): component deployment evidence and program status update`.

The final verification commands and results were:

```text
rtk git show -1 --format='%H%n%s' --name-only
rtk run 'actual=$(git show -1 --format= --name-only); expected="ROADMAP.md
docs/evidence/2026-08-06-phase3-component-deployment.md"; test "$actual" = "$expected"; rc=$?; printf "commit_path_allowlist_exit_code=%s\\n" "$rc"; exit "$rc"'
rtk run 'matches=$(grep -Ein "production.ready|\\bHA\\b|\\bSLA\\b|phase 3 complete" docs/evidence/2026-08-06-phase3-component-deployment.md README.md ROADMAP.md KNOWN-LIMITATIONS.md); grep_rc=$?; test -z "$matches"; empty_rc=$?; printf "%s\\n" "$matches"; printf "post_commit_guard_grep_exit_code=%s\\npost_commit_guard_empty_exit_code=%s\\n" "$grep_rc" "$empty_rc"; test "$empty_rc" -eq 0'
rtk run 'git diff --quiet -- README.md KNOWN-LIMITATIONS.md docs/governance/PLAN-DISPOSITIONS.md docs/governance/CONDITIONS-REGISTER.md STAGING-HANDOVER.md docs/phase0/staging-handover-contract.md .omo/plans/phase2-closure-phase3-start.md; rc=$?; printf "post_commit_forbidden_paths_unchanged_exit_code=%s\\n" "$rc"; exit "$rc"'
rtk run 'test -s .omo/evidence/phase2-closure-phase3-start/task-21.md; rc=$?; printf "task_evidence_nonempty_exit_code=%s\\n" "$rc"; exit "$rc"'
```

All commands exited `0`. The commit path allowlist code was `0`; the final
guard reported `post_commit_guard_grep_exit_code=1` and
`post_commit_guard_empty_exit_code=0`; the forbidden-path and evidence-nonempty
codes were both `0`.

Final status contains exactly the six preserved unrelated dirty paths listed
above and no staged change. No cleanup action is needed beyond the temporary
marker deletion already verified; no containers, servers, ports, or temporary
files remain.
