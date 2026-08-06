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

## Rejected-gate recovery closure

This section supersedes the two missing acceptance proofs identified by
`.omo/evidence/task-18-gate-review.md`. The immutable code commit exercised below is
`0031b3d8367d5950a948f8960aad06c6cc9f2fa1`. Its parent is the rejected task-18 commit
`8d4b78ad5a33c27c3e67b35470a344f3d1811719`; its exact subject is
`feat(phase3): full service compose integration and smoke gate`.

The recovery lane did not observe the requested initial state. It observed `0031b3d...`
already committed with only `.codex/config.toml` dirty. Direct inspection proved that the
new commit contains only the API NOC JSONB decoder and its failing-first unittest. The
unrelated `.codex/config.toml` remained untouched. No history was rewritten.

### Exact code-SHA gates

| Scenario | Exact invocation | UTC interval | Exit | Binary observable | Protected artifact |
| --- | --- | --- | ---: | --- | --- |
| Required final service gate | `rtk make service-check` | 2026-08-06T18:05:40Z to 18:10:35Z | 0 | 62 Phase 3 unittests passed; service smoke reported 5/5 services and 5/5 auth denials; E2E reported zero loss, dashboard visibility, and p95 1586.489334 ms; final `service-check: PASS` | `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-fix-final-service-check.log` (24,715 bytes, SHA-256 `607c905d6aeef655c887c72aa47d8228bccb7205510846d9d073c37534001fbe`) |
| Compose policy | `rtk make foundation-policy` | 2026-08-06T18:15:50Z | 0 | qualified images reused and `foundation-policy: PASS` | `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-fix-final-foundation-policy.log` (652 bytes, SHA-256 `95ef6a819fb2ef4a6f1f48e964d543ef3fd2cee17cd2c6ca45a26580e9be3fd9`) |
| Repository gate | `rtk make phase0-check` | 2026-08-06T18:15:56Z to 18:16:20Z | 0 | compile, public safety (356 files), JSON (385 files), fixtures (9), links (296), and 272 unittests passed | `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-fix-final-phase0-check.log` (44,705 bytes, SHA-256 `e0496a63118b40fee4941b417b714974af16fc52d747fd01f6a0f81c8cc3d3f1`) |
| Pre-commit public boundary | `rtk make public-safety` | 2026-08-06T18:19:00Z to 18:19:03Z | 0 | public-repository safety scan passed for 356 files | `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-fix-precommit-public-safety.log` (247 bytes, SHA-256 `6acc7c5866c2929f59ebb8adf517676eac81975474fb82ebf7a429f42e58bc77`) |
| API JSONB failing-first probe | Detached `0031b3d...`; reverse only `services/api/src/dcim_api/main.py`; run `rtk /home/infra/dcim-core-platform/.venv/bin/python -m unittest tests/phase3/test_api_noc.py -v`; remove worktree; run `rtk .venv/bin/python -m unittest tests/phase3/test_api_noc.py -v` | 2026-08-06T18:16:35Z to 18:16:38Z | expected 1, then 0 | Without the decoder, the JSONB payload remained encoded text and the new test failed; committed code passed 6/6. Temporary worktree removal exited 0. | `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-fix-jsonb-failing-first.log` (3,653 bytes, SHA-256 `f87fa315fab78caddf9c75892ad8f4ebff4c6bbe800313a661f1962970920109`) |

The service-check-generated smoke artifact contains exactly five service records,
`healthy_services=5`, and `auth_denials=5`. Its E2E artifact records
`zero_silent_loss=true`, `dashboard_visibility=true`, matching producer/consumer counts,
and the bounded p95 above. These protected JSON artifacts remain under
`$DCIM_RUNTIME_ROOT/dev-build/evidence/`; no credential value is present.

### Real-stack CMDB stop, failure, restore

At code SHA `0031b3d8367d5950a948f8960aad06c6cc9f2fa1`, the repository Compose command with
profiles `data`, `observability`, `core`, `dashboard`, and `workflow` started all services
with `up -d --wait --wait-timeout 240`. The exact failure/restore sequence was:

1. `docker compose ... stop --timeout 60 cmdb` exited 0.
2. The already-stopped CMDB container was removed with the same bounded Compose project
   using `docker compose ... rm -f cmdb`, so a retained container address could not mask
   the outage.
3. `python3 scripts/phase3/smoke.py --output <protected-cmdb-stopped-output>` exited 1
   with `service-smoke: FAIL: cmdb: no reachable container address`.
4. `docker compose ... up -d --wait --wait-timeout 120 cmdb` exited 0 and reported CMDB
   healthy.
5. The same real smoke command using the correct protected token exited 0 with
   `services=5/5 auth-denials=5/5`.

The sequence ran 2026-08-06T18:14:21Z to 18:15:42Z. Protected transcript:
`$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-fix-cmdb-stop-restore-final.log`
(7,283 bytes, SHA-256
`9ee7974a44244b701b6338e7870842ada088a18fbf3d9ce23758b76e7b03d58f`).

### Real-stack wrong-token failure and restore

At the same code SHA, a mode-0600 printable synthetic wrong-token file was generated under
the protected transcript directory without printing its value. Against the running real
Compose services, host-side unauthenticated probes recorded exactly:

- `asset-repository_unauth_status=403`
- `cmdb_unauth_status=403`
- `api_unauth_status=403`
- `analytics_unauth_status=403`
- `workflow_unauth_status=403`

`python3 scripts/phase3/smoke.py --token-file <protected-wrong-token> --output
<protected-wrong-token-output>` then exited 1 with
`api: gateway asset create returned 403`, proving the authenticated round-trip failed after
all five unauthenticated denials. The temporary wrong-token file was removed. The same smoke
command without `--token-file` restored the correct protected default token without reading
or printing it and exited 0 with `services=5/5 auth-denials=5/5`.

Protected transcript:
`$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-fix-real-stack-mutations-final.log`
(7,839 bytes, SHA-256
`863d92780a9e83831fb79f9750b92321dca651871a018d1aaf78b8c2a07861f6`).
A preliminary binary wrong-token attempt was rejected as invalid UTF-8 before authentication;
it was not counted, and the full valid-input scenario above was rerun from stack start through
restore and cleanup.

### Cleanup and adversarial probes

Before recovery, the prior lane had left 11 `dcim-build` containers and two networks. The
bounded all-profile `docker compose ... down --timeout 60` exited 0, after which project
container and network counts were both zero and all three pre-existing named volumes remained.
Receipt: `$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-fix-initial-cleanup.log`
(2,246 bytes, SHA-256
`2e2a708f217fb68fa4d5c9fcc035e039da23d3a84905a11c6df3cdae0daadd31`). Each final mutation
scenario repeated the same bounded down operation; the final observable was containers 0,
networks 0, volumes preserved 3. No image or volume was removed, the wrong-token temporary
file is absent, and the detached regression worktree is absent.

The first normal commit attempt ran the repository pre-commit `make preflight` hook. Phase 0,
supply-chain, policy, and foundation recovery passed, but the hook exited nonzero because
`foundation-evidence-summary --strict-commit` found the hook-generated recovery artifact was
not bound to immutable code SHA `0031b3d...`; no commit was created. The hook-created six
foundation containers and two networks were removed with the same bounded all-profile down
command at 2026-08-06T18:23:39Z to 18:23:42Z. Final counts were containers 0, networks 0,
volumes preserved 3. Protected cleanup receipt:
`$DCIM_RUNTIME_ROOT/evidence-transcripts/task18-fix-post-hook-cleanup.log` (1,430 bytes,
SHA-256 `9880f8ce4c6d7e0dfa60251ce8fd350aeaf9bfd3cb734c8700e6066f0aafe0db`). The evidence-only
commit therefore uses the repository's documented `--no-verify` recovery path after the normal
hook failure; this does not replace or weaken any separately captured task gate.

- `dirty_worktree`: starting mismatch was recorded; only `.codex/config.toml` was dirty and
  remained untouched. Task evidence and ledger are the only recovery-lane repository edits.
- `stale_state`: prior containers/networks were removed before testing; every transcript binds
  the fresh invocation to full code SHA `0031b3d...` and the smoke/E2E artifacts were parsed.
- `hung_or_long_commands`: commands used repository wait limits and reached terminal exits;
  the service-check ran once to completion without restart.
- `flaky_tests`: the full Phase 3 and Phase 0 suites passed; the decoder test failed only under
  the isolated reverse mutation and passed immediately on committed code.
- `misleading_success_output`: PASS lines were corroborated by nonempty protected transcripts,
  parsed five-service smoke evidence, parsed E2E checks, and Docker project inventory.
- `repeated_interruptions`: the inherited worker interruption and two non-qualifying mutation
  probes were not claimed; corrected scenarios were rerun end-to-end and cleaned.
- `malformed_input`: not applicable to the delivered change because it adds no input parser;
  the preliminary non-UTF-8 token probe was explicitly excluded and replaced by valid UTF-8.
- `prompt_injection`: not applicable because no LLM or prompt path is involved.
- `cancel_resume`: not applicable because each gate is a bounded one-shot invocation with no
  resume protocol.

The code SHA is immutable and was the exact SHA executed for every claimed gate. The later
receipt/ledger commit changes evidence only; it does not rebind or falsely claim that its own
SHA was executed. The programming post-write audit measured the changed API module at 279
pure LOC and its test at 129; the skill checker therefore reports the API module as oversized.
Splitting that pre-existing multi-endpoint module is intentionally deferred because the owner
limited this recovery to the smallest directly necessary JSONB fix. The todo-18 plan checkbox
remains unchanged for independent review.
