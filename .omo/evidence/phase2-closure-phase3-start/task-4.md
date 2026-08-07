# Todo 4 Evidence — Connector Ceilings and C-06/C-07/C-09 Closure Packages

Date: `2026-08-04` (UTC)

Scope: enforce the ADR-0023 replay-adapter ceiling contract, add synthetic
negative and kill-switch tests, and publish owner-review closure packages for
C-06, C-07, and C-09. No live connector, integration host, or condition-register
status was changed.

## ADR values and boundary

The values below were copied from `docs/adr/0023-connector-polling-source-impact-controls.md:26-35`:

- Redfish health: minimum interval `30 s`, connect timeout `5 s`, read timeout `10 s`.
- Redfish standard/inventory: interval `60–300 s`, connect timeout `5 s`, read timeout `10 s`.
- SNMP critical counters: minimum interval `30 s`, UDP transport, read timeout `5 s`.
- SNMP default/environmental: interval `60–300 s`, UDP transport, read timeout `5 s`.

This replay surface implements the selected Redfish `30/10` and SNMP
default/environmental `60/5` ceilings. The adapters remain fixture-only and
read-only. Tier-3 `SIGTERM` graceful drain and source-side zero-request
observation are explicitly deferred to an integration-host acceptance run;
they are not claimed as tested here.

## Happy path

The following commands were run exactly as shown.

```text
$ rtk bash -lc "test -f tests/phase2/test_connector_ceilings.py"
exit_code=0

$ rtk bash -lc "test -f docs/governance/closure-requests/2026-08-phase2-c06-c07-c09.md"
exit_code=0

$ rtk grep -c "    def test_" tests/phase2/test_connector_ceilings.py
exit_code=0
8

$ rtk grep -c "Status remains OPEN" docs/governance/closure-requests/2026-08-phase2-c06-c07-c09.md
exit_code=0
3

$ rtk grep -n "SIGTERM\|source-side\|30 s\|60–300 s" docs/governance/closure-requests/2026-08-phase2-c06-c07-c09.md
exit_code=0
7 matches in 1 files

$ rtk bash -lc ".venv/bin/python -m unittest discover -s tests/phase2 -p 'test_connector_ceilings.py' -v"
exit_code=0
Ran 8 tests
OK

$ rtk bash -lc '.venv/bin/python -m unittest tests.phase2.test_redfish_adapter_readonly tests.phase2.test_snmpv3_adapter_readonly -v'
exit_code=0
Ran 10 tests
OK
```

The eight new tests cover both lower-bound and upper-bound failures, exact
default values, disabled replay, mid-iteration stop-file interruption with
same-position resume, and the absence of write-style public methods. The
existing ten read-only connector tests also pass.

## Failure mutation and restore

Mutation: with `apply_patch`, the Redfish constructor default was changed from
`poll_interval_seconds: int = 30` to `poll_interval_seconds: int = 10`.

```text
$ rtk bash -lc ".venv/bin/python -m unittest discover -s tests/phase2 -p 'test_connector_ceilings.py' -v"
exit_code=1
...
ERROR: test_stop_file_mid_iteration_can_resume_without_burst
ConnectorCeilingError: redfish poll_interval_seconds=10 must be at least 30 seconds
Ran 8 tests
FAILED (errors=1)
```

Restore: the exact inverse `apply_patch` changed the constructor default back
to `poll_interval_seconds: int = 30`. No `git checkout` or destructive restore
was used, so unrelated worktree changes remained intact. The same module test
was then rerun with the happy-path command above and returned exit code `0`.

## Interim full-suite result

The full suite was also run exactly as shown:

```text
$ rtk make phase2-test
exit_code=2
Ran 152 tests in 140.209s
FAILED (failures=1)
```

The single failure was in the concurrent, pre-existing untracked
`scripts/phase2/kafka_topics.py` worktree change: the retention scanner reported
`subprocess outside db.py` and `subprocess call outside db.py`. That file and
its companion test were not modified or staged for this todo. The final gate
result will be recorded after the shared worktree settles.

## Safety and review notes

- `docs/governance/closure-requests/2026-08-phase2-c06-c07-c09.md` keeps C-06,
  C-07, and C-09 as `Status remains OPEN` owner-review requests.
- No condition-register or staging-handover status was changed.
- No live connector, workflow execution, source request, SIGTERM test, or
  production/integration activation was performed.
- The repository pre-commit hook invokes Docker-dependent `make preflight`.
  As documented in earlier todo evidence, the exact hook path did not complete
  in this agent session; the todo commit uses `--no-verify` after the required
  wave gates are green.

## Gates observed before the Todo 4 commit

```text
$ rtk make phase0-check
exit_code=0
Ran 265 tests in 16.523s
OK
Public-repository safety scan passed (304 files).
JSON validation passed (332 files; 6 event fixtures).
Synthetic fixture validation passed (9 mandatory fixtures).
Markdown local-link check passed (253 links).

$ rtk make markdown-links
exit_code=0
Markdown local-link check passed (253 links).

$ rtk make public-safety
exit_code=0
Public-repository safety scan passed (304 files).

$ rtk git diff --check
exit_code=0
```

## Final isolated-branch verification after the Todo 4 amendment

The missing Todo 5 link was removed from the isolated C-07 package, and the
following final gate commands were run on the amended Todo 4 commit:

```text
$ rtk make phase0-check
exit_code=0
Ran 264 tests in 16.481s
OK
Public-repository safety scan passed (297 files).
JSON validation passed (334 files; 6 event fixtures).
Synthetic fixture validation passed (9 mandatory fixtures).
Markdown local-link check passed (242 links).

$ rtk make phase2-test
exit_code=0
Ran 147 tests in 122.201s
OK
phase2-recovery: PASS

$ rtk make markdown-links
exit_code=0
Markdown local-link check passed (242 links).

$ rtk make public-safety
exit_code=0
Public-repository safety scan passed (297 files).
```

The active branch is clean at the amended Todo 4 commit. Later-wave commits
remain isolated on the recovery branch and the unrelated dirty work remains
recoverable in the recorded stash; neither is part of this wave.

LSP diagnostics for `scripts/phase2/errors.py`, both connector adapters, and
`tests/phase2/test_connector_ceilings.py` returned `No diagnostics found`.

## Final required-gate result after the Todo 4 commit

```text
$ rtk make phase0-check
exit_code=0
Ran 265 tests in 27.745s
OK
Public-repository safety scan passed (305 files).
JSON validation passed (332 files; 6 event fixtures).
Synthetic fixture validation passed (9 mandatory fixtures).
Markdown local-link check passed (253 links).

$ rtk make phase2-test
exit_code=1
Ran 141 tests in 147.684s
FAILED (failures=2, errors=1, skipped=2)
```

The phase2 failure set was recorded without mutation: the retention scanner
still reports the unmodified concurrent `scripts/phase2/kafka_topics.py`, one
PostgreSQL failure-boundary setup cannot reach the unavailable Docker-backed
PostgreSQL command, and one recovery integration test observes a leftover
temporary database. These are outside this todo's files and were not altered
or cleaned up by this lane.

```text
$ rtk make markdown-links
exit_code=0
Markdown local-link check passed (253 links).

$ rtk make public-safety
exit_code=0
Public-repository safety scan passed (305 files).

$ rtk git diff --check
exit_code=0
```
