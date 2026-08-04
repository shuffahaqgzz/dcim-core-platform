# Todo 3 Evidence — Phase 2 Vertical-Slice Plan Sync

Date: `2026-08-04` (UTC)
Scope: synchronize tasks 1, 3, 5, 6, 9, 12, and 13 in
`.omo/plans/phase2-p1-p2-vertical-slice.md`. F1–F4 remain unticked.

## Artifact checks before ticking

Every referenced repository artifact was checked before the plan lines were
changed. All checks passed; no referenced artifact was missing.

```text
$ rtk bash -lc 'test -f docs/adr/0028-duplicate-disposition-and-deterministic-identity.md'
exit_code=0
$ rtk bash -lc 'test -f scripts/phase2/manifest.py'
exit_code=0
$ rtk bash -lc 'test -f scripts/phase2/ledger.py'
exit_code=0
$ rtk bash -lc 'test -f connectors/redfish/adapter.py'
exit_code=0
$ rtk bash -lc 'test -f connectors/snmp/adapter.py'
exit_code=0
$ rtk bash -lc 'test -f scripts/phase2/run.py'
exit_code=0
$ rtk bash -lc 'test -f scripts/phase2/persist.py'
exit_code=0
$ rtk bash -lc 'test -f scripts/phase2/check.py'
exit_code=0
$ rtk bash -lc 'test -f Makefile'
exit_code=0
$ rtk bash -lc 'test -f .github/workflows/ci.yml'
exit_code=0
$ rtk bash -lc 'test -f docs/evidence/2026-08-02-phase2-vertical-slice.md'
exit_code=0
```

The PR references are historical references from the owner-approved plan; the
file checks above cover every concrete path named beside those references.

## Happy path result

Each newly checked task has one completion-reference line immediately below
its heading. The final verification rows were not changed except for the
required annotation directly above F1.

```text
$ rtk grep -c '\- \[x\]' .omo/plans/phase2-p1-p2-vertical-slice.md
exit_code=0
13

$ rtk grep -c 'SUPERSEDED-PENDING' .omo/plans/phase2-p1-p2-vertical-slice.md
exit_code=0
1

$ rtk grep -c '\- \[ \] F' .omo/plans/phase2-p1-p2-vertical-slice.md
exit_code=0
4

$ rtk git diff --check
exit_code=0
```

## Failure mutation and restore

Mutation: the task 3 completion reference was temporarily changed from
`scripts/phase2/manifest.py` to the nonexistent
`scripts/phase2/manifest-missing.py`.

```text
$ rtk bash -lc 'test -f scripts/phase2/manifest-missing.py'
exit_code=1
```

Restore: the completion reference was changed back with the inverse
`apply_patch` operation (tool result successful; `apply_patch` has no shell
exit code). The restored artifact and plan invariants were then checked:

```text
$ rtk bash -lc 'test -f scripts/phase2/manifest.py'
exit_code=0

$ rtk grep -c '\- \[x\]' .omo/plans/phase2-p1-p2-vertical-slice.md
exit_code=0
13

$ rtk grep -c 'SUPERSEDED-PENDING' .omo/plans/phase2-p1-p2-vertical-slice.md
exit_code=0
1

$ rtk grep -c '\- \[ \] F' .omo/plans/phase2-p1-p2-vertical-slice.md
exit_code=0
4
```
