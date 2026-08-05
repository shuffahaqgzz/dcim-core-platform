# Task 6 evidence — stream-mode producer (validate + publish only)

Scope: `scripts/phase2/kafka_producer.py` (new), `KafkaPublishError` in
`scripts/phase2/errors.py`, additive `--mode batch|stream` in
`scripts/phase2/run.py`, tests in `tests/phase2/test_stream_producer.py`.
Batch mode remains byte/behavior-identical; stream mode builds the manifest in
memory only, writes nothing to the database, publishes valid envelopes to
`dcim.normalized.events` and failures to `dcim.dlq.synthetic` with
`source_run_id` + `reason` headers; `confluent_kafka` is imported lazily by the
stream branch only.

## Commands and exit codes

| Command | Exit |
|---|---|
| `.venv/bin/python -m unittest discover -s tests/phase2 -p 'test_stream_producer*' -v` | 0 (13 tests, OK) |
| `make phase2-test` | 0 (182 tests, OK) |
| `.venv/bin/python -m compileall -q scripts/phase2/run.py scripts/phase2/kafka_producer.py scripts/phase2/errors.py` | 0 |
| Docker batch-freeze proof (below) | 0, zero diff |

## Happy path

Unit: 3 valid repo fixtures (`p1-redfish-health.json`, `p1-ups-alarm.json`,
`p2-network-utilization.json`) + 2 invalid fixtures (JSON syntax error,
schema-invalid envelope) in a temporary directory, producer mocked:

- summary stdout parsed to exactly `{"received":5,"published":3,"dlq":2}`;
- 3 publishes to `dcim.normalized.events`, key = `event_id`, headers exactly
  `{schema_version: "0.1.0", source_run_id: <run_id>, input_ordinal: "2"|"3"|"4"}`;
- 2 publishes to `dcim.dlq.synthetic`, key `None`, raw input bytes as value,
  headers `reason=schema_invalid`, non-empty `detail`, `source_fixture`,
  `source_run_id=<run_id>`;
- payload-type violation publishes DLQ header `reason=payload_invalid`
  (batch quarantine vocabulary);
- `begin_execution`, `PostgresClaimStore`, `persist_quarantine`,
  `reconcile_execution`, and `db.psql` never invoked in stream mode
  (trip-wire mocks).

## Failure-mutation results and restore steps

1. Delivery callback with `msg.error()` set (and with the first-argument
   error set) → `KafkaPublishError` raised; no restore needed (in-memory
   fake driver, no external state).
2. Full local queue (`BufferError` on produce) and flush leaving pending
   messages → `KafkaPublishError`; no external state mutated.
3. `run.py` invoked without `--mode` in a subprocess with a meta-path import
   blocker → parser default is `batch`, `confluent_kafka` absent from
   `sys.modules` (exit 0). No restore needed.
4. Batch byte-freeze mutation guard: hardcoded baseline stdout captured from
   the pre-stream pipeline; any semantic drift fails
   `test_batch_stdout_is_byte_identical_to_baseline`. Restore step for a
   deliberate mutation: `git checkout -- scripts/phase2/run.py` (not needed;
   no mutation was left in place).

## Docker-host batch-freeze proof (zero diff vs main)

Foundation stack was already up (`dcim-build-*` healthy). Steps run verbatim:

```text
$ git worktree add /tmp/dcim-main-freeze main                 # baseline checkout
$ export DCIM_RUNTIME_ROOT="$HOME/.local/state/dcim-core-platform/runtime"
$ .venv/bin/python -c "import sys; sys.path.insert(0,'.'); from scripts.phase2 import check; check.clean_acceptance_state()"
$ .venv/bin/python /tmp/dcim-main-freeze/scripts/phase2/run.py --run-id batch-freeze-proof \
    --fixtures-dir /tmp/dcim-main-freeze/fixtures/synthetic/events \
    --fixed-clock 2026-07-30T00:00:00Z > /tmp/batch-main.out
  MAIN-EXIT=0
$ .venv/bin/python -c "... check.clean_acceptance_state()"    # reset DB state
$ .venv/bin/python scripts/phase2/run.py --run-id batch-freeze-proof \
    --fixtures-dir fixtures/synthetic/events \
    --fixed-clock 2026-07-30T00:00:00Z > /tmp/batch-branch.out
  BRANCH-EXIT=0
$ diff /tmp/batch-main.out /tmp/batch-branch.out
  ZERO-DIFF-OK   (identical summary line incl. manifest_sha256
                  9be828cdaaa2c297c2d71bddb623124403331acae8da4518b8a6091cf3bbbdfe)
```

Restore/cleanup: `check.clean_acceptance_state()` re-run (acceptance tables
truncated, DB left as found) and `git worktree remove /tmp/dcim-main-freeze
--force` (worktree list verified).

## Non-claims

No Staging/Production/HA/SLA claim. Stream mode performs no persistence; the
bounded consumer (todo 7) is the sole persistence owner for streamed events.
