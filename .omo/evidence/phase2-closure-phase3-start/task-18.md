# Task 18 Evidence: Full Compose Integration and Service Smoke Gate

Date: 2026-08-06
Branch: `feat/phase2-closure-phase3-start`
Starting HEAD: `7903748e7b9d684b4355adbfc73d5e160f6afa86`

All runtime data was synthetic Development data. Raw transcripts are outside Git under
`$DCIM_RUNTIME_ROOT/evidence-transcripts/`; this receipt contains only public-safe results.

## Baseline characterization before edits

The initial dirty worktree contained six pre-existing paths: `.codex/config.toml`, the
todo-19 API dashboard JSON decoder, the asset/workflow JSONB fixes, the workflow migration
grant, and its migration test. No file was edited before this baseline.

| Exact command | Exit | Binary observable | Artifact |
| --- | ---: | --- | --- |
| `rtk .venv/bin/python -m unittest tests/phase3/test_smoke.py tests/phase3/test_compose_core.py -v` | 0 | 16/16 tests passed | This receipt, focused baseline section |
| `rtk make service-smoke` | 0 | `service-smoke: PASS services=5/5 auth-denials=5/5` | `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-baseline-service-smoke.log` |

The dirty-state PASS did not prove commit `b9c959d` complete. A detached clean worktree at
the current committed `HEAD` was created and exercised with the same command:

| Exact command and working tree | Exit | Binary observable | Artifact |
| --- | ---: | --- | --- |
| `rtk make service-smoke` from detached clean `HEAD` | 2 | `service-smoke: FAIL: api: gateway asset create returned 500`; Compose stop still ran | `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-clean-head-service-smoke.log` |
| `rtk make service-smoke` after applying only the asset-repository, workflow, m0004 grant, and m0004 test changes (API dashboard change excluded) | 0 | 5/5 service PASS and 5/5 auth-denial PASS | `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-selected-fix-service-smoke.log` |

Conclusion: `b9c959d` supplies the compose/smoke implementation but is not complete by
itself. The selected JSONB and schema-usage repairs are directly required by its gateway
round-trip and workflow-lifecycle behavior. The dirty API dashboard change is todo-19 work
and was preserved but excluded from task 18.

## Failing-first regression characterization

The service fakes were changed to reproduce asyncpg's JSONB string boundary. Against clean
production code, the exact command below failed; after applying only the selected fixes it
passed.

| Exact command (detached worktree) | Exit | Binary observable |
| --- | ---: | --- |
| `rtk /home/infra/dcim-core-platform/.venv/bin/python -m unittest tests/phase3/test_asset_repository.py tests/phase3/test_workflow.py -v` before selected fixes | 1 | 10 tests ran: two asset errors and three workflow failures on JSONB string handling |
| same command after selected fixes | 0 | 10/10 tests passed |

## Auth-denial failure mutation and exact restore

Pre-mutation SHA-256 for `scripts/phase3/smoke.py` was
`5f6ed0c43377ece474de861800a75a16908da32e4cb11a00e1b9b3b68fad1378`.

Mutation applied with a targeted `apply_patch`:

```diff
-    if status != 403:
+    if status not in (200, 403):
```

`rtk .venv/bin/python -m unittest tests/phase3/test_smoke.py -v` exited 1: 12 tests
passed and `test_unauthenticated_probe_must_return_403` failed with
`SmokeFailure not raised`. This proves a weakened boundary that permits unauthenticated 200
cannot pass the focused suite.

Restore applied with the inverse targeted `apply_patch`:

```diff
-    if status not in (200, 403):
+    if status != 403:
```

`rtk sha256sum scripts/phase3/smoke.py` reproduced the exact pre-mutation digest above.
`rtk .venv/bin/python -m unittest tests/phase3/test_smoke.py tests/phase3/test_compose_core.py -v`
then exited 0 with 16/16 tests passing.

## Final verification on the candidate tree

| Exact command | Exit | Binary observable | Captured artifact |
| --- | ---: | --- | --- |
| `rtk make phase3-test` | 0 | 61 tests passed | `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-final-phase3-test.log` |
| `rtk make foundation-policy` | 0 | image qualification and `foundation-policy: PASS` | `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-final-foundation-policy.log` |
| `rtk make phase0-check` | 0 | compile, public safety (356 files), JSON (385 files), fixtures (9), links (296), 272 tests passed | `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-final-phase0-check.log` |
| `rtk make service-smoke` | 0 | all real Compose services healthy/ready/metric-bearing; all auth probes denied | `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-final-service-smoke.log` |

Manual Compose artifact:
`$DCIM_RUNTIME_ROOT/dev-build/evidence/service-smoke/evidence.json`, generated
`2026-08-06T17:34:39.107811Z`, SHA-256
`43f9de2034c8828d021737e3b4bec9cb0d092239ffbc7e9488ec4f229651a327`.

- `asset-repository`, `cmdb`, `api`, `analytics`, and `workflow`: health 200, readiness
  200, non-empty metrics (1899, 1913, 1912, 1897, and 1910 bytes respectively), and
  unauthenticated API denial 403.
- Aggregate result: `healthy_services=5`, `auth_denials=5`.
- Gateway synthetic asset: create/idempotent replay 200, read 200.
- Workflow synthetic draft: create 201, simulate 200, terminal re-simulation 409,
  final status `simulated_approved`.
- Analytics health, freshness, capacity, and quality endpoints: 200 with internal auth.
- The token value is absent from stdout, errors, and evidence.

## Adversarial QA

- `dirty_worktree`: initial six paths were recorded; only the four proven prerequisite
  paths, their two direct service tests, and this receipt belong to task 18. The API and
  `.codex/config.toml` changes remain untouched and uncommitted.
- `stale_state`: dirty-state PASS was challenged from detached clean `HEAD` and failed;
  the minimal selected patch then passed. Final evidence was regenerated and digest-checked.
  The deterministic asset's 200 replay also proves stale persisted state is idempotent.
- `hung_or_long_commands`: each Compose command used repository wait limits (180/240
  seconds), reached a terminal exit without polling/restart, and retained a non-empty raw
  transcript.
- `flaky_tests`: the 16-test focused suite passed before edits and after exact restore;
  the final 61-test Phase 3 suite passed independently.
- `misleading_success_output`: the PASS line was not trusted alone; `evidence.json` was
  parsed and independently showed five service records, five 403 denials, non-empty metrics,
  gateway/workflow/analytics results, and no token.
- `repeated_interruptions`: the clean-HEAD runtime failure interrupted the workflow at the
  gateway stage and still executed Compose stop; two later independent full starts passed
  and stopped cleanly.
- `malformed_input`: not applicable; no new external input parser or payload format was added.
- `prompt_injection`: not applicable; no LLM or untrusted prompt path exists in this gate.
- `cancel_resume`: not applicable; the gate is a bounded one-shot Compose invocation with
  no persisted resume protocol.

## Cleanup receipt

Exact cleanup command:

```bash
rtk env -u DCIM_COMPOSE_OVERRIDE COMPOSE_PROJECT_NAME=dcim-build docker compose --env-file /home/infra/.local/state/dcim-core-platform/runtime/dev-build/runtime.env --env-file /home/infra/.local/state/dcim-core-platform/runtime/dev-build/images.env -f deploy/compose/dev-build/compose.yaml --profile data --profile observability --profile core --profile dashboard --profile workflow down --timeout 60
```

Exit 0. The transcript records removal of all 11 `dcim-build` containers and both Compose
networks. Follow-up `docker ps -a` and `docker network ls` queries filtered by the Compose
project returned no rows. The task-created detached worktree was removed with
`rtk git worktree remove --force /tmp/dcim-task18-clean-head.LSdOEa` (exit 0). Pre-existing
persistent volumes and qualified images were preserved because they were not created by
this task.

Cleanup artifact: `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-final-cleanup.log`.

## Limits and disposition

This is synthetic Development evidence only. It makes no Staging, Production, HA, or SLA
claim. No live connector, office/Production access, DEV-INTEGRATION-RO, workflow execution,
image push, published host port, privileged/host namespace, credential logging, `.sql` file,
pytest, SQLAlchemy/ORM, or version range was introduced. The plan checkbox remains unticked
for orchestrator-owned independent verification.
