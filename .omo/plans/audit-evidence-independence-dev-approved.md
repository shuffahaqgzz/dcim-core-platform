> DISPOSITION: RETIRED 2026-08-03 — see docs/governance/PLAN-DISPOSITIONS.md

# audit-evidence-independence-dev-approved - Work Plan

## TL;DR (For humans)
<!-- Fill this LAST, after the detailed plan below is written, so it summarizes the REAL plan. -->
<!-- Plain English for a non-engineer: NO file paths, NO todo numbers, NO wave/agent/tool names. -->

**What you'll get:** A clean pull-request candidate whose evidence is produced by fresh independent execution, not by editable claims. The prior failed audit remains preserved, while the corrected result is bound to one exact source revision and is ready for the owner's Development decision.

**Why this approach:** The approved plan itself becomes the authority outside the code being audited, and the branch is rebuilt safely on the current accepted base. This closes the circular “code verifies itself” problem and prevents stale evidence from surviving a changed revision.

**What it will NOT do:** It will not rewrite the old failure, touch the currently changing worktree, publish anything remotely, approve Development status, or make Staging/Production claims. It will not use live data or add a signing service or new dependency.

**Effort:** XL
**Risk:** High - The work rebuilds branch history, supervises a stateful Docker acceptance run, and replaces the audit trust model while preserving exact historical evidence.
**Decisions to sanity-check:** Rebuild on the exact current base in a new recoverable branch; require mutation-sensitive proof for every changed Python file; require Docker acceptance for local handoff; keep all remote actions and final approval owner-only.

Your next move: start work with the final plan SHA, or request a high-accuracy dual review first. Full execution detail follows below.

---

> TL;DR (machine): XL/high-risk sequential remediation that reconstructs the branch on pinned main, installs plan-anchored external scope/execution/coverage/F3 evidence, preserves historical failures, and ends at local owner handoff only.

## Scope
### Must have

- Treat this plan's owner-supplied raw SHA-256 as the only root of trust. The executor must receive the full 64-hex digest out-of-band in the `$omo:start-work` request; it must never derive the expected digest from the plan, tracked repository, manifest, or receipt being audited.
- Verify the plan bytes and every authority block before the first heredoc or product-tree mutation. The integrity gate must print exactly `heredoc_integrity=PASS`; any mismatch prints `NO-GO_PLAN_AUTHORITY` and stops.
- Use `backup/phase2-before-pr-prep-20260727` only as the pinned source of original HEAD `995383355f32ac7b70573c5ca756786e1836a954`. Never mutate or continue the existing product worktree or its branch.
- Create a new branch `fix/phase2-audit-evidence-independence` and worktree `/home/infra/dcim-core-platform-worktrees/phase2-audit-evidence-independence-20260727` from exact base `e20c8e3569cb171a23fb1e4a9c417074dfb0ae8a`; fail if either target already exists.
- Reconstruct the accepted feature in eleven single-parent commits: one reconciled prerequisite security commit followed by the ten Phase-2 Todo commits. Preserve the original branch and map every original commit to `UPSTREAM_EQUIVALENT`, one reconciled commit, or one rewritten Todo commit.
- Preserve current-main Phase-1 closure semantics. At the prerequisite checkpoint, `README.md`, `docs/phase1/DEVELOPMENT-HANDOVER.md`, `docs/phase1/ISSUE-9-ACCEPTANCE-MATRIX.md`, and `docs/phase1/ISSUE-9-CLOSURE-PACKAGE.md` equal the exact base bytes. Port only the four later security-remediation differences listed in Authority Block A. Later Phase-2 README additions may be replayed, but must not reintroduce stale counts or final-head claims.
- Keep separate, non-interchangeable scope inventories: the original 16-patch sequence; the 77-pair/58-path/34-Python Phase-2 range; the 65-path/35-Python candidate tree delta; the eight-file prerequisite disposition; the expected 62-path/35-Python pre-remediation reconstruction; and the exact remediation allowlist.
- Derive final scope from raw two-tree and diff-tree Git facts. Check paths, statuses, modes, object types, symlinks, renames/copies, parent topology, tracked diff, staged/unstaged state, and untracked state. Branch-local tables and verifiers are evidence inputs, never authority.
- Replace self-attested F2/F3 outcomes with fresh execution owned by the trusted launcher. Callers may not supply commands, exit codes, markers, verdicts, receipt IDs, F3 invocation IDs, nonces, or qualifying receipts.
- Keep receipts external and non-authoritative. Every qualifying local aggregate, Docker/F3 qualification, review join, and final handoff verdict reruns the plan-owned external oracle against the pinned commit/tree/parents and rereads the branch ref before and after the run.
- Execute verified oracle/executor bytes from the same verified descriptor under a scrubbed environment and pinned interpreter/toolchain identity. Exclude subject-tree `PYTHONPATH`, startup hooks, original-worktree access, and mutable imports.
- Provide strict closed-schema JSON receipts with duplicate-key rejection, canonical encoding, launcher-generated nonces and unique IDs, exact requirement mapping, atomic exclusive publication, process-outcome union, timeout/signal/descendant handling, output byte counts/digests, and explicit `NO-GO_*` disposition.
- Prove causal coverage for every Python path changed by the final PR, including new verifier and test files. The external algorithm must execute a real exact unittest, trace a non-module changed callable, observe the required failure/return/filesystem/subprocess/database effect, apply a deterministic non-no-op structural mutation, prove the mutated node executes, and require the intended mapped assertion to fail.
- Rerun the full synthetic Docker acceptance. Capture a direct nonzero PostgreSQL snapshot and runtime identities before cleanup, then complete selected-run cleanup, service stop, one-off cleanup, and fixed-volume verification. Emit the sole qualifying F3 receipt only after every cleanup check succeeds while binding the earlier snapshot.
- Preserve every legacy PASS, FAIL, and NO-GO artifact byte-for-byte in an external append-only epoch. Classify old F2/F3/completion/terminal records as historical or `legacy_self_attestation`; later success references, never replaces, prior failure.
- End with five independent exact-head lanes and a separate terminal join. The only successful local gate word is `LOCAL_PASS`; the only final local outcome is `READY_FOR_OWNER_HANDOFF`.
- Always include `remote_ci=NOT_RUN_OWNER_ONLY`, `github_mutation=NOT_PERFORMED`, and `dev_approved=false` in the local terminal result.

### Must NOT have (guardrails, anti-slop, scope boundaries)

- No product edit, Git operation, or heredoc before `heredoc_integrity=PASS`.
- No mutation of `/home/infra/dcim-core-platform-worktrees/phase2-first-vertical-slice-20260724`, its branch, or its current rebase/reconciled state.
- No floating `main`, merge commit, force-push, destructive reset, in-place rebase, rename/copy, unexpected conflict resolution, extra commit, or unapproved path/mode/type.
- No caller-authored PASS, cached/replayed receipt as authorization, marker-only success, prose-only review, tracked exact-head PASS record, or branch-substituted oracle/executor.
- No symbol/import/grep-only coverage, no-op mutation, surviving or unexecuted mutant, skipped/expected-failure/zero/multiple-test target, or original-worktree import leakage.
- No F3 qualification from a pre-cleanup cache alone or from post-cleanup zero state alone.
- No Docker-degraded readiness. Docker/Compose absence is `NO-GO_DOCKER_REQUIRED_FOR_HANDOFF`.
- No new package, signing service, key infrastructure, network service, repository-ruleset change, or unrelated refactor.
- No deletion, rewrite, omission, or favorable reclassification of historical FAIL/NO-GO evidence.
- No GitHub push, PR/issue mutation, remote-check claim, condition/open-decision change, ADR disposition, issue closure, merge/tag, or `DEV-APPROVED` claim.
- No Staging, Production, connected-source, HA, SLA, write/control, or Production-readiness claim.
- No live credentials, endpoints, identifiers, payloads, logs, dumps, screenshots, topology, host identifiers, raw Docker inspection, absolute runtime-root value in evidence, or non-synthetic data.

## Verification strategy
> Zero human intervention - all verification is agent-executed.

- Test decision: strict TDD with Python 3.12 standard-library `unittest`. Each behavior-changing Todo starts with its named RED test or an existing characterization test, records the observed result, makes the smallest change, and reruns the same selector GREEN before broader gates.
- Trusted launcher boundary: the start-work executor is the external launcher. It receives the plan SHA from the user, opens the plan once, hashes those raw bytes, extracts the delimited Authority/Oracle blocks from that same buffer, validates their full hashes, places executable bytes in anonymous or exclusive descriptors, and invokes those exact descriptors via `pass_fds` with `PYTHONPATH`, `PYTHONSTARTUP`, `PYTHONHOME`, user-site, locale overrides, and subject-tree startup hooks removed.
- Plan-FD and oracle-FD TOCTOU tests must replace the pathname after open and prove the opened verified bytes execute while substituted bytes do not.
- Interpreter/toolchain assumptions: Linux with `/proc/self/fd`, Python 3.12, Git, GNU Make, Docker Engine, and Docker Compose v2. Pin observed versions in external evidence. Absence or drift outside the plan's compatible major/minor contract is `NO-GO_TOOLCHAIN_IDENTITY`.
- All shell commands are prefixed with `rtk`. Direct `subprocess.run([...], shell=False)` argv inside Python does not include `rtk`.
- Owner-decided runtime root remains the protected path fixed in the original owner-approved plan at `.omo/plans/phase1-or-phase2-implementation-continuation.md:61-65`. It may be used by the process but must never be copied into evidence or tracked files.
- Pre-flight Docker gate: `rtk docker info --format 'server={{.ServerVersion}}'` and `rtk docker compose version` must both exit `0`; otherwise stop with `NO-GO_DOCKER_REQUIRED_FOR_HANDOFF`.
- Present fixed-volume state must be exactly the three named `dcim-build-*` volumes from the original plan. Runtime binding is verified by protected secrets plus Kafka cluster identity comparison against fixed volumes; absence of a `DCIM_RUNTIME_ROOT` line in legacy `runtime.env` is not a failure.
- Evidence root: outside `ulw-loop`, `.omo/evidence/audit-evidence-independence-dev-approved/`; inside `ulw-loop`, the current attempt directory returned by `omo ulw-loop status --json`. T1 creates one external epoch directory and every later task writes only beneath it.
- Each invocation binds `base_sha`, `subject_commit_sha`, `subject_tree_sha`, ordered parent SHAs, plan SHA, authority-block hashes, oracle/executor hashes, requirement ID, launcher nonce, receipt ID, start/end UTC, monotonic duration, exit/signal/timeout/spawn outcome, stdout/stderr byte counts and SHA-256, and the observed branch ref before/after.
- Receipts are non-authoritative caches. The launcher reruns the external oracle for `LOCAL_GATE_AGGREGATE`, `F3_QUALIFICATION`, `REVIEW_JOIN`, and `FINAL_HANDOFF`.
- A dirty-state change, ref movement, subject-object mismatch, receipt replay, duplicate ID/nonce, duplicate JSON key, unknown field, wrong requirement mapping, or stale artifact invalidates the entire current-and-downstream evidence epoch.
- Any source/test/doc/manifest change after Todo 9 creates a new exact-head epoch and reruns Todos 9-12 plus F1-F6.
- Required non-Docker gates:
  - `rtk python3 -m unittest tests.test_phase2_evidence_receipts -q`
  - `rtk python3 -m unittest tests.test_contracts tests.test_validate_synthetic_fixtures -q`
  - `rtk python3 -m unittest tests.test_phase2_fixtures tests.test_phase2_contracts tests.test_synthetic_connectors tests.test_phase2_vertical_slice tests.test_phase2_docs -q`
  - `rtk python3 -m unittest tests.test_foundation_acceptance tests.test_foundation_smoke tests.test_foundation_policy tests.test_foundation_evidence_summary tests.test_foundation_images tests.test_foundation_lifecycle tests.test_foundation_supply_chain -q`
  - `rtk make validate-json`
  - `rtk make validate-fixtures`
  - `rtk make phase2-check`
  - `rtk make phase0-check`
  - `rtk python3 scripts/check_public_repo_safety.py`
  - `rtk python3 scripts/check_markdown_links.py`
- Required Docker/milestone gates:
  - `rtk make preflight`
  - `rtk python3 scripts/phase2_final_acceptance.py --requirement F3_QUALIFICATION --as-of-utc 2026-01-02T03:04:05Z --run-id phase2-audit-remediation`
  - External direct-DB/runtime oracle rerun after the product command and after cleanup.
- Evidence: `<attemptDir>/task-<N>-audit-evidence-independence-dev-approved.{json,md}`. Only allowlisted public-safe summaries, hashes, synthetic test identities, counts, durations, and dispositions may be written.

## Execution strategy
### Parallel execution waves
> Implementation is intentionally sequential because each task changes the subject or its trust graph. Only F1-F5 fan out after the exact head is frozen; F6 joins them.

- Wave 1, authority and reconstruction: Todos 1-4 in order.
- Wave 2, test-first audit hardening: Todos 5-8 in order. Todo 6 and Todo 7 are logically separable but remain sequential to avoid a shared exact-head/evidence race.
- Wave 3, exact-head qualification: Todos 9-12 in order.
- Final verification: F1-F5 launch independently against the same exact commit/tree/plan SHA; F6 runs only after all five terminate.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | none | 2-12, F1-F6 | none |
| 2 | 1 | 3-12, F1-F6 | none |
| 3 | 2 | 4-12, F1-F6 | none |
| 4 | 3 | 5-12, F1-F6 | none |
| 5 | 4 | 6-12, F1-F6 | none |
| 6 | 5 | 7-12, F1-F6 | none |
| 7 | 6 | 8-12, F1-F6 | none |
| 8 | 7 | 9-12, F1-F6 | none |
| 9 | 8 | 10-12, F1-F6 | none |
| 10 | 9 | 11-12, F1-F6 | none |
| 11 | 10 | 12, F1-F6 | none |
| 12 | 11 | F1-F6 | none |
| F1-F5 | 12 | F6 | F1-F5 only |
| F6 | F1-F5 | owner handoff | none |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [ ] 1. Verify the plan trust root, immutable inventories, toolchain, runtime pre-flight, and legacy evidence
  What to do:
  - Receive the full expected SHA-256 from the `$omo:start-work` request. Open this plan once, hash the raw bytes, extract the exact delimited blocks in Appendices A-E from that buffer, verify their block hashes, and execute the Oracle Contract from the same verified descriptor under the scrubbed environment.
  - Before any heredoc, worktree creation, or product edit, print `heredoc_integrity=PASS`. Any mismatch prints `NO-GO_PLAN_AUTHORITY` and exits nonzero.
  - Verify `origin/main=e20c8e3569cb171a23fb1e4a9c417074dfb0ae8a`, `backup/phase2-before-pr-prep-20260727=995383355f32ac7b70573c5ca756786e1836a954`, original merge base `3a92960314df11d68152dc59244d31b93eaa9a57`, original start `2db4022b756d6d98934234daabce3a28bb8443dc`, and original/completed plan reconstruction `a5b4527d…`/`fabc78ee…`.
  - Capture the current existing product-worktree status read-only, then mark that worktree and branch forbidden for all later writes.
  - Create the external attempt directory descriptor-safely. Snapshot every legacy file named in Appendix D from the original evidence directory, verify its pinned SHA-256 before and after copying, and generate an append-only inventory. Do not follow symlinks or copy raw runtime material.
  - Run the Docker/Compose capability gate, fixed-volume count/state check, and protected-runtime binding check from Verification strategy. Record only public-safe state. Docker absence or partial volumes is a NO-GO.
  - Pin observed Linux, Python, Git, Make, Docker, and Compose identities.
  Must NOT do:
  - Do not derive the expected plan SHA from the plan, accept truncated hashes, materialize before verification, trust pathnames after open, import subject-tree code, or expose the runtime-root value.
  - Do not mutate any Git ref/worktree or continue an existing rebase.
  Parallelization: Wave 1 | Blocked by: none | Blocks: 2-12, F1-F6
  References:
  - `.omo/drafts/audit-evidence-independence-dev-approved.md` — owner-approved topology and adversarial corrections.
  - `.omo/plans/phase1-or-phase2-implementation-continuation.md:59-115` — owner runtime-root/pre-flight decision and local/Docker gate catalog.
  - `scripts/phase2_scope_safety.py:20-117` — branch-authored table that is evidence only.
  - `.omo/evidence/phase1-or-phase2-implementation-continuation/implementation-start.json` — original start/plan bindings.
  - `AGENTS.md:12-42` and `docs/baseline/DEVELOPMENT-BASELINE.md:13-16,120-138` — safety and Development authority.
  Acceptance criteria:
  - The launcher-observed plan digest equals the full user-supplied value; all Appendix block hashes validate; `heredoc_integrity=PASS` appears exactly once before any later action.
  - `rtk git rev-parse` resolves every pinned object exactly, backup ref is immutable for this attempt, and no operation writes the existing product worktree.
  - Legacy inventory count/path/hash equality matches Appendix D; symlink/FIFO/device/path-swap inputs are rejected.
  - `rtk docker info` and `rtk docker compose version` exit `0`; exactly three fixed volumes exist and the guard proves secrets plus Kafka cluster identity match the bound runtime material without requiring a `runtime.env` root line.
  QA scenarios:
  - happy: run the plan-owned bootstrap with the correct out-of-band SHA; assert exact markers `heredoc_integrity=PASS`, `authority_blocks=PASS`, `legacy_inventory=PASS`, and `runtime_preflight=PASS`.
  - failure: pathname-replace the plan after open, alter one extracted byte, pass a truncated/wrong SHA, substitute `PYTHONPATH`, duplicate a legacy file, replace a legacy file with a symlink, report partial volumes, and omit Docker; each must exit nonzero with the matching `NO-GO_*`.
  - Evidence: `<attemptDir>/task-1-audit-evidence-independence-dev-approved.json`
  Commit: N | external authority/evidence only

- [ ] 2. Create the recoverable clean remediation branch and worktree
  What to do:
  - Assert the target branch `fix/phase2-audit-evidence-independence` and target worktree path `/home/infra/dcim-core-platform-worktrees/phase2-audit-evidence-independence-20260727` do not exist.
  - Create a recovery annotation in the external evidence epoch that binds the existing branch name, its observed current head, and backup ref `9953833…`; do not move either ref.
  - Create the new branch/worktree from exact base `e20c8e3…`. Immediately verify clean tracked state, zero untracked files, single-parent base topology, and base tree identity.
  - Configure no new remote and perform no network operation.
  Must NOT do:
  - Do not use the existing product worktree, `git rebase --continue`, `git reset`, `git checkout --`, `git branch -f`, or force-push.
  - Do not reuse an existing target path/ref or silently choose a different name.
  Parallelization: Wave 1 | Blocked by: 1 | Blocks: 3-12, F1-F6
  References:
  - Appendix A — pinned base/source/recovery refs and reconstruction policy.
  - `docs/runbooks/GITHUB-REPOSITORY-SETUP.md:21-71` — branch/PR conventions.
  Acceptance criteria:
  - `rtk git -C <new-worktree> rev-parse HEAD` equals `e20c8e3569cb171a23fb1e4a9c417074dfb0ae8a`.
  - `rtk git -C <new-worktree> status --porcelain=v1 --untracked-files=all` is empty.
  - The backup ref and existing product branch resolve to their pre-task values; the existing product worktree status bytes are unchanged from Todo 1.
  QA scenarios:
  - happy: create the exact target and verify base/head/tree/clean state through the external scope oracle.
  - failure: precreate a target branch or directory in a disposable fixture, move the backup ref, dirty the target, or point base at any other object; require `NO-GO_RECONCILIATION_TARGET_EXISTS`, `NO-GO_BACKUP_REF_DRIFT`, `NO-GO_DIRTY_TARGET`, or `NO-GO_BASE_DRIFT`.
  - Evidence: `<attemptDir>/task-2-audit-evidence-independence-dev-approved.json`
  Commit: N | branch/worktree setup only

- [ ] 3. Reconcile the six prerequisite patches into one exact security-remediation commit
  What to do:
  - Evaluate original commits `cefcfdf4…`, `3b086ac7…`, `dd3b1957…`, `5dbf4715…`, and `872df38a…` against base `e20c8e3…`. Record `UPSTREAM_EQUIVALENT` only when the plan-owned oracle proves their required Phase-1 behavior and files are already present or superseded on the base.
  - Replay original `2db4022b…` as one new single-parent commit, but accept only the four exact prerequisite deltas:
    `deploy/compose/derived-images/grafana/Dockerfile`,
    `deploy/compose/derived-images/license-dispositions.json`,
    `deploy/compose/derived-images/recipes.json`,
    `tests/test_foundation_images.py`.
  - Require those four resulting blobs to equal the corresponding original `2db4022…` blobs. Require `README.md` and the three Phase-1 closure documents to remain exact `e20c8e3…` blobs at this checkpoint.
  - Verify the `kin-openapi` recipe/input/digest/license/test remediation, then commit with `fix(phase1): preserve image remediation on current main`.
  Must NOT do:
  - Do not blindly cherry-pick the six commits, revive stale Phase-1 documentation, port Kafka paths already present on the base, accept an empty/unmapped commit, or resolve an unexpected conflict.
  Parallelization: Wave 1 | Blocked by: 2 | Blocks: 4-12, F1-F6
  References:
  - Appendix B — original six commits and exact per-commit path inventory.
  - `deploy/compose/derived-images/grafana/Dockerfile` at `2db4022…` — `kin-openapi` remediation.
  - `deploy/compose/derived-images/recipes.json` and `license-dispositions.json` at `2db4022…`.
  - `tests/test_foundation_images.py` at `2db4022…`.
  - `docs/phase1/DEVELOPMENT-HANDOVER.md`, `ISSUE-9-ACCEPTANCE-MATRIX.md`, and `ISSUE-9-CLOSURE-PACKAGE.md` at `e20c8e3…`.
  Acceptance criteria:
  - New branch is exactly one commit ahead of `e20c8e3…`; that commit has one parent and exactly four `M` paths with mode `100644`.
  - Four ported blob IDs equal `2db4022…`; four retained-base blobs equal `e20c8e3…`.
  - `rtk python3 -m unittest tests.test_foundation_images -q` and the full Phase-1 non-regression suite exit `0`.
  - External mapping records five `UPSTREAM_EQUIVALENT` originals and `2db4022… -> <new-sha>`.
  QA scenarios:
  - RED/characterization: run the `kin-openapi` test against an isolated `e20c8e3…` archive and observe failure/absence, then run against the reconciled commit and observe success.
  - failure: alter a retained doc, omit the Grafana fix, include either Kafka path, add a fifth path, change a mode, or create a merge/empty commit; external oracle rejects with `NO-GO_PREREQUISITE_DISPOSITION`.
  - Evidence: `<attemptDir>/task-3-audit-evidence-independence-dev-approved.json`
  Commit: Y | `fix(phase1): preserve image remediation on current main`

- [ ] 4. Replay the ten Phase-2 Todo commits with exact ordinal/path authority
  What to do:
  - Replay original commits `7efd2bc8…` through `99538335…` sequentially as ten single-parent commits on the Todo 3 commit.
  - For ordinal Todo 1-10, require exact equality to the 77 `(Todo,path)` pairs in Appendix C; no path may move between Todos even when the final union is unchanged.
  - Preserve original commit subjects. Record original-to-new SHA mapping, parent mapping, tree IDs, statuses, modes, and blob IDs.
  - After replay, require eleven commits ahead of base, an expected 62-path/35-Python two-tree delta before remediation, and the three Phase-1 closure documents byte-identical to `e20c8e3…`.
  - Verify `README.md` retains current-main Phase-1 caveats/count semantics while including only authorized Phase-2 additions from original Todos 5, 6, and 9.
  Must NOT do:
  - Do not replay against floating refs, squash/reorder commits, accept conflicts/renames/copies/mode changes, add a commit, or reuse current rebased branch commits as authority.
  Parallelization: Wave 1 | Blocked by: 3 | Blocks: 5-12, F1-F6
  References:
  - Appendix B — exact original commit sequence and per-commit paths.
  - Appendix C — authoritative Todo 1-10 path sets and digest `67cb81e1…`.
  - `.omo/plans/phase1-or-phase2-implementation-continuation.md:478-520` — original broad scope intent; Appendix C supersedes it for exact mapping.
  Acceptance criteria:
  - The external scope oracle prints `original_phase2_authority=PASS`, `reconciled_history=PASS`, and `reconciled_tree_delta=PASS`.
  - Exactly ten new Todo commits follow the one prerequisite commit; every commit has one parent and its exact authorized path set.
  - No rename/copy/symlink/mode drift; worktree and index are clean; expected pre-remediation delta is exactly 62 paths/35 Python.
  - `rtk make phase2-check`, `rtk make phase0-check`, the Phase-1 non-regression suite, public-safety, and markdown-links all exit `0`.
  QA scenarios:
  - happy: compare every original/reconciled ordinal using plan-owned raw Git inspection and record the mapping.
  - failure: move one path between Todos, add an allowed-union path to the wrong commit, amend parent topology, change a retained Phase-1 doc, introduce a symlink/mode change, or use a stale mapping; each fails with `NO-GO_SCOPE_AUTHORITY`.
  - Evidence: `<attemptDir>/task-4-audit-evidence-independence-dev-approved.json`
  Commit: Y | ten replayed commits with their original Conventional Commit subjects

- [ ] 5. Add the strict receipt contract and fixed trusted-execution integration test-first
  What to do:
  - Add `schemas/phase2-evidence-receipt.schema.json` as a closed, versioned schema and validate it through the existing contract gate.
  - Add `scripts/phase2_evidence_receipt.py` for descriptor-safe strict parsing, duplicate-key rejection, canonical encoding, process-outcome union, unique requirement/nonce/receipt constraints, atomic `O_EXCL` publication, and public-safe output digests/counts.
  - Add `scripts/phase2_final_acceptance.py` as the single product-side integration entry point. It may mirror the plan contract and expose structured observations, but it is never the qualifying external root of trust.
  - Add `tests/test_phase2_evidence_receipts.py` and update `tests/test_contracts.py`.
  - Start RED with caller-authored PASS plus nonzero subprocess exit; then implement the minimum contract until RED becomes GREEN.
  Must NOT do:
  - Do not accept caller commands/verdicts/outcomes/IDs, arbitrary shell strings, unknown fields, duplicate keys/IDs, existing receipt input as authorization, marker-only PASS, or Markdown `COMMAND_RECORD` as execution proof.
  - Do not add dependencies, signing, network, or backward-compatible acceptance of legacy self-attestation.
  Parallelization: Wave 2 | Blocked by: 4 | Blocks: 6-12, F1-F6
  References:
  - `scripts/phase2_verify_completion_manifest.py:297-340` — current declared-outcome trust gap.
  - `scripts/phase2_verify_terminal_manifest.py:311-389,634-682` — current F2/F3 record validation and limited recomputation.
  - `tests/test_phase2_vertical_slice.py:6433-7323` — current manifest/terminal tamper tests.
  - Appendix E — receipt schema/requirement/oracle contract.
  Acceptance criteria:
  - Schema rejects additional properties, duplicate JSON keys, invalid outcome unions, reused nonces/receipt IDs, wrong requirement IDs, wrong base/head/tree/parents/plan/oracle hashes, noncanonical encoding, missing timeout/signal data, and output bodies instead of digests/counts.
  - Product integration owns immutable argv catalogs for its supported requirements and uses `subprocess` argv with `shell=False`, bounded timeouts, new process groups, descendant termination, and launcher-generated IDs.
  - A PASS marker with exit `2`/`97`, signal, timeout, spawn error, or surviving descendant produces non-PASS and explicit `NO-GO_RECEIPT_*`.
  - `rtk python3 -m unittest tests.test_phase2_evidence_receipts tests.test_contracts -q` exits `0`.
  QA scenarios:
  - RED: `rtk python3 -m unittest tests.test_phase2_evidence_receipts.Phase2EvidenceReceiptTests.test_declared_pass_cannot_override_nonzero_process -q` fails before implementation and passes after.
  - failure: fabricate/copy/replay a receipt; duplicate a key/ID; alter a canonical byte; emit marker with nonzero exit; signal/timeout/spawn-error a child; leave a descendant; substitute wrong plan/head/tree/parent; each exact test exits `0` only by observing rejection.
  - external check: trusted launcher runs a known exit-0 and exit-97 fixture itself and compares the product observation to its independent process observation.
  - Evidence: `<attemptDir>/task-5-audit-evidence-independence-dev-approved.json`
  Commit: Y | `feat(evidence): add strict phase2 execution receipts`

- [ ] 6. Replace symbol-only mapping with causal trace, probe, and mutation verification
  What to do:
  - Add `scripts/phase2_verify_python_coverage.py` as a subject-side mirror of the plan-owned external coverage algorithm; the external algorithm remains authoritative.
  - Define changed executable lines from the exact base/head two-tree diff plus Python AST: exclude blank/comment/type-only/import-only/module-docstring lines; attribute executable lines to the smallest enclosing callable; explicitly classify deleted and module-only files.
  - In isolated `git archive` extractions, enumerate exact unittest selectors deterministically. For every final changed Python path, select and run exactly one non-skipped test that reaches a changed non-module callable, records one observable probe class, and kills at least one deterministic structural mutant.
  - Mutation priority is plan-owned and deterministic: fail-closed comparison/boolean guard, return constant, raised disposition, branch predicate, then side-effect call boundary. Validate a unique AST locator/source-span digest; reject syntax/import-breaking or no-op mutations before credit.
  - For changed test modules, require trace of the exact test method plus a killed implementation/input mutant outside that test file. For subprocess entrypoints, collect child trace through a structured child receipt rather than treating missing parent trace as success.
  - Cover all Python paths in the final PR delta, not only the original 34/35.
  Must NOT do:
  - Do not accept an unrelated no-op test, test-file self-mutation, import-time hit, percentage-only trace, grep/symbol existence, a skipped/expected-failure target, zero/multiple selected tests, surviving/unexecuted/ambiguous mutant, or original-worktree import.
  Parallelization: Wave 2 | Blocked by: 5 | Blocks: 7-12, F1-F6
  References:
  - `scripts/phase2_verify_terminal_manifest.py:470-631` — current symbol/import-only mapping.
  - `tests/test_phase2_vertical_slice.py` — current Phase-2 behaviors and subprocess tests.
  - `scripts/phase2_postgres_adversarial_sql_smoke.py`, `phase2_postgres_idempotency_smoke.py`, and `phase2_postgres_rollback_smoke.py` — previously unmapped direct entrypoints.
  - `tests/test_contracts.py` — previously not executed by the 24 mapped selectors.
  - Appendix E — exact classifier, isolation, selector, probe, mutation, and timeout contract.
  Acceptance criteria:
  - Baseline runner reports `testsRun == 1`, success, and zero failures/errors/skips/expected failures/unexpected successes for each selected claim.
  - Trace proves at least one authorized changed executable line in a non-module callable; child subprocess claims include a matching child receipt.
  - Each mutation changes the source digest, resolves exactly one AST node, executes in the mutated run, keeps the test importable/runnable exactly once, and causes the intended selected test assertion to fail.
  - Every final changed Python path has exactly one qualifying claim; no extra/missing/duplicate path exists.
  - `rtk python3 -m unittest tests.test_phase2_evidence_receipts tests.test_phase2_vertical_slice -q` exits `0`.
  QA scenarios:
  - RED: add `test_placeholder: return None` as a disposable fixture mapping and prove `NO-GO_TEST_NO_CAUSAL_PROBE`; then implement causal verification until the real positive fixture passes.
  - failure: import-only hit, skipped/expected-failure/zero/multiple selection, original-worktree access, no-op/surviving/unexecuted mutant, ambiguous locator, syntax/import-breaking mutant, child receipt omission, and changed test mapped only to another test file each produce the specified `NO-GO_*`.
  - happy: independently execute/trace/mutate each original changed Python path plus all new remediation Python paths in isolated pinned-tree extractions.
  - Evidence: `<attemptDir>/task-6-audit-evidence-independence-dev-approved.json`
  Commit: Y | `test(phase2): require causal changed-python coverage`

- [ ] 7. Implement the supervised F3 pre-cleanup binding and post-cleanup qualification
  What to do:
  - Extend `scripts/phase2_final_acceptance.py` with fixed requirement `F3_QUALIFICATION` and extend `scripts/phase2_verify_postgres_recovery.py` only where needed to expose structured direct-DB snapshots and cleanup observations.
  - Generate the F3 invocation ID inside the trusted supervisor. Bind fixed `as_of_utc`, run ID, input-manifest SHA, database-snapshot SHA, capacity/NOC digests, runtime guard identity, Compose project, image/config digests, Phase-1 sentinel/relation fingerprints, and fixed-volume identities.
  - After the production Phase-2 run, retained recovery, idempotency, adversarial SQL, incompatible-schema, fresh-shell replay, capacity capture, and NOC verification succeed, query the five allowlisted Phase-2 tables directly before cleanup. Require nonzero per-table count/checksum tuples and hash the canonical snapshot in supervisor memory.
  - Wait for the exact Docker process and all children. Then clean only selected-run rows, verify five-table selected-run zero state, stop services, remove one-offs/temp artifacts, and verify exactly three fixed volumes remain.
  - Emit the only qualifying F3 receipt after cleanup/stop/volume checks succeed, binding the earlier nonzero snapshot plus every child outcome.
  Must NOT do:
  - Do not accept caller F3 IDs, product `status`, stdout markers, summary-derived DB identity, zero pre-clean state, pre-clean receipt alone, post-clean zero state alone, cleanup masked with `|| true`, broad table cleanup, volume deletion, or an absent Docker degraded result.
  Parallelization: Wave 2 | Blocked by: 6 | Blocks: 8-12, F1-F6
  References:
  - `.omo/plans/phase1-or-phase2-implementation-continuation.md:792-798` — original exact retained-runtime F3 contract.
  - `scripts/phase2_capture_capacity_posture.py:119-215` — direct capacity capture.
  - `scripts/phase2_verify_noc_artifact.py:298-366` — fresh DB/NOC comparison.
  - `scripts/phase2_verify_postgres_recovery.py` — retained recovery/cleanup.
  - `scripts/phase2_foundation_runtime_guard.py` — secrets plus Kafka-cluster fixed-volume binding.
  - Appendix E — F3 table allowlist, ordered step IDs, timeouts, pre/post state, and receipt fields.
  Acceptance criteria:
  - The table allowlist is exactly `foundation.phase2_runs`, `foundation.phase2_accepted_events`, `foundation.phase2_quarantined_events`, `foundation.phase2_duplicate_events`, and `foundation.phase2_noc_snapshots`.
  - Pre-cleanup receipt material contains nonzero count/checksum tuples for all five tables, canonical aggregate DB digest, run/manifest/as-of/F3 IDs, capacity/NOC digests, and preserved Phase-1 fingerprints.
  - Final qualifying receipt exists only after all child exits are `0`, cleanup succeeds, selected-run counts are zero, services are `0`, one-offs are `0`, temp artifacts are `0`, and fixed volumes are exactly `3`.
  - Failure/timeout/signal/cleanup error preserves fixed volumes, emits a non-PASS attempt record, and never emits a qualifying receipt.
  - Focused F3 unit tests and `rtk python3 -m unittest tests.test_phase2_vertical_slice -q` exit `0`.
  QA scenarios:
  - RED: `rtk python3 -m unittest tests.test_phase2_vertical_slice.Phase2FinalAcceptanceTests.test_precleanup_snapshot_cannot_qualify_before_cleanup -q` fails before implementation and passes after.
  - failure: zero pre-clean table, mismatched manifest/DB/capacity/NOC/F3 IDs, cleanup-before-capture, child exit/signal/timeout, cleanup failure, lingering service/one-off/temp artifact, lost/extra volume, or `runtime.env`-only binding each produces a distinct `NO-GO_F3_*`.
  - happy unit: mock Docker/psql boundaries and prove exact ordering and atomic final publication.
  - Evidence: `<attemptDir>/task-7-audit-evidence-independence-dev-approved.json`
  Commit: Y | `feat(phase2): supervise independent final acceptance`

- [ ] 8. Integrate fail-closed completion/scope/terminal behavior, Make targets, docs, and local-only vocabulary
  What to do:
  - Update `scripts/phase2_verify_completion_manifest.py`, `scripts/phase2_verify_scope_diff.py`, and `scripts/phase2_verify_terminal_manifest.py` so legacy `COMMAND_RECORD`/Markdown records cannot satisfy F2/F3 or causal coverage, coordinated local table/verifier edits cannot elevate scope, and external evidence is clearly an input/cache rather than root authority.
  - Keep branch-side verifiers useful as defense in depth, but require fresh external-oracle invocation for any qualifying aggregate.
  - Add Make entry points for focused receipt tests and local candidate verification without naming a CI job `preflight` as full `make preflight`.
  - Update `docs/phase2/FIRST-VERTICAL-SLICE.md`, `RUNBOOK.md`, and `DEVELOPMENT-HANDOVER.md` to document one acceptance entry point, append-only legacy classification, exact local/remote boundary, and nonclaims.
  - Tracked docs may state procedures and `LOCAL_READY_FOR_OWNER_REVIEW` only as descriptive vocabulary if needed, but the machine result vocabulary remains gate `LOCAL_PASS` and final `READY_FOR_OWNER_HANDOFF`. They must not embed an exact-head PASS, review verdict, remote result, or DEV approval.
  - Add/update doc and manifest tests before the production/doc change.
  Must NOT do:
  - Do not trust branch-local authority, weaken existing descriptor/no-follow checks, grandfather old F2/F3, rewrite historical evidence, claim remote/full preflight, alter Phase-1 closure documents, or change C/OD/ADR status.
  Parallelization: Wave 2 | Blocked by: 7 | Blocks: 9-12, F1-F6
  References:
  - `scripts/phase2_verify_completion_manifest.py:191-420`.
  - `scripts/phase2_verify_scope_diff.py:117-232`.
  - `scripts/phase2_verify_terminal_manifest.py:278-683`.
  - `Makefile:88-107` and `.github/workflows/ci.yml:17-36`.
  - `docs/phase2/DEVELOPMENT-HANDOVER.md`, `FIRST-VERTICAL-SLICE.md`, `RUNBOOK.md`.
  - `docs/evidence/README.md:5` and `docs/baseline/DEVELOPMENT-BASELINE.md:13-16`.
  Acceptance criteria:
  - A disposable fixture with real F2 exit `2`, declared F3 exit `97`, and internally consistent/rehashed Markdown/JSON fails every branch-side and external aggregate.
  - Coordinated edits to branch table + verifier + manifest + tests cannot change the plan-owned result.
  - Terminal output can emit internal diagnostic PASS markers only with explicit non-authoritative labeling; the external join emits only `LOCAL_PASS`/`READY_FOR_OWNER_HANDOFF` and mandatory owner-only fields.
  - `rtk make phase2-check`, `rtk make phase0-check`, focused receipt/manifest/doc tests, public-safety, and markdown-links exit `0`.
  QA scenarios:
  - RED: existing synthetic terminal fixture that manufactures PASS without executing F2/F3 must fail under the new contract; then update the minimal implementation/tests until only externally executed fixtures pass.
  - failure: legacy record, fabricated receipt, coordinated table/verifier edit, tracked final-head PASS, remote-CI claim, `DEV-APPROVED` text, status drift, or missing mandatory owner-only field is rejected with explicit `NO-GO_*`.
  - happy: run all branch-side verifiers as defense-in-depth, then run the external oracle and compare the non-authoritative diagnostics.
  - Evidence: `<attemptDir>/task-8-audit-evidence-independence-dev-approved.json`
  Commit: Y | `fix(phase2): bind audit-ready local handoff`

- [ ] 9. Freeze the exact remediation head and prove whole-PR scope externally
  What to do:
  - Require all tracked implementation/doc changes committed and the target worktree/index/untracked set empty.
  - Capture one exact-head epoch: base SHA, subject commit SHA, tree SHA, ordered parents, plan SHA, authority hashes, interpreter/toolchain identity, and branch ref.
  - Run the plan-owned scope oracle directly from its verified descriptor. It must independently derive the final two-tree delta from `e20c8e3…` to the frozen subject, the eleven reconstructed commits, all remediation commits, statuses, modes, types, symlinks, renames/copies, and dirty state.
  - Require original replayed paths to conform to Appendices B-C and every remediation edit to be inside Appendix F's exact path/mode allowlist.
  - Reverify the legacy evidence inventory and confirm no tracked evidence attempts to bind its own final HEAD.
  - Reread the branch ref and dirty state after the oracle. Any drift invalidates this epoch.
  Must NOT do:
  - Do not write tracked files, amend/rebase, create evidence in the subject extraction, accept `83` as a PR count, or trust branch-side scope output as authority.
  Parallelization: Wave 3 | Blocked by: 8 | Blocks: 10-12, F1-F6
  References:
  - Appendices A-C — original/reconciliation authority.
  - Appendix D — legacy evidence inventory.
  - Appendix F — exact remediation path/mode allowlist.
  - `scripts/phase2_scope_safety.py` and branch verifiers — evidence inputs only.
  Acceptance criteria:
  - External scope oracle reports `scope_original_inventory=PASS`, `scope_reconciliation=PASS`, `scope_remediation=PASS`, `legacy_inventory=PASS`, `head_stability=PASS`, and final gate `LOCAL_PASS`.
  - Final delta count is derived from raw Git and recorded; it equals the plan-derived expected reconstruction plus actual authorized remediation paths, with overlaps deduplicated. No hardcoded `83` comparison exists.
  - Exactly one parent exists for every reconstructed/remediation commit; no merge, rename/copy, symlink, mode/type drift, unexpected path, dirty file, or untracked file exists.
  QA scenarios:
  - happy: run the external oracle twice against the same commit/tree and require identical canonical fact digests with distinct launcher nonces/receipt IDs.
  - failure: move the ref during a run, dirty a file, add an allowed-union path to the wrong commit, add an untracked file, introduce rename/mode/symlink/parent drift, delete/rewrite a legacy artifact, or coordinate branch table/verifier changes; each fails with `NO-GO_SCOPE_*` or `NO-GO_HEAD_DRIFT`.
  - Evidence: `<attemptDir>/task-9-audit-evidence-independence-dev-approved.json`
  Commit: N | exact-head freeze; any fix returns to Todo 5-8 and creates a new epoch

- [ ] 10. Execute fresh exact-head non-Docker gates through the trusted launcher
  What to do:
  - With the frozen Todo 9 subject, have the external launcher execute every non-Docker command from Verification strategy itself; do not import claimed exits/markers from branch evidence.
  - Capture one receipt per immutable requirement ID, then rerun the external `LOCAL_GATE_AGGREGATE` oracle rather than trusting those receipts.
  - Require public-safety scanning of the final tracked tree and external summaries, JSON/schema/fixture validation, markdown links, Phase-0, Phase-1 focused, Phase-2, receipt, manifest, scope, and causal-harness unit suites.
  - Read the branch ref/dirty state before and after every command and after the aggregate.
  Must NOT do:
  - Do not skip a gate because a historical run passed, use CI job name `preflight` as evidence of full `make preflight`, accept a marker with nonzero exit, or modify the subject after execution.
  Parallelization: Wave 3 | Blocked by: 9 | Blocks: 11-12, F1-F6
  References:
  - Verification strategy command catalog in this plan.
  - `Makefile:88-107` — local/full gate distinction.
  - `.github/workflows/ci.yml:17-36` — remote job naming caveat.
  Acceptance criteria:
  - Every required command is launched by the trusted launcher, exits `0`, has no signal/timeout/spawn error/descendant leak, contains no `NO-GO_*`, and is bound to the frozen subject.
  - The fresh aggregate rerun observes all required result facts and emits `LOCAL_PASS`; cached receipts alone cannot reproduce the aggregate.
  - Branch ref/tree/parents and clean state match Todo 9 before and after each invocation.
  QA scenarios:
  - happy: execute the full non-Docker catalog and fresh aggregate; record only public-safe digests/counts/durations.
  - failure: replace one command with `exit 97`, copy a previous receipt, replay a nonce/ID, emit PASS then exit `2`, move the branch ref, dirty the tree, timeout/signal a child, or omit a required gate; each aggregate fails explicitly.
  - Evidence: `<attemptDir>/task-10-audit-evidence-independence-dev-approved.json`
  Commit: N | external exact-head evidence only

- [ ] 11. Execute fresh exact-head Docker/preflight/F3 acceptance and post-cleanup oracle
  What to do:
  - Reconfirm Docker/Compose, exactly three fixed volumes, protected runtime binding by secrets plus Kafka cluster identity, subject/ref stability, and no partial bootstrap state.
  - Run full `rtk make preflight` on the authorized Docker-capable Development host through the trusted launcher.
  - Run fixed `F3_QUALIFICATION` through the trusted launcher with `as_of_utc=2026-01-02T03:04:05Z` and a launcher-generated invocation ID. The product entry point must execute the retained Phase-2 vertical slice, rollback/recovery, real idempotency, adversarial SQL, incompatible-schema, fresh-shell replay, capacity capture, and NOC verification.
  - Independently capture the direct pre-cleanup five-table snapshot and Phase-1/runtime identities, wait for all children, perform selected-run cleanup/stop, verify post-cleanup state, and only then publish the qualifying F3 receipt.
  - Rerun the external `F3_QUALIFICATION` oracle after publication and reread the branch ref/dirty state.
  Must NOT do:
  - Do not bootstrap a random root against fixed volumes, rely on `runtime.env` root text, persist the runtime path, use raw logs/dumps, mask cleanup, delete volumes, emit a qualifying pre-clean receipt, or treat Docker absence as skipped readiness.
  Parallelization: Wave 3 | Blocked by: 10 | Blocks: 12, F1-F6
  References:
  - `.omo/plans/phase1-or-phase2-implementation-continuation.md:61-115,745-747,792-798` — owner runtime, F3, PostgreSQL, and cleanup contract.
  - `scripts/phase2_final_acceptance.py`, `phase2_verify_postgres_recovery.py`, `phase2_capture_capacity_posture.py`, `phase2_verify_noc_artifact.py`.
  - Appendix E — fixed F3 requirement/step/table contract.
  Acceptance criteria:
  - `rtk make preflight` exits `0` under the launcher.
  - All F3 child steps exit `0`; pre-cleanup tuples are nonzero and identity-consistent; Phase-1 fingerprints remain unchanged; cleanup/stop succeeds; selected-run counts, services, one-offs, and temp artifacts are zero; exactly three fixed volumes remain.
  - Sole qualifying receipt is published after cleanup, binds the pre-clean snapshot hash plus all outcomes, and the fresh external oracle emits `LOCAL_PASS`.
  - Any failure produces non-PASS, preserves volumes, and leaves no qualifying receipt.
  QA scenarios:
  - happy: run full F3 once against the retained synthetic runtime and then rerun the independent oracle.
  - failure: Docker missing, partial volumes, mismatched secrets/Kafka identity, wrong run/manifest/DB/capacity/NOC/F3 ID, zero pre-clean state, product-only summary, child exit/signal/timeout, cleanup failure, lingering state, missing/extra volume, or ref drift each produces the corresponding `NO-GO_F3_*`.
  - Evidence: `<attemptDir>/task-11-audit-evidence-independence-dev-approved.json`
  Commit: N | external Docker/milestone evidence only

- [ ] 12. Run final causal coverage against the same frozen exact head
  What to do:
  - Extract the frozen commit through `git archive` into a fresh isolated temporary tree. Keep external receipts in a separately descriptor-opened directory; block original/subject worktree reads.
  - Have the plan-owned coverage oracle derive all final changed Python paths from raw Git. Apply the plan-owned executable-line classifier, deterministic selector discovery, trace, observable probe, and mutation algorithm to every path.
  - Run each exact selected unittest once at baseline, then each authorized mutation in a fresh extraction. Prove source digest change, unique AST locator, changed node execution, and intended selected-test failure.
  - Cover deleted/module-only/test/subprocess files according to Appendix E; no unclassified Python path may pass.
  - Rerun the external coverage aggregate oracle after all claims and reread the branch ref.
  Must NOT do:
  - Do not load a branch-authored mapping as authority, reuse Todo 6 unit fixtures as final evidence, run from the original worktree, accept aggregate percentage, or leave an unclassified path/mutant.
  Parallelization: Wave 3 | Blocked by: 11 | Blocks: F1-F6
  References:
  - `scripts/phase2_verify_python_coverage.py` — subject-side mirror only.
  - Appendix E — authoritative classifier/selector/trace/probe/mutation/isolation algorithm.
  - Frozen Todo 9 external scope facts — authoritative final changed-Python set.
  Acceptance criteria:
  - Coverage report key set equals the final changed-Python set exactly.
  - Every claim has `testsRun=1`, clean baseline, non-module changed-callable hit, observed probe, non-no-op executed mutant, and intended test failure; no skip/expected failure/import error/timeout/survivor exists.
  - External coverage aggregate rerun emits `LOCAL_PASS`, with exact subject/tree/parents/plan/oracle bindings and stable branch ref.
  QA scenarios:
  - happy: execute all final claims from isolated archives; randomly recheck at least three claim fact graphs by a second fresh launcher invocation.
  - failure: placeholder/no-op test, import-only hit, skip/expected-failure, zero/multiple selector, wrong test module, original-worktree import, child-receipt omission, ambiguous/no-op/unexecuted/surviving mutant, module-only/deleted file without disposition, or ref drift each causes explicit `NO-GO_TEST_*`.
  - Evidence: `<attemptDir>/task-12-audit-evidence-independence-dev-approved.json`
  Commit: N | external causal-coverage evidence only

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.

- [ ] F1. Plan/spec compliance audit
  - Launch an independent read-only reviewer with the exact plan-pinned F1 prompt from Appendix E.
  - Bind structured output to the Todo 9 commit/tree/parents, full plan SHA, original plan SHA `a5b4527…`, base `e20c8e3…`, and all authority hashes.
  - Verify every Must have/Must NOT have, Todo dependency, original ten-Todo acceptance intent, Phase-1 preservation, open-condition/nonclaim boundary, and evidence epoch.
  - Branch-authored Markdown, prose markers, or missing launcher completion cannot qualify.
  - Evidence: `<attemptDir>/f1-plan-spec.json`

- [ ] F2. Code and evidence-quality review
  - Launch an independent read-only reviewer with Appendix E's exact F2 prompt.
  - Review the complete `e20c8e3…<subject>` diff, strict receipt/schema implementation, process lifecycle, descriptor/TOCTOU safety, exact-head fixed-point avoidance, public-safety, test quality, and whether any qualifying claim remains self-attested.
  - Falsify with caller PASS/nonzero exit, cached receipt, coordinated source/test/manifest edits, branch-oracle substitution, and tracked final-head PASS.
  - Evidence: `<attemptDir>/f2-code-evidence.json`

- [ ] F3. Synthetic runtime manual QA
  - Launch an independent QA executor with Appendix E's exact F3 review prompt and matching artifact surface.
  - Reobserve the retained synthetic runtime results, direct pre-clean snapshot binding, recovery/idempotency/adversarial/fresh-shell/NOC behavior, cleanup/stop state, and three fixed volumes without using raw sensitive material.
  - It must validate the launcher-owned F3 invocation and independently check post-clean state; it cannot reuse the review target's verdict.
  - Evidence: `<attemptDir>/f3-synthetic-runtime-qa.json`

- [ ] F4. Security and public/private boundary review
  - Launch an independent read-only security reviewer with Appendix E's exact F4 prompt.
  - Verify public-only synthetic data, no credential/path/raw-output leakage, no write-capable source/control path, descriptor/environment isolation, subprocess safety, fixed-volume preservation, dependency/supply-chain non-expansion, and no remote mutation.
  - Any Critical/High unresolved finding or public/private-boundary uncertainty is a NO-GO.
  - Evidence: `<attemptDir>/f4-security-boundary.json`

- [ ] F5. Scope, terminal, and governance fidelity review
  - Launch an independent read-only reviewer with Appendix E's exact F5 prompt.
  - Recompute original inventories, prerequisite disposition, ten-Todo paths, final two-tree diff, modes/types/parents/clean state, remediation allowlist, legacy hash inventory, closed result vocabulary, and owner-only boundary.
  - Explicitly reject hardcoded `83`, missing fifth lane, branch-local scope authority, stale head, remote claim, governance status change, or `DEV-APPROVED`.
  - Evidence: `<attemptDir>/f5-scope-terminal-governance.json`

- [ ] F6. Terminal join and owner-handoff record
  - Run only after F1-F5 all terminate. The trusted launcher validates each session's exact prompt hash, session identity, observed completion, structured schema, exact subject/tree/parents/plan binding, and APPROVE verdict.
  - Rerun the external scope, local-gate, F3, coverage, historical-inventory, and head-stability oracles. Do not trust cached receipts or the review JSON as authority.
  - If all fresh facts and five lanes pass, emit external final result:
    `result=READY_FOR_OWNER_HANDOFF`,
    `local_gate=LOCAL_PASS`,
    `remote_ci=NOT_RUN_OWNER_ONLY`,
    `github_mutation=NOT_PERFORMED`,
    `dev_approved=false`.
  - Prepare a public-safe local PR body/checklist and owner disposition packet bound to the exact subject. Do not push or mutate GitHub.
  - Any failed/missing/stale lane, oracle discrepancy, ref/dirty drift, or file change returns to the relevant Todo and then reruns Todos 9-12 and F1-F6.
  - Evidence: `<attemptDir>/f6-terminal-handoff.json`

## Commit strategy

- Never commit `.omo/`, external receipts, raw runtime evidence, review outputs, exact-head verdicts, or the owner-supplied plan SHA.
- Reconstruction history is eleven single-parent commits:
  1. `fix(phase1): preserve image remediation on current main`
  2. ten replayed original Phase-2 commits with original subjects and exact Todo path sets.
- Audit-hardening commits follow reconstruction:
  1. `feat(evidence): add strict phase2 execution receipts`
  2. `test(phase2): require causal changed-python coverage`
  3. `feat(phase2): supervise independent final acceptance`
  4. `fix(phase2): bind audit-ready local handoff`
- Before each commit: stage only the current Todo's Appendix F paths, ensure no staged file has unstaged hunks, run the Todo's focused tests, verify the index path/mode set externally, then commit. Never use `git commit --only`.
- A failed commit gate leaves the commit uncreated. A later fix creates a new coherent commit only within the owning Todo; do not hide failures with fixup/squash after exact-head evidence begins.
- After Todo 9, no tracked commit is allowed. Any required tracked change invalidates the epoch and returns to the owning implementation Todo.
- No push, force-push, merge, tag, or GitHub mutation is authorized by this plan.

## Success criteria

- The owner-supplied final plan SHA and all plan-owned authority/oracle blocks verify before any action; `heredoc_integrity=PASS` precedes every heredoc/materialization.
- Original evidence source is pinned by backup ref `9953833…`; original/completed plan reconstruction is verified; legacy evidence inventory is complete and byte-preserved.
- A fresh target branch/worktree exists from exact base `e20c8e3…`; the original/current product worktree and refs are untouched.
- Six prerequisite patches have explicit dispositions; the four security-remediation blobs are ported; current-main Phase-1 closure semantics remain.
- Ten Phase-2 Todos are replayed in exact order with all 77 Todo/path pairs, 58-path original union, modes/types, and single-parent topology validated externally.
- Final whole-PR scope is derived from raw Git and contains only reconstructed authority plus Appendix F remediation paths; no hardcoded `83`, rename/copy, symlink/mode drift, dirty state, or extra path exists.
- Strict receipt and product integration tests reject fabricated/cached/replayed/duplicate/stale/marker-only/nonzero/timeout/signal/spawn/descendant cases.
- Every final changed Python path has independent baseline execution, changed-callable trace, observable probe, non-no-op executed mutation, and intended selected-test failure in an isolated archive.
- Full local non-Docker catalog and `make preflight` are freshly executed by the trusted launcher against the same exact head and pass.
- Fresh F3 proves nonzero pre-clean DB/runtime identity, all retained-runtime behaviors, successful cleanup/stop, zero selected state, and exactly three preserved fixed volumes; the qualifying receipt is emitted only after cleanup.
- Every qualifying aggregate reruns the external oracle and proves branch-ref/dirty stability; cached receipts never authorize.
- Five independent exact-head lanes approve, and F6 independently rejoins/reruns facts.
- Final external result is exactly `READY_FOR_OWNER_HANDOFF` with `LOCAL_PASS`, `remote_ci=NOT_RUN_OWNER_ONLY`, `github_mutation=NOT_PERFORMED`, and `dev_approved=false`.
- The handoff is locally PR-ready for an owner decision. It makes no remote-CI, GitHub, DEV-APPROVED, Staging, Production, connected-source, HA, SLA, or write/control claim.

## Authority block digest index

Hash scope is the exact bytes after each `` `BEGIN <NAME>` `` line's LF and before its matching `` `END <NAME>` `` marker, including all internal/final whitespace.

| Block | Bytes | SHA-256 |
|---|---:|---|
| `AUTHORITY_ROOTS_V1` | 2589 | `2b20bfbda00d1263c77a0049ae719ab779ad8091ca75b00597e343d3bc17ef24` |
| `ORIGINAL_PATCH_INVENTORY_V1` | 7696 | `93ce1427ec3aeac934e159f2d925a7fe1333884646796bac51c318264b903198` |
| `PHASE2_TODO_PATH_AUTHORITY_V1` | 3860 | `bd1edfd6e4a3173152da556fc763c41fee99295fa51560445ca2845466fada82` |
| `LEGACY_FAILURE_INVENTORY_V1` | 3115 | `036a17c9c2161f1c0b7f4fd68edb5497fa50b31c4df031e58c3fc78ed34ec35f` |
| `ORACLE_CONTRACT_V1` | 12069 | `8f44a16eb4a92e7d92bd1915b0a091fdbdccd63437d7cfa51c76780b1dd4f5f5` |
| `REMEDIATION_ALLOWLIST_V1` | 864 | `4cc68690bac41dbeb461ba698164aa25add4546e2c6635575f1415d80bcd433c` |

## Appendix A — immutable roots and reconstruction policy

`BEGIN AUTHORITY_ROOTS_V1`

```text
repository=shuffahaqgzz/dcim-core-platform
original_merge_base_sha=3a92960314df11d68152dc59244d31b93eaa9a57
original_merge_base_tree=c759a1a20f8c59046b55956a2c46dd8954ef98f1
approved_destination_base_sha=e20c8e3569cb171a23fb1e4a9c417074dfb0ae8a
approved_destination_base_tree=2cc61d7bec83ec1624fe930d9fbee6e9157501a2
original_phase2_start_sha=2db4022b756d6d98934234daabce3a28bb8443dc
original_phase2_start_tree=dca6042b6738520603b322cf5fc4961aa0e55e1f
original_subject_sha=995383355f32ac7b70573c5ca756786e1836a954
original_subject_tree=c03d8408b0689b788b45532e3fb144bbaefe7e91
original_subject_backup_ref=backup/phase2-before-pr-prep-20260727
original_owner_plan_sha256=a5b4527d99d61a33c113620688131c82ebfd490ab8161dc979cd488a3e59dc8a
completed_owner_plan_sha256=fabc78ee6d7e0c7d0efdc58efe188aca507a477bcb91064a50b3fd0be3a76d11
phase2_todo_path_table_sha256=67cb81e18e3a77a4243846fb92b364c903bd41d31609e5c27faaf4a9ea812d3e
original_phase2_commits=10
original_phase2_todo_path_pairs=77
original_phase2_unique_paths=58
original_phase2_python_paths=34
candidate_two_tree_paths_e20_to_995=65
candidate_two_tree_python_paths_e20_to_995=35
expected_reconciled_commits_ahead_of_base=11
expected_reconciled_pre_remediation_paths=62
expected_reconciled_pre_remediation_python_paths=35
target_branch=fix/phase2-audit-evidence-independence
target_worktree=/home/infra/dcim-core-platform-worktrees/phase2-audit-evidence-independence-20260727
result_gate_success=LOCAL_PASS
result_final_success=READY_FOR_OWNER_HANDOFF
remote_ci=NOT_RUN_OWNER_ONLY
github_mutation=NOT_PERFORMED
dev_approved=false
```

Policy:

1. Expected raw plan SHA comes only from the owner's start-work request.
2. Original commits 1-5 may map only to `UPSTREAM_EQUIVALENT`; original commit 6 maps to one reconciled four-path commit; original commits 7-16 map ordinally to ten rewritten single-parent commits.
3. At the prerequisite checkpoint, four base-retained files equal `e20c8e3…`: `README.md` and the three Phase-1 closure documents. Four ported files equal `2db4022…`: Grafana Dockerfile, recipes, license dispositions, and foundation-image test.
4. After Phase-2 replay, the three Phase-1 closure documents remain base-identical. `README.md` may differ only by Phase-2 additions originating in original Todos 5, 6, and 9; its current-main Phase-1 caveats/count semantics remain.
5. Exact commit counts and expected path counts are checkpoint assertions, not substitutes for raw path/mode/type/tree comparison.
6. Any base/ref/plan/object drift or unexpected conflict requires a new owner-approved plan SHA.

`END AUTHORITY_ROOTS_V1`

## Appendix B — original 16-patch inventory

`BEGIN ORIGINAL_PATCH_INVENTORY_V1`

| # | Original commit | Parent | Subject | Exact changed paths |
|---|---|---|---|---|
| 1 | `cefcfdf4fb77dc7cb9a4f88f370598c387762a34` | `3a92960314df11d68152dc59244d31b93eaa9a57` | `fix(foundation): add clean runtime acceptance guardrails` | `Makefile`; `README.md`; `deploy/compose/README.md`; `deploy/compose/dev-build/compose.yaml`; `docs/phase1/DEVELOPMENT-HANDOVER.md`; `docs/phase1/FOUNDATION-RUNBOOK.md`; `docs/phase1/ISSUE-9-ACCEPTANCE-MATRIX.md`; `docs/phase1/ISSUE-9-CLOSURE-PACKAGE.md`; `docs/runbooks/FOUNDATION.md`; `scripts/foundation_acceptance.py`; `scripts/foundation_evidence_summary.py`; `scripts/foundation_policy.py`; `scripts/foundation_smoke.py`; `scripts/protected_runtime.py`; `tests/test_foundation_acceptance.py`; `tests/test_foundation_evidence_summary.py`; `tests/test_foundation_policy.py`; `tests/test_foundation_smoke.py` |
| 2 | `3b086ac72d6ac9754764286c9bf5d0f7cb92b263` | `cefcfdf4fb77dc7cb9a4f88f370598c387762a34` | `docs(issue9): update closure tracking and package state` | `docs/phase1/DEVELOPMENT-HANDOVER.md`; `docs/phase1/ISSUE-9-ACCEPTANCE-MATRIX.md`; `docs/phase1/ISSUE-9-CLOSURE-PACKAGE.md` |
| 3 | `dd3b19573b0306c40ec89b9b219b233a1daf466a` | `3b086ac72d6ac9754764286c9bf5d0f7cb92b263` | `fix(foundation): fail closed on acceptance evidence` | `Makefile`; `scripts/foundation_acceptance.py`; `tests/test_foundation_acceptance.py` |
| 4 | `5dbf47154f287bc35756d4ab0a3cafebaf3b1c56` | `dd3b19573b0306c40ec89b9b219b233a1daf466a` | `fix(foundation): remediate fresh image findings` | `deploy/compose/README.md`; `deploy/compose/derived-images/grafana/Dockerfile`; `deploy/compose/derived-images/kafka/Dockerfile`; `deploy/compose/derived-images/license-dispositions.json`; `deploy/compose/derived-images/prometheus/Dockerfile`; `deploy/compose/derived-images/recipes.json`; `deploy/compose/dev-build/compose.yaml`; `docs/adr/0013-derived-hardened-foundation-images.md`; `docs/adr/0014-official-release-binary-source-provenance.md`; `docs/adr/0015-full-source-prometheus-grpc-remediation.md`; `docs/adr/README.md`; `docs/phase1/ISSUE-9-ACCEPTANCE-MATRIX.md`; `docs/phase1/ISSUE-9-CLOSURE-PACKAGE.md`; `scripts/foundation_images.py`; `scripts/foundation_policy.py`; `scripts/foundation_supply_chain.py`; `tests/test_foundation_images.py`; `tests/test_foundation_lifecycle.py`; `tests/test_foundation_policy.py`; `tests/test_foundation_supply_chain.py` |
| 5 | `872df38a4ede87d129533965b28ca335672916bc` | `5dbf47154f287bc35756d4ab0a3cafebaf3b1c56` | `fix(foundation): bind smoke evidence to prometheus derivative` | `docs/phase1/ISSUE-9-CLOSURE-PACKAGE.md`; `scripts/foundation_smoke.py`; `tests/test_foundation_smoke.py` |
| 6 | `2db4022b756d6d98934234daabce3a28bb8443dc` | `872df38a4ede87d129533965b28ca335672916bc` | `fix(phase1): remediate kafka image findings` | `deploy/compose/derived-images/grafana/Dockerfile`; `deploy/compose/derived-images/kafka/Dockerfile`; `deploy/compose/derived-images/license-dispositions.json`; `deploy/compose/derived-images/recipes.json`; `tests/test_foundation_images.py`; `tests/test_foundation_images_kafka_remediation.py` |
| 7 | `7efd2bc83f3a6edd03377c8476588cc8591df030` | `2db4022b756d6d98934234daabce3a28bb8443dc` | `docs(phase2): define first vertical slice boundary` | `Makefile`; `docs/phase2/FIRST-VERTICAL-SLICE.md`; `scripts/check_public_repo_safety.py`; `scripts/phase2_capture_worktree_baseline.py`; `tests/test_phase2_vertical_slice.py` |
| 8 | `14c61f52bb1b6df4aeecc7485df13cc7af215fab` | `7efd2bc83f3a6edd03377c8476588cc8591df030` | `test(fixtures): add phase2 synthetic source corpus` | `fixtures/synthetic/README.md`; `fixtures/synthetic/context/alias-collision.json`; `fixtures/synthetic/context/asset-server-001.json`; `fixtures/synthetic/context/asset-switch-001.json`; `fixtures/synthetic/context/ci-server-001.json`; `fixtures/synthetic/context/ci-switch-001.json`; `fixtures/synthetic/events/p1-redfish-health.json`; `fixtures/synthetic/events/p2-network-utilization.json`; `fixtures/synthetic/expected/phase2/p1-redfish-health.json`; `fixtures/synthetic/expected/phase2/p2-network-utilization.json`; `fixtures/synthetic/sources/redfish/malformed-input.json`; `fixtures/synthetic/sources/redfish/p1-redfish-health.json`; `fixtures/synthetic/sources/snmpv3/duplicate-replay-input.json`; `fixtures/synthetic/sources/snmpv3/p2-network-utilization.json`; `tests/test_phase2_fixtures.py` |
| 9 | `3c42260454d6f6652ebd0034380c89327b237f73` | `14c61f52bb1b6df4aeecc7485df13cc7af215fab` | `test(contracts): validate phase2 synthetic fixtures` | `contracts/README.md`; `scripts/identity_contracts.py`; `scripts/json_types.py`; `scripts/phase2_collision_contracts.py`; `scripts/phase2_disposition_contracts.py`; `scripts/phase2_source_contracts.py`; `scripts/validate-json.py`; `scripts/validate_synthetic_fixtures.py`; `tests/test_contracts.py`; `tests/test_phase2_contracts.py`; `tests/test_phase2_fixture_regressions.py`; `tests/test_phase2_schema_regressions.py`; `tests/test_validate_synthetic_fixtures.py` |
| 10 | `e76a807d07c2a5833e39704bcca7502d65270152` | `3c42260454d6f6652ebd0034380c89327b237f73` | `feat(connectors): add synthetic phase2 source adapters` | `connectors/redfish/README.md`; `connectors/redfish/synthetic_adapter.py`; `connectors/snmp/README.md`; `connectors/snmp/synthetic_adapter.py`; `tests/test_synthetic_connectors.py` |
| 11 | `627bcc607f845297efea1399a6853c656d2bb6db` | `e76a807d07c2a5833e39704bcca7502d65270152` | `feat(ingestion): add phase2 synthetic lifecycle engine` | `README.md`; `scripts/phase2_vertical_slice.py`; `tests/test_phase2_vertical_slice.py` |
| 12 | `230b5f7813cae9f14ae833706b56f5c23b59f919` | `627bcc607f845297efea1399a6853c656d2bb6db` | `feat(storage): persist phase2 slice in foundation postgres` | `README.md`; `deploy/compose/dev-build/config/postgres/phase2-vertical-slice-migration.json`; `scripts/phase2_foundation_runtime_guard.py`; `scripts/phase2_postgres.py`; `scripts/phase2_postgres_adversarial_sql_smoke.py`; `scripts/phase2_postgres_idempotency_smoke.py`; `scripts/phase2_postgres_rollback_smoke.py`; `scripts/phase2_verify_postgres_recovery.py`; `scripts/phase2_vertical_slice.py`; `tests/test_phase2_vertical_slice.py` |
| 13 | `ef77b982c3d9326f46eee3e7b52ea5ad87617f1b` | `230b5f7813cae9f14ae833706b56f5c23b59f919` | `feat(api): generate phase2 noc read model` | `scripts/phase2_capture_capacity_posture.py`; `scripts/phase2_noc_view.py`; `scripts/phase2_verify_noc_artifact.py`; `scripts/phase2_vertical_slice.py`; `tests/test_phase2_vertical_slice.py` |
| 14 | `71a18d4e74d3ef765e706d41302846fd5bb8ebfa` | `ef77b982c3d9326f46eee3e7b52ea5ad87617f1b` | `build(phase2): add vertical slice gates` | `Makefile`; `tests/test_phase2_docs.py`; `tests/test_phase2_vertical_slice.py` |
| 15 | `ef3af2c31cf0d019e8d2e310b1689480dda84cbd` | `71a18d4e74d3ef765e706d41302846fd5bb8ebfa` | `docs(phase2): document vertical slice operation` | `README.md`; `ROADMAP.md`; `docs/phase2/DEVELOPMENT-HANDOVER.md`; `docs/phase2/FIRST-VERTICAL-SLICE.md`; `docs/phase2/RUNBOOK.md`; `tests/test_phase2_docs.py` |
| 16 | `995383355f32ac7b70573c5ca756786e1836a954` | `ef3af2c31cf0d019e8d2e310b1689480dda84cbd` | `docs(phase2): record vertical slice verification` | `scripts/identity_contracts.py`; `scripts/phase2_capture_worktree_baseline.py`; `scripts/phase2_foundation_runtime_guard.py`; `scripts/phase2_scope_safety.py`; `scripts/phase2_verify_completion_manifest.py`; `scripts/phase2_verify_noc_artifact.py`; `scripts/phase2_verify_scope_diff.py`; `scripts/phase2_verify_terminal_manifest.py`; `tests/test_phase2_docs.py`; `tests/test_phase2_vertical_slice.py`; `tests/test_synthetic_connectors.py`; `tests/test_validate_synthetic_fixtures.py` |

`END ORIGINAL_PATCH_INVENTORY_V1`

## Appendix C — authoritative Phase-2 Todo/path table

`BEGIN PHASE2_TODO_PATH_AUTHORITY_V1`

Canonicalization: JSON object keys are string Todo IDs sorted numerically for construction; each value is a bytewise-sorted unique path list. Serialize with Python `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n"`. The approved digest is `67cb81e18e3a77a4243846fb92b364c903bd41d31609e5c27faaf4a9ea812d3e`.

| Todo | Count | Exact paths |
|---|---:|---|
| 1 | 5 | `Makefile`; `docs/phase2/FIRST-VERTICAL-SLICE.md`; `scripts/check_public_repo_safety.py`; `scripts/phase2_capture_worktree_baseline.py`; `tests/test_phase2_vertical_slice.py` |
| 2 | 15 | `fixtures/synthetic/README.md`; `fixtures/synthetic/context/alias-collision.json`; `fixtures/synthetic/context/asset-server-001.json`; `fixtures/synthetic/context/asset-switch-001.json`; `fixtures/synthetic/context/ci-server-001.json`; `fixtures/synthetic/context/ci-switch-001.json`; `fixtures/synthetic/events/p1-redfish-health.json`; `fixtures/synthetic/events/p2-network-utilization.json`; `fixtures/synthetic/expected/phase2/p1-redfish-health.json`; `fixtures/synthetic/expected/phase2/p2-network-utilization.json`; `fixtures/synthetic/sources/redfish/malformed-input.json`; `fixtures/synthetic/sources/redfish/p1-redfish-health.json`; `fixtures/synthetic/sources/snmpv3/duplicate-replay-input.json`; `fixtures/synthetic/sources/snmpv3/p2-network-utilization.json`; `tests/test_phase2_fixtures.py` |
| 3 | 13 | `contracts/README.md`; `scripts/identity_contracts.py`; `scripts/json_types.py`; `scripts/phase2_collision_contracts.py`; `scripts/phase2_disposition_contracts.py`; `scripts/phase2_source_contracts.py`; `scripts/validate-json.py`; `scripts/validate_synthetic_fixtures.py`; `tests/test_contracts.py`; `tests/test_phase2_contracts.py`; `tests/test_phase2_fixture_regressions.py`; `tests/test_phase2_schema_regressions.py`; `tests/test_validate_synthetic_fixtures.py` |
| 4 | 5 | `connectors/redfish/README.md`; `connectors/redfish/synthetic_adapter.py`; `connectors/snmp/README.md`; `connectors/snmp/synthetic_adapter.py`; `tests/test_synthetic_connectors.py` |
| 5 | 3 | `README.md`; `scripts/phase2_vertical_slice.py`; `tests/test_phase2_vertical_slice.py` |
| 6 | 10 | `README.md`; `deploy/compose/dev-build/config/postgres/phase2-vertical-slice-migration.json`; `scripts/phase2_foundation_runtime_guard.py`; `scripts/phase2_postgres.py`; `scripts/phase2_postgres_adversarial_sql_smoke.py`; `scripts/phase2_postgres_idempotency_smoke.py`; `scripts/phase2_postgres_rollback_smoke.py`; `scripts/phase2_verify_postgres_recovery.py`; `scripts/phase2_vertical_slice.py`; `tests/test_phase2_vertical_slice.py` |
| 7 | 5 | `scripts/phase2_capture_capacity_posture.py`; `scripts/phase2_noc_view.py`; `scripts/phase2_verify_noc_artifact.py`; `scripts/phase2_vertical_slice.py`; `tests/test_phase2_vertical_slice.py` |
| 8 | 3 | `Makefile`; `tests/test_phase2_docs.py`; `tests/test_phase2_vertical_slice.py` |
| 9 | 6 | `README.md`; `ROADMAP.md`; `docs/phase2/DEVELOPMENT-HANDOVER.md`; `docs/phase2/FIRST-VERTICAL-SLICE.md`; `docs/phase2/RUNBOOK.md`; `tests/test_phase2_docs.py` |
| 10 | 12 | `scripts/identity_contracts.py`; `scripts/phase2_capture_worktree_baseline.py`; `scripts/phase2_foundation_runtime_guard.py`; `scripts/phase2_scope_safety.py`; `scripts/phase2_verify_completion_manifest.py`; `scripts/phase2_verify_noc_artifact.py`; `scripts/phase2_verify_scope_diff.py`; `scripts/phase2_verify_terminal_manifest.py`; `tests/test_phase2_docs.py`; `tests/test_phase2_vertical_slice.py`; `tests/test_synthetic_connectors.py`; `tests/test_validate_synthetic_fixtures.py` |

Rules: exact equality per Todo; no prefixes/globs/aliases; no `.`/`..`/absolute path; no missing/additional/moved path; no rename/copy; exact original ordinal parent chain. Counts are `5,15,13,5,3,10,5,3,6,12`, total pairs `77`, unique union `58`, Python union `34`.

`END PHASE2_TODO_PATH_AUTHORITY_V1`

## Appendix D — historical FAIL/NO-GO preservation inventory

Source directory: `.omo/evidence/phase1-or-phase2-implementation-continuation/` in the original backup worktree. This conservative inventory includes every file whose bytes contain `FAIL` or `NO-GO`, even when the term appears in a negative-test contract rather than the file's final verdict.

`BEGIN LEGACY_FAILURE_INVENTORY_V1`

```text
3578fe0207cd019a0ba187fb69392d4c81e73e39a2c295c62d44872a9e60729a  debug-runtime-audit-99538335.md
1cad756eed90dbbee3cc5567ae53dd12b0f9f08c156c4dcda7fa25ea211e556a  debug-runtime-audit.md
6fd639fdb1678a6e0091d19a5f525df632fe73aded4ef54ca0738f234e44b2f1  f3-real-qa.md
79a11298784684143be4b8d42599f8ad68922d3d417deced3a3715e4b7c915ea  f5-terminal-manifest.md
392650e5e0edbe5c818e985b57648da6ec69be8189e1836cfe600594f65b5ceb  phase1-kafka-prerequisite-remediation.md
da75d1368a9adba61225d8748171e2fbb0b94277bee8749cbd3c947902e75ab8  review-code-quality.md
8bdc0d34bf0fea85eb267226097563be8433ada8ebfc840a32ed63f66bc532fc  review-context-mining.md
f8b86b92cc2ffd597a286b0f68e5557ec9adecfcf67655b8b6e347efb7b50259  review-final-52e7d6e8-context.md
a5c801aafd690bb4c2d276a7fc91afb7beb3a187654c7144e43d4d3419e6dfa1  review-final-52e7d6e8-qa.md
cde40b03affba8997d9cc77d5cf71195416f7bbe83ca797ee6cde9885c864821  review-final-52e7d6e8-security.md
c72340790a8a06b920e294eefc59da0e5cbc6506a60590e359fe7ce36a3adcda  review-final-99538335-context.md
9bd61eee291fb1800a1be4dcc5b20ebc35faefb70129f60bae30a04cfe2449cb  review-final-99538335-goal.md
42b9303efdc1481d586195f44eb9d7a7e332dcd8c43a7f71299dd3c7ba193aac  review-goal-constraints.md
572f1f859e7e0194e55404d5c2e158af2412a84dad355140b2b5e50b1582678a  review-qa.md
8ab6e901e455ee5d3c63106d574cfd39ed2f4bc02d3cbbe1508e44e6633df5c8  review-remediation-runtime-success-52e7d6e8.md
7e1255b2bdbd4680f4aebf37bf0edc9d9f029e0232dd26c9830b5fad693ebc64  review-remediation-runtime-success-99538335-rerun.md
5f9540d3ca314565dcba2674cd95bdde5f63a7bce23f33f6a676041e1ac3a0ee  review-remediation-runtime-success-99538335.md
68fd52f23d24e7d7567d0e904d51a0af02a0cfab277376e430fdcafd67339dcb  review-remediation-runtime-success-e4294c44.md
846e8e4e41358b6b3b8a42e2054586504f4b029ca8c7a1741a0947440f81f796  review-remediation-runtime.md
61b71b19c7b20f27e6cb7c937ea3ac0695758e1e7fa02fc6abc26aa27ba0e405  task-1-boundary.md
40bb77c866370c547c4334d160cd8d7b3fa8e7f04faa17c8bed571ad3c340bd5  task-10-final-verification.md
bc3831b3c3bdf5fd65f2824d1166e31a318f8ae734c25f2830d7c1042e804c7c  task-3-contract-validation.md
06a642eee3442c861e7b23e597852fdecd37525755c8567392c72c8f7ef54aad  task-4-connectors.md
9a57eaa46c67e4628aba265c167a0abce9deab916d2117a679ddf10e82f5aa40  task-5-lifecycle.md
98d235cdebe25dc9c1d5dd9f378f29a5a64ba6c4bf2c985defc3f9147b2161ab  task-6-postgres.md
5a1636f5d0d4472abfd313319c38f57b1ff39344abc2b0857746f92ab4b25f7a  task-7-noc-view.md
3fd19891e22d326170e12c34625fdf1fff07a57855c3dd37b0e5716bc0c3b192  task-8-make-targets.md
5629397c5ed473a5c91fa442d101f1fdf93e9f929979eb954b6d8c5cc12ebed3  task-9-docs.md
b8d44f568f68a5f641d827210a57f1837cf45f7bf0fa3be9cfa4ed87bcf3b50a  terminal-manifest.json
```

The snapshot copies every named file byte-for-byte into the new epoch's `legacy/` directory with the same basename plus a canonical inventory. Missing, extra, duplicate, rewritten, symlinked, non-regular, hash-mismatched, or reclassified entries fail. A new success record must include `supersedes_for_qualification` references but may not overwrite these bytes.

`END LEGACY_FAILURE_INVENTORY_V1`

## Appendix E — plan-owned oracle, requirement, receipt, coverage, F3, and review contract

The trusted launcher is the external `$omo:start-work` executor acting on this exact plan. No tracked repository script is the trusted launcher. Tracked scripts may mirror this contract and expose observations, but every qualifying decision is recomputed by the external launcher from raw process/Git/runtime facts.

`BEGIN ORACLE_CONTRACT_V1`

### Bootstrap and descriptor execution

1. Input `expected_plan_sha256` is exactly one externally supplied lowercase 64-hex string.
2. Open the plan with `O_RDONLY|O_CLOEXEC|O_NOFOLLOW`; require regular file, stable `(dev, ino, mode, uid, gid, size, mtime_ns)` before/after a complete descriptor read.
3. Hash the raw bytes and compare to `expected_plan_sha256`.
4. Extract each `BEGIN …`/`END …` block from that raw buffer; require exactly one ordered occurrence, no nesting, no duplicate marker, and no missing final LF.
5. Hash each extracted block and record the digest in the external attempt header. The plan raw SHA remains the root; a digest stated only inside its own block is never authority.
6. Place executable oracle/executor material derived from this contract in anonymous `memfd` descriptors where available, otherwise exclusive `0600` files inside a freshly created `0700` temp directory opened by descriptor. Rehash the execution descriptor immediately before spawn.
7. Spawn with `pass_fds`, `close_fds=True`, new process group/session, bounded timeout, subject-tree current directory only when the requirement needs it, and environment allowlist `PATH`, fixed locale, fixed timezone, and requirement-specific synthetic variables. Remove `PYTHONPATH`, `PYTHONHOME`, `PYTHONSTARTUP`, user-site, shell startup, credential, proxy, Docker override, and unrelated variables.
8. Pin Python major/minor and executable digest plus Git/Make/Docker/Compose identities. Reject incompatible drift.
9. Read subject branch ref, commit, tree, parents, index, tracked and untracked state before and after every requirement. Any change is `NO-GO_HEAD_DRIFT`.
10. A stored receipt is a cache. Qualifying aggregates rerun this algorithm and inspect raw facts.

### Requirement catalog

| Requirement ID | Owned operation | Timeout ceiling | Success fact |
|---|---|---:|---|
| `AUTHORITY_BOOTSTRAP` | plan/block/descriptor/toolchain/legacy/runtime pre-flight | 300 s | `heredoc_integrity=PASS` and all raw facts valid |
| `RECONCILIATION_SCOPE` | original/reconciled commits, paths, modes, types, blobs, parents, dirty state | 300 s | raw authority equality |
| `LOCAL_PHASE0` | `rtk make phase0-check` | 1800 s | process exit `0` |
| `LOCAL_PHASE2` | `rtk make phase2-check` | 1800 s | process exit `0` |
| `LOCAL_PHASE1_FOCUSED` | exact Phase-1 unittest command in Verification strategy | 1800 s | process exit `0` |
| `LOCAL_RECEIPT_TESTS` | receipt/contract unittest command | 900 s | process exit `0` |
| `LOCAL_PUBLIC_SAFETY` | public-safety command | 900 s | process exit `0` |
| `LOCAL_MARKDOWN_LINKS` | markdown-link command | 900 s | process exit `0` |
| `LOCAL_GATE_AGGREGATE` | fresh recomputation of every required local fact | 600 s | `LOCAL_PASS` |
| `FOUNDATION_PREFLIGHT` | `rtk make preflight` on Docker-capable host | 3600 s | process exit `0` |
| `F3_QUALIFICATION` | full retained-runtime execution, pre-clean snapshot, cleanup/stop/volumes, final join | 7200 s | `LOCAL_PASS` after cleanup |
| `PYTHON_CAUSAL_COVERAGE` | isolated exact-test trace/probe/mutation for every final changed Python path | 14400 s | `LOCAL_PASS` |
| `REVIEW_F1` | plan/spec review | 3600 s | structured `APPROVE` bound to subject |
| `REVIEW_F2` | code/evidence-quality review | 3600 s | structured `APPROVE` bound to subject |
| `REVIEW_F3` | synthetic runtime QA | 3600 s | structured `APPROVE` bound to subject |
| `REVIEW_F4` | security/data-boundary review | 3600 s | structured `APPROVE` bound to subject |
| `REVIEW_F5` | scope/terminal/governance review | 3600 s | structured `APPROVE` bound to subject |
| `REVIEW_JOIN` | validate five sessions and rerun all qualifying oracles | 1800 s | `LOCAL_PASS` |
| `FINAL_HANDOFF` | fresh final recomputation and local handoff packet | 1800 s | `READY_FOR_OWNER_HANDOFF` plus owner-only fields |

### Receipt contract

Strict JSON, UTF-8, one trailing LF, duplicate keys rejected, no unknown fields. Required fields:

```text
schema_version
requirement_id
launcher_nonce
receipt_id
attempt_epoch_id
base_sha
subject_commit_sha
subject_tree_sha
subject_parent_shas
plan_sha256
authority_block_sha256
oracle_contract_sha256
executor_material_sha256
toolchain_identity_sha256
argv
argv_sha256
environment_allowlist_sha256
started_at_utc
finished_at_utc
duration_monotonic_ms
timeout_ms
process_outcome
exit_code
signal
spawn_error_class
stdout_bytes
stdout_sha256
stderr_bytes
stderr_sha256
pass_marker_observations
no_go_marker_observations
artifact_sha256
computed_disposition
branch_ref_before
branch_ref_after
dirty_state_before_sha256
dirty_state_after_sha256
```

`process_outcome` is exactly one of `exited`, `signaled`, `timed_out`, `spawn_error`. `computed_disposition` is computed by the launcher and cannot be supplied by the subject. A receipt ID or nonce may appear once in one requirement only. Exit must be `0`, no signal/timeout/spawn error/descendant leak may exist, required raw facts must pass, and any `NO-GO_*` observation fails regardless of a PASS marker.

### Scope oracle

Use raw `git cat-file`, `rev-list`, `diff-tree --raw -r -M -C`, `ls-tree`, `diff --raw`, and index/worktree status against pinned object IDs. Parse NUL-delimited output. Reject missing objects, abbreviated IDs, non-single-parent mapped commits, merge commits, unexpected empty commits, rename/copy status, non-`100644` remediation files, symlink/submodule/tree where blob expected, path normalization aliases, duplicate paths, wrong ordinal, unexpected conflict resolution, dirty state, and ref movement. Compare original Phase-2 paths to Appendix C, not branch constants. Derive final two-tree counts; do not use `83`.

### Causal coverage oracle

1. Derive the exact final changed-Python set from raw two-tree Git output. Every path needs one disposition: executable, deleted, module-only, or changed-test.
2. Create a fresh `git archive <subject>` extraction per baseline and per mutant. Reject any resolved path outside that extraction. External receipts use a separately opened directory.
3. Parse base/head source with Python AST. Changed executable lines exclude comments, blank lines, imports, annotations without runtime value, type-only blocks, and module docstrings. Map lines to the smallest enclosing callable.
4. Discover `unittest` selectors deterministically, sort bytewise, and execute candidates one at a time. A qualifying selector runs exactly one `TestCase`, has success with zero failure/error/skip/expected-failure/unexpected-success, and traces an authorized changed non-module callable after module load.
5. Record one observable probe class: `failure`, `return`, `filesystem`, `subprocess`, or `database_side_effect`, including the expected observation and absence-of-effect-on-rejection where relevant.
6. Mutation priority on an authorized changed callable is: negate fail-closed comparison; negate boolean guard; replace return constant; alter raised disposition; negate branch predicate; replace an allowlisted side-effect call with no-op. Choose the first bytewise `(path, line, column, operator)` candidate whose unique AST span digest matches.
7. Prove mutation is non-no-op by source digest change and AST change; prove the node executes in the mutated run; rerun the exact selector once; require import/runnable test and failure/error attributable to the selected assertion, not syntax/import/setup failure.
8. A changed test file additionally traces its exact test method and kills a product/input mutant outside that test. A subprocess entrypoint requires a child trace receipt bound to the parent. A deleted/module-only file needs an explicit plan-owned non-executable disposition and a test of its removal/import behavior.
9. Any missing/duplicate path, unrelated placeholder, import-only hit, original-worktree access, zero/multiple/skip/expected-failure target, ambiguous/no-op/unexecuted/surviving mutant, or timeout is `NO-GO_TEST_*`.

### F3 oracle

Fixed table allowlist:

```text
foundation.phase2_runs
foundation.phase2_accepted_events
foundation.phase2_quarantined_events
foundation.phase2_duplicate_events
foundation.phase2_noc_snapshots
```

Required ordered facts:

1. launcher generates `F3_INVOCATION_ID`; fixed clock is `2026-01-02T03:04:05Z`;
2. runtime guard verifies protected material by secrets plus Kafka cluster identity against exactly three fixed volumes;
3. Foundation starts; Phase-1 sentinel and relation/schema fingerprints are captured;
4. production Phase-2 slice, rollback/recovery, real idempotency/concurrency, adversarial SQL, incompatible-schema rollback, rematerialization, capacity, fresh-shell replay, checksum comparison, and NOC verification all exit `0`;
5. before cleanup, direct PostgreSQL queries produce nonzero `(table, count, checksum)` for all five tables and a canonical aggregate digest bound to run ID, input-manifest SHA, fixed clock, F3 ID, capacity digest, NOC digest, and preserved Phase-1 fingerprints;
6. exact Docker process and every child terminate successfully;
7. selected-run cleanup occurs only after snapshot; five selected-run counts become zero; Foundation stop succeeds; services, one-offs, and temp artifacts are zero; exactly three fixed volumes remain;
8. sole qualifying receipt is atomically emitted after step 7 and binds step 5's digest plus every child outcome;
9. fresh external F3 oracle rerun inspects post-clean state and receipt graph. Neither step 5 cache nor step 7 zero state qualifies alone.

### Plan-pinned independent review prompts

All prompts begin: `Review exact subject <commit>/<tree>/<parents> against plan <sha>; use raw repository/runtime facts, not branch-authored verdicts; return strict JSON with verdict APPROVE|REJECT, findings, checked_requirement_ids, subject bindings, and no prose outside JSON.`

- F1 suffix: `Verify every Must have/Must NOT have, dependency, original owner-plan intent, Phase-1 preservation, five review lanes, closed vocabulary, and owner-only boundary.`
- F2 suffix: `Falsify receipt provenance, command execution, TOCTOU/environment isolation, exact-head fixed-point avoidance, causal tests, error handling, and public-safe evidence.`
- F3 suffix: `Reobserve synthetic retained-runtime behavior, nonzero pre-clean DB binding, recovery/idempotency/adversarial/fresh-shell/NOC behavior, successful cleanup/stop, and three preserved volumes.`
- F4 suffix: `Audit secrets/data leakage, source write/control paths, subprocess/environment isolation, fixed-volume safety, dependency/supply-chain change, and unauthorized external mutation.`
- F5 suffix: `Recompute original and final scope, commit/path/mode/type/parent mapping, legacy hash inventory, terminal joins, result vocabulary, open conditions/decisions, and DEV-APPROVED prohibition.`

### Mandatory negative matrix

| Attack/failure | Required rejection |
|---|---|
| wrong/truncated/self-derived plan SHA or changed block | `NO-GO_PLAN_AUTHORITY` |
| plan/oracle pathname replacement after open | `NO-GO_TOCTOU` |
| subject-tree import/startup hook/toolchain drift | `NO-GO_TOOLCHAIN_IDENTITY` |
| fabricated/cached/replayed/duplicate receipt or nonce | `NO-GO_RECEIPT_PROVENANCE` |
| PASS marker with nonzero/signal/timeout/spawn/descendant | `NO-GO_PROCESS_OUTCOME` |
| ref/tree/parents/dirty movement | `NO-GO_HEAD_DRIFT` |
| branch table/verifier/manifest collusion | `NO-GO_SCOPE_AUTHORITY` |
| wrong Todo/path/ordinal/mode/type/rename/copy/symlink | `NO-GO_SCOPE_AUTHORITY` |
| tracked exact-head PASS evidence | `NO-GO_TRACKED_FIXED_POINT` |
| legacy FAIL/NO-GO missing/rewritten/reclassified | `NO-GO_LEGACY_EVIDENCE` |
| symbol/import/no-op/skip/multiple/unmapped/surviving mutant | `NO-GO_TEST_CAUSALITY` |
| pre-clean receipt only or post-clean zero only | `NO-GO_F3_INCOMPLETE_BINDING` |
| Docker absent/partial or runtime identity mismatch | `NO-GO_DOCKER_REQUIRED_FOR_HANDOFF` |
| cleanup/stop/volume preservation failure | `NO-GO_F3_CLEANUP` |
| missing/stale/self-reported review lane | `NO-GO_REVIEW_PROVENANCE` |
| remote/DEV-approved/governance claim | `NO-GO_OWNER_BOUNDARY` |

`END ORACLE_CONTRACT_V1`

## Appendix F — exact remediation path/mode allowlist

`BEGIN REMEDIATION_ALLOWLIST_V1`

All entries are regular Git blobs with mode `100644`. Todos 5-8 may modify only these paths; a Todo may use only the subset named in its own instructions.

```text
Makefile
docs/phase2/DEVELOPMENT-HANDOVER.md
docs/phase2/FIRST-VERTICAL-SLICE.md
docs/phase2/RUNBOOK.md
schemas/phase2-evidence-receipt.schema.json
scripts/phase2_evidence_receipt.py
scripts/phase2_final_acceptance.py
scripts/phase2_verify_completion_manifest.py
scripts/phase2_verify_postgres_recovery.py
scripts/phase2_verify_python_coverage.py
scripts/phase2_verify_scope_diff.py
scripts/phase2_verify_terminal_manifest.py
tests/test_contracts.py
tests/test_phase2_docs.py
tests/test_phase2_evidence_receipts.py
tests/test_phase2_vertical_slice.py
```

No other tracked remediation path is authorized. `.omo/` plan/evidence files are external process artifacts, never tracked remediation paths.

`END REMEDIATION_ALLOWLIST_V1`
