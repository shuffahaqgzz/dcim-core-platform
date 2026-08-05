# Task 7 evidence — bounded streaming consumer

## Scope

`scripts/phase2/stream.py` introduces the bounded Kafka drain seam used by the
latency harness. It disables Kafka auto-commit, commits only after the existing
claim or quarantine disposition is durable, and treats the consumer as the sole
persistence owner for streamed normalized events. Stream runs deliberately skip
`reconcile_execution`: the stream manifest has no finite source list.

## Unit evidence

| Command | Result |
|---|---:|
| `.venv/bin/python -m unittest discover -s tests/phase2 -p 'test_stream_consumer*' -v` | 0 (7 tests) |
| `.venv/bin/python scripts/phase2/stream.py --help` | 0 |
| `python3 scripts/check-public-safety.py` | 0 |

Covered synthetic fake-consumer outcomes:

- validated input claims before offset commit;
- schema-invalid input quarantines, then DLQ publishes with copied
  `source_run_id`, before offset commit;
- a quarantine failure causes neither DLQ publish nor offset commit;
- a DLQ delivery failure causes no offset commit;
- bounded inclusive `--from-offsets` replay seeks its exact start and records
  valid replays as duplicate dispositions without new event rows;
- `--start-offsets` seeks the supplied starts and drains until idle;
- count-only mode filters foreign `source_run_id` records and performs no
  persistence.
- missing `source_run_id` quarantines with `missing_source_run_id` and never
  publishes to the DLQ.

## Limits

This is Development synthetic evidence only. It makes no Production, HA, SLA,
or broker-durability claim. Docker-dependent preflight is deferred to a Docker
host under the accepted baseline gate process.
