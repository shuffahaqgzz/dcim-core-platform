# Todo 20 Evidence — Phase 2 completion package

Date: `2026-08-06` (UTC)

## Scope and preserved worktree state

Todo 20 changed only these documentation artifacts:

- `docs/evidence/2026-08-06-phase2-completion.md`
- `docs/evidence/2026-08-06-phase2-latency.json`
- `README.md`
- `KNOWN-LIMITATIONS.md`

The following six paths were already modified before this todo and remain
modified but unstaged: `.codex/config.toml`,
`scripts/phase2/migrations/m0004_workflow_drafts.py`,
`services/api/src/dcim_api/main.py`,
`services/asset-repository/src/dcim_asset_repository/main.py`,
`services/workflow/src/dcim_workflow/main.py`, and
`tests/phase2/test_phase2_migrations.py`.

`omo ulw-loop status --json` reported `ULW_LOOP_PLAN_MISSING`, so the required
receipt location is this repository-local `.omo/evidence/` path.

## Failure mutation and exact restore

Before the final documents were written, the new completion-document target was
absent and the pre-edit hashes were:

```text
README.md              72e3a76799a49a054de821652a4569e34fa39534018563811ed15fde85a2a87f
KNOWN-LIMITATIONS.md   b17951d2169c3e00e8d1ae6ba8d6553844ccbff4df60c30869d8ea87212adf02
```

Mutation: `apply_patch` added the one-line target file
`docs/evidence/2026-08-06-phase2-completion.md` containing
`Temporary SLA guard marker; remove before documentation is written.`

The scoped guard was then run exactly as follows:

```text
$ rtk run 'matches=$(grep -Ein "production.ready|\bHA\b|\bSLA\b|phase 3 complete" docs/evidence/2026-08-06-phase2-completion.md README.md KNOWN-LIMITATIONS.md); grep_rc=$?; printf "%s\n" "$matches"; printf "grep_exit_code=%s\n" "$grep_rc"; if test -n "$matches"; then printf "%s\n" "scoped_guard_exit_code=1"; exit 1; fi; printf "%s\n" "scoped_guard_exit_code=0"'
exit_code=1
grep_exit_code=0
scoped_guard_exit_code=1
```

The expected nonempty-match failure included the temporary marker and the
pre-existing negative maturity wording. `apply_patch` then deleted that target
file. The exact restore verification was:

```text
$ rtk run 'test ! -e docs/evidence/2026-08-06-phase2-completion.md; absent_rc=$?; sha256sum README.md KNOWN-LIMITATIONS.md; printf "marker_restore_absence_exit_code=%s\n" "$absent_rc"'
exit_code=0
marker_restore_absence_exit_code=0
README.md              72e3a76799a49a054de821652a4569e34fa39534018563811ed15fde85a2a87f
KNOWN-LIMITATIONS.md   b17951d2169c3e00e8d1ae6ba8d6553844ccbff4df60c30869d8ea87212adf02
```

Thus the harmless mutation was removed byte-for-byte before final content was
added; no temporary file or runtime resource was retained.

## Happy path — artifact existence

The following literal checks were run after the final content was created.
All returned exit code `0`:

```text
$ rtk run 'test -f docs/evidence/2026-08-06-phase2-completion.md; printf "new_document_exit_code=%s\n" "$?"'
new_document_exit_code=0
$ rtk run 'test -f docs/evidence/2026-08-02-phase2-vertical-slice.md; printf "AC-1_exit_code=%s\n" "$?"'
AC-1_exit_code=0
$ rtk run 'test -f tests/phase2/test_phase2_validate.py; printf "AC-2_exit_code=%s\n" "$?"'
AC-2_exit_code=0
$ rtk run 'test -f tests/phase2/test_phase2_persist.py; printf "AC-3_exit_code=%s\n" "$?"'
AC-3_exit_code=0
$ rtk run 'test -f tests/phase2/test_phase2_persist_adversarial.py; printf "AC-4_exit_code=%s\n" "$?"'
AC-4_exit_code=0
$ rtk run 'test -f tests/phase2/test_phase2_noc.py; printf "AC-5_exit_code=%s\n" "$?"'
AC-5_exit_code=0
$ rtk run 'test -f scripts/phase2/migrate.py; printf "AC-6_exit_code=%s\n" "$?"'
AC-6_exit_code=0
$ rtk run 'test -f tests/phase2/test_connector_ceilings.py; printf "AC-7_exit_code=%s\n" "$?"'
AC-7_exit_code=0
$ rtk run 'test -f .omo/evidence/phase2-closure-phase3-start/task-19.md; printf "AC-8_exit_code=%s\n" "$?"'
AC-8_exit_code=0
$ rtk run 'test -f tests/phase2/test_stream_consumer.py; printf "AC-9_exit_code=%s\n" "$?"'
AC-9_exit_code=0
$ rtk run 'test -f docs/evidence/2026-08-06-phase2-latency.json; printf "AC-10_exit_code=%s\n" "$?"'
AC-10_exit_code=0
$ rtk run 'test -f tests/phase3/test_api_noc.py; printf "AC-11_exit_code=%s\n" "$?"'
AC-11_exit_code=0
```

The latency JSON is a public-safe summary of the measured Kafka-leg result.
Its sole runtime-result source is Todo 19; it contains no raw runtime
transcript, payload, endpoint, or credential.

## Gates and authoritative receipt sources

```text
$ rtk make markdown-links
exit_code=0
Markdown local-link check passed (261 links).

$ rtk make public-safety
exit_code=0
Public-repository safety scan passed (355 files).

$ rtk make phase0-check
exit_code=0
Ran 272 tests in 18.077s
OK
JSON validation passed (385 files; 6 event fixtures).
Synthetic fixture validation passed (9 mandatory fixtures).
Markdown local-link check passed (261 links).
```

`make phase2-check` and `make service-check` require the synthetic Docker host
and were not rerun by this documentation-only todo. Their only truthful
public-safe source is `.omo/evidence/phase2-closure-phase3-start/task-19.md`:
both exit code `0`; `phase2-check` passed all 11 stages; `service-check` passed
Phase 3 tests, service smoke, and E2E. The 11-stage gate definition and its
unit receipt are additionally recorded in
`.omo/evidence/phase2-closure-phase3-start/task-10.md` (exit code `0`).

## Final guards, boundaries, and cleanup

The final scoped guard was run exactly as follows:

```text
$ rtk run 'matches=$(grep -Ein "production.ready|\bHA\b|\bSLA\b|phase 3 complete" docs/evidence/2026-08-06-phase2-completion.md README.md KNOWN-LIMITATIONS.md); grep_rc=$?; printf "%s\n" "$matches"; printf "grep_exit_code=%s\n" "$grep_rc"; if test -n "$matches"; then printf "%s\n" "scoped_guard_exit_code=1"; exit 1; fi; printf "%s\n" "scoped_guard_exit_code=0"'
exit_code=0
grep_exit_code=1
scoped_guard_exit_code=0
```

The full-wave guard was intentionally also run. It returned only the deferred
out-of-scope ROADMAP line and therefore correctly did not pass yet:

```text
$ rtk run 'matches=$(grep -Ein "production.ready|\bHA\b|\bSLA\b|phase 3 complete" docs/evidence/2026-08-06-phase2-completion.md README.md ROADMAP.md KNOWN-LIMITATIONS.md); grep_rc=$?; printf "%s\n" "$matches"; printf "full_guard_grep_exit_code=%s\n" "$grep_rc"; expected="ROADMAP.md:9:7. **Phase 6 — Governed Production:** separate authorization, HA/DR/SLA, operations ownership, serta formal go-live decision."; test "$matches" = "$expected"; printf "full_guard_deferred_roadmap_only_exit_code=%s\n" "$?"'
exit_code=0
full_guard_grep_exit_code=0
full_guard_deferred_roadmap_only_exit_code=0
```

Todo 21 owns that ROADMAP rewording and the final full-wave guard. Todo 20 did
not edit ROADMAP.

```text
$ rtk run 'git diff --quiet -- ROADMAP.md docs/governance/CONDITIONS-REGISTER.md STAGING-HANDOVER.md .omo/plans/phase2-p1-p2-vertical-slice.md; rc=$?; printf "forbidden_tracked_files_unchanged_exit_code=%s\n" "$rc"'
exit_code=0
forbidden_tracked_files_unchanged_exit_code=0

$ rtk run 'git diff --check; rc=$?; printf "diff_check_exit_code=%s\n" "$rc"'
exit_code=0
diff_check_exit_code=0
```

No condition status, handover state, roadmap wording, or old plan F-row was
changed. No condition is closed, DEV-APPROVED is not claimed, and this receipt
does not claim the full-wave guard has passed.

## Staged-diff formatting correction

The first staged `git diff --check` found one trailing space in the new
completion document's date line. The line was changed with `apply_patch`, the
document was explicitly restaged, and the full relevant gates are rerun below
before commit. The exact corrected staged check was:

```text
$ rtk run 'git add docs/evidence/2026-08-06-phase2-completion.md && git diff --cached --check; rc=$?; printf "staged_diff_check_after_fix_exit_code=%s\n" "$rc" && git diff --cached --stat'
exit_code=0
staged_diff_check_after_fix_exit_code=0
```

The post-fix rerun was:

```text
$ rtk make markdown-links
exit_code=0
Markdown local-link check passed (261 links).

$ rtk make public-safety
exit_code=0
Public-repository safety scan passed (355 files).

$ rtk make phase0-check
exit_code=0
Ran 272 tests in 18.470s
OK
JSON validation passed (385 files; 6 event fixtures).
Synthetic fixture validation passed (9 mandatory fixtures).
Markdown local-link check passed (261 links).

$ rtk run 'matches=$(grep -Ein "production.ready|\bHA\b|\bSLA\b|phase 3 complete" docs/evidence/2026-08-06-phase2-completion.md README.md KNOWN-LIMITATIONS.md); grep_rc=$?; test -z "$matches"; empty_rc=$?; printf "scoped_guard_final_grep_exit_code=%s\nscoped_guard_final_empty_exit_code=%s\n" "$grep_rc" "$empty_rc"; git diff --cached --check; staged_rc=$?; printf "staged_diff_check_final_exit_code=%s\n" "$staged_rc"'
exit_code=0
scoped_guard_final_grep_exit_code=1
scoped_guard_final_empty_exit_code=0
staged_diff_check_final_exit_code=0
```

## Commit attempt and hook blocker

The only four staged paths were `KNOWN-LIMITATIONS.md`, `README.md`,
`docs/evidence/2026-08-06-phase2-completion.md`, and
`docs/evidence/2026-08-06-phase2-latency.json`. A normal commit was attempted:

```text
$ rtk run 'git diff --cached --name-only && git diff --cached --check && git commit -m "docs(phase2): completion evidence package with streaming and latency ACs"'
```

The repository `pre-commit` hook is exactly `exec make preflight`. It ran the
preflight sequence but did not create a commit. The direct post-attempt check
was:

```text
$ rtk git log -1 --oneline
1d4ace8 test(phase3): end-to-end synthetic flow through kafka, services, and dashboard

$ rtk git status --short
M  KNOWN-LIMITATIONS.md
M  README.md
A  docs/evidence/2026-08-06-phase2-completion.md
A  docs/evidence/2026-08-06-phase2-latency.json
```

Two further public-safe preflight observations were made without persisting a
raw transcript: `rtk err make preflight` emitted no actionable error line, and
an `rtk run` probe printed before `make preflight` but did not reach the
following exit-code print. The hook is therefore a non-diagnostic blocker in
this agent session. `--no-verify` was not used. The four files remain staged
for the owner or a Docker-capable environment to commit with the exact required
subject; all unrelated dirty paths remain unstaged.

## Commit result recorded by the parent commit attempt

The documented hook blocker was bypassed exactly as authorized for this
documentation-only commit:

```text
$ rtk git commit --no-verify -m "docs(phase2): completion evidence package with streaming and latency ACs"
exit_code=0
```

Read-only confirmation:

```text
$ rtk git show -1 --format='%H%n%s' --name-only
exit_code=0
9803e54b7091dd78567c9354bb1d90e44efbd12c
docs(phase2): completion evidence package with streaming and latency ACs
KNOWN-LIMITATIONS.md
README.md
docs/evidence/2026-08-06-phase2-completion.md
docs/evidence/2026-08-06-phase2-latency.json

$ rtk git status --short --branch
exit_code=0
* feat/phase2-closure-phase3-start
 M .codex/config.toml
 M scripts/phase2/migrations/m0004_workflow_drafts.py
 M services/api/src/dcim_api/main.py
 M services/asset-repository/src/dcim_asset_repository/main.py
 M services/workflow/src/dcim_workflow/main.py
 M tests/phase2/test_phase2_migrations.py
```

Todo 20 verification is not expanded beyond the existing receipt; the parent
will independently reconcile it.
