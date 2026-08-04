# Task 8 — deterministic p95 event-to-dashboard latency harness

Date: 2026-08-04  
Scope: synthetic Development measurement only; this evidence makes no Production latency guarantee.

## Acceptance review

| Check | Result |
|---|---|
| Seeded workload | PASS — `random.Random(seed)` and `uuid.UUID(int=rng.getrandbits(128))`; 50 generated IDs are unique and seed 42 replays identically. |
| Required legs | PASS — CLI requires `--leg {direct,kafka}`. |
| Kafka watermark order | PASS — captures the `dcim.normalized.events` end offsets, writes `start-offsets.json`, and only then publishes. The same path is passed as `start_offsets` to the consumer with `max_messages=count` and a 30-second idle timeout. |
| Timing points | PASS — injection uses `time.time_ns`; persistence is observed by a 50 ms poll; dashboard visibility is stamped after synchronous `noc.materialize`. |
| Public report | PASS — reports interval values only and nearest-rank p50/p95/max for persistence and dashboard latency, with workload class `event/trap (P1)`. |
| Threshold | PASS — `--assert` requires dashboard p95 to be strictly below 5000 ms. |
| Isolation | PASS — run IDs use `latency-<seed>-<timestamp-ns>` and `finally` issues four run-scoped deletes in FK-safe order. |
| Deferred integration | PASS — unavailable producer/consumer modules fail through `KafkaIntegrationError`; Todos 6 and 7 remain out of scope. |

## Happy-path verification

| Command | Exit | Result |
|---|---:|---|
| `.venv/bin/python -m unittest discover -s tests/phase2 -p 'test_latency*.py' -v` | 0 | 11 tests passed, including deterministic generation, Kafka watermark handoff, interval-only reporting, threshold behavior, and cleanup. |
| `.venv/bin/python scripts/phase2/latency.py --help` | 0 | Shows required `--leg {direct,kafka}` and options `--count`, `--seed`, `--assert`, and `--output`. |
| `make phase0-check` | 0 | 267 repository tests passed; compile, public-safety, JSON, synthetic-fixture, and Markdown-link gates passed. |

The fixed-seed replay is covered by
`WorkloadTests.test_generate_is_counted_unique_and_seed_deterministic`: two
seed-42 runs produce identical event ID lists, while seed 43 differs.

## Failure mutation

| Mutation | Expected | Observed |
|---|---|---|
| Canned 50-sample set with five (10%) dashboard samples at 6000 ms | Nearest-rank p95 is 6000 ms and assertion fails. | PASS — `test_nearest_rank_p95_rejects_ten_percent_slow_dashboard_samples` raises `LatencyThresholdError`. |
| Success, threshold failure, and injected runtime failure | Cleanup always issues exactly four run-scoped deletes. | PASS — cleanup tests observe `dispositions`, `noc_cards`, `events`, then `run_manifests`. |

## Restore

The mutations are in-memory unit fixtures and mocks; no source file or database
mutation requires restoration. The harness cleanup path is exercised for the
success and failure cases. No test database rows were created by this evidence
run.

## Limitations

- This is a deterministic synthetic Development harness, not a Production benchmark or guarantee.
- The Kafka producer and bounded consumer are intentionally deferred integration seams supplied by later plan tasks.
- Condition register statuses are unchanged.
