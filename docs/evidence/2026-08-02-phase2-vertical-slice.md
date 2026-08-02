# Phase 2 P1/P2 Vertical Slice — Development Evidence

UTC: `2026-08-02T19:00:34Z` (execution record; package name follows the approved plan)
Commit/tag: base `12209562339f43b8c32c7d936686d03c4b8398ea`; delivery branch `feat/phase2-vertical-slice`; final delivery subject `docs(phase2): vertical slice evidence, ac matrix, condition impact`
Issue/PR: issue [#21](https://github.com/shuffahaqgzz/dcim-core-platform/issues/21); one-todo PR assembly remains an owner workflow and no PR was opened in this session
Scope: synthetic Redfish P1 and SNMPv3 P2 fixture replay through validation, disposition, deterministic identity, PostgreSQL persistence, and a PostgreSQL-authoritative static NOC read model, plus the Phase 2 gate and retained Stage 1/2 safety boundary
Acceptance criterion: issue #21 AC-1 through AC-8, restated from the approved Phase 2 plan and its issue references below
Synthetic fixture/provenance: `fixtures/synthetic/` only; six public synthetic event fixtures and the mandatory invalid fixture; no connected source, live endpoint, credential, raw payload, dump, or operational identity was used
Owner/reviewer status: Development evidence package and closure requests are ready for owner review. The issue and all conditions named below remain open; no owner disposition is claimed.

## AC matrix

The result column records a concise verbatim output excerpt. Excerpts are kept
small and public-safe; raw logs and runtime artifacts remain outside Git.

| Issue #21 AC | Criterion covered | Exact command | Verbatim output excerpt | Result / measurement |
|---|---|---|---|---|
| AC-1 | P1 Redfish and P2 SNMPv3 synthetic signals complete the fixture → validation → disposition → identity → PostgreSQL → NOC path. | `make phase2-check` | `pipeline-run: PASS`<br>`noc-verify: PASS` | PASS; the orchestrator used one commit-derived run ID and the six synthetic event corpus. Duration measured by the command session; final unit-discovery duration was `117.445s`. |
| AC-2 | Every received input has an explicit accepted, quarantined, or duplicate disposition; no silent loss. | `python3 -m unittest tests.phase2.test_phase2_validate.Phase2DispositionEngineTests.test_six_fixtures_then_replay_balances_ledger -v` | `test_six_fixtures_then_replay_balances_ledger ... ok`<br>`OK` | PASS; replay ledger balance and duplicate classification asserted by the test. Duration measured by unittest. |
| AC-3 | Invalid input is durably quarantined with a stable reason; duplicate/conflict paths do not mutate the stored event. | `python3 -m unittest tests.phase2.test_phase2_persist.PostgresPipelineTests.test_invalid_first_is_durable_after_manifest_commit tests.phase2.test_phase2_persist.PostgresPipelineTests.test_content_conflict_quarantines_without_mutating_event -v` | `test_invalid_first_is_durable_after_manifest_commit ... ok`<br>`test_content_conflict_quarantines_without_mutating_event ... ok`<br>`OK` | PASS; PostgreSQL integration tests assert durable quarantine, `event_id_content_conflict`, and unchanged first content. Duration measured by unittest. |
| AC-4 | A run manifest is immutable; identical replay is idempotent and manifest drift fails closed. | `python3 -m unittest tests.phase2.test_phase2_persist.PostgresPipelineTests.test_full_replay_is_duplicate_and_authoritative_rows_are_stable tests.phase2.test_phase2_persist_adversarial.AdversarialPersistenceTests.test_same_manifest_conflict_mutates_only_dispositions -v` | `test_full_replay_is_duplicate_and_authoritative_rows_are_stable ... ok`<br>`test_same_manifest_conflict_mutates_only_dispositions ... ok`<br>`OK` | PASS; authoritative rows remain stable while duplicate/conflict dispositions are added. Duration measured by unittest. |
| AC-5 | Persisted PostgreSQL NOC rows are authoritative and regeneration is deterministic. | `python3 scripts/phase2/noc.py --run-id phase2-check-12209562339f` (twice) | `noc-verify: PASS` | PASS; two generations were byte-identical, file tampering is overwritten from PostgreSQL, and stale persisted cards are removed. Runtime output stays under the protected runtime root. |
| AC-6 | Phase 2 schema is applied idempotently through Python migrations and supports rollback/re-apply plus recovery/capacity checks. | `python3 scripts/phase2/migrate.py --verify` | `schema_migrations`<br>`run_manifests`<br>`events`<br>`dispositions`<br>`assets`<br>`cis`<br>`aliases`<br>`noc_cards` | PASS; exact eight-table inventory verified; the same run also passed rollback/re-apply, PostgreSQL restore, and the 90% admission threshold check. Duration measured by the command/gate session. |
| AC-7 | Connector and workflow paths remain read-only: fixture adapters have kill switches and Stage 1/2 remains dry-run/advisory-only. | `python3 -m unittest tests.phase2.test_stage12_retention tests.phase2.test_redfish_adapter_readonly tests.phase2.test_snmpv3_adapter_readonly -v` | `test_workflow_stage_one_and_two_safety_text_remains_exact ... ok`<br>`OK` | PASS; AST/behavioral tests retain the no-network/no-write boundary and the stop/kill controls. Duration measured by unittest. |
| AC-8 | The complete Development verification surface is green and evidence is public-safe. | `make phase0-check`<br>`make phase2-check`<br>`make preflight` | `Ran 263 tests in 16.968s`<br>`Ran 139 tests in 117.445s`<br>`foundation-recovery: PASS (48.3s)`<br>`"overall_result": "pass"`<br>`exit 0` | PASS on the final local execution sequence; remote CI, PR review, issue disposition, and owner approval are not claimed. Durations are the final unittest/recovery measurements from the command sessions. |

## Receipt and authority binding

The plan was hashed live immediately before receipt generation. The receipt CLI
help exposes no `--requirement-id` option, so its default requirement ID is
recorded rather than supplied by the caller.

```text
plan_sha256=90379ea4330179bbf342642c65b6ab2bd9b05f3dfb72f5856fdf7fc7e4f2dc3a
receipt_path=.omo/evidence/phase2-p1-p2-vertical-slice/todo13-authority-bootstrap-receipt.json
computed_disposition=LOCAL_PASS
process_outcome=exited
exit_code=0
requirement_id=AUTHORITY_BOOTSTRAP
pass_marker_count=4
no_go_marker_count=0
```

The receipt is local execution evidence only and is intentionally not part of
the PR. Its subject commit is the todo-12 base
`12209562339f43b8c32c7d936686d03c4b8398ea`; the final todo-13 commit is the
single documentation commit named above.

## Public-safe NOC sample

Selected fields from the todo-11 synthetic output are reproduced below. This
is a documentation sample, not a committed runtime artifact.

```json
{
  "generated_at": "2026-07-30T00:00:00+00:00",
  "kind": "event",
  "run_id": "phase2-check-12209562339f",
  "subject_key": "11111111-1111-4111-8111-111111111111",
  "payload": {
    "asset": {
      "asset_type": "synthetic-device",
      "identity": {
        "manufacturer": "ExampleVendor",
        "serial_number": "SYNTHETIC-0001"
      }
    },
    "ci": {
      "ci_type": "synthetic-ci",
      "identity": "synthetic-lab:device-001"
    },
    "dispositions": {
      "accepted": 1,
      "duplicate": 1,
      "quarantined": 0
    },
    "envelope": {
      "event_type": "server.health.degraded",
      "priority": "P1",
      "source": {
        "connector": "redfish-fixture-adapter",
        "system": "redfish-synthetic",
        "transport": "redfish"
      }
    }
  }
}
```

## Condition impact and closure requests

No condition is closed by this evidence package. Closure requests are recorded
for owner review according to the conditions register:

- C-06 remains `OPEN`. Request owner review of the five deterministic
  ADR-0020 collision tests in todo 7: duplicate serial across sources,
  hostname reuse after validity expiry, IP movement, confidence-tie
  quarantine, and merge lineage. The register remains authoritative.
- C-07 remains `OPEN`. The Phase 2 cap declaration is recorded in
  [`phase2-resource-caps.md`](../architecture/phase2-resource-caps.md), and
  the capacity gate passed. This slice activates no long-running service and
  does not provide the register's complete service-cap/load evidence.
- C-09 remains `OPEN`. The fixture adapters exercise configuration and stop
  kill-switch tiers, while the connector ceiling negative tests required by
  the register remain open. No connected Runtime Plane is authorized.

The corresponding register note is in
[`CONDITIONS-REGISTER.md`](../governance/CONDITIONS-REGISTER.md). Only the
owner or named authority may change any status to `CLOSED`.

## Governing decisions

This slice follows [ADR-0004](../adr/0004-read-only-integration-plane.md),
[ADR-0005](../adr/0005-dry-run-automation.md),
[ADR-0006](../adr/0006-canonical-contract-and-identity.md),
[ADR-0007](../adr/0007-cmdb-implementation-for-development.md),
[ADR-0008](../adr/0008-synthetic-and-sanitized-demo-data.md),
[ADR-0020](../adr/0020-identity-alias-conflict-resolution.md),
[ADR-0021](../adr/0021-foundation-resource-limits-retention.md),
[ADR-0023](../adr/0023-connector-polling-source-impact-controls.md),
[ADR-0024](../adr/0024-python-fastapi-service-language-baseline.md),
[ADR-0026](../adr/0026-program-technology-version-baseline.md), and
[ADR-0028](../adr/0028-duplicate-disposition-and-deterministic-identity.md).

The owner decision recorded for 2026-07-29 scopes this slice to issue #21's
P1+P2 path and supersedes the earlier PRD Q10 P1-only freeze. This is a scope
decision for the synthetic Development slice, not an authorization for live
integration.

## Limitations and non-claims

- This is a one-shot batch pipeline. Kafka bus integration is omitted relative
  to [`DEV-BOOTSTRAP-V0.1.md`](../plan/DEV-BOOTSTRAP-V0.1.md) and deferred to a
  separately governed slice.
- Event-to-dashboard p95 latency was not measured. The batch design has no
  supported p95 latency claim.
- TimescaleDB, Avro, a React dashboard, and a long-running Phase 2 service are
  not part of this slice.
- No live device connection or infrastructure write/control method was
  invoked; fixture replay is the only source path.
- No Production, HA, SLA, Staging, or `DEV-APPROVED` claim is made. Remote CI,
  PR review, issue closure, and condition closure remain pending owner action.

## Gate record

`make markdown-links` and `make public-safety` passed during the final local
sequence. `make phase0-check`, `make phase2-check`, and `make preflight` all
returned exit 0 on the final local sequence. Durations were measured with
wall-clock command timing; the final preflight also recorded `foundation-recovery:
PASS (48.3s)` and strict evidence summary `"overall_result": "pass"`. A first
final-head Phase 2 invocation was blocked by stale protected synthetic state;
after the existing Phase 2 acceptance cleanup and reversible archive of stale
runtime receipts, the exact command passed. Only decisive public-safe output
excerpts are retained here and the full raw logs were not stored.

Related stale-status updates are recorded in
[`GAP-ANALYSIS.md`](../research/GAP-ANALYSIS.md),
[`STATUS-SUMMARY.md`](../research/STATUS-SUMMARY.md), and the repository
[`README.md`](../../README.md).
