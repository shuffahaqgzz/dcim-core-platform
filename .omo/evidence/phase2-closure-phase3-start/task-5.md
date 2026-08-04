# Task 5 — Kafka topics and retention synchronization

Date: 2026-08-04  
Scope: synthetic Development foundation only; no Production-readiness claim.

## Happy path

| Command | Exit | Result |
|---|---:|---|
| `.venv/bin/python -m unittest discover -s tests/phase2 -p 'test_kafka_topics*.py' -v` | 0 | 10 Kafka topic tests passed. |
| `.venv/bin/python -m unittest tests.phase2.test_kafka_topics -v` | 0 | The same 10 tests passed through the module path. |
| `.venv/bin/python -m unittest tests.test_foundation_policy -v` | 0 | 26 policy tests passed, including the 30d-to-14d retention mutation. |
| `.venv/bin/python -m unittest tests.test_foundation_smoke -v` | 0 | 18 smoke contract tests passed, including allowed, unexpected, and missing-topic inventory cases. |
| `make phase0-check` | 0 | Compile, public-safety, JSON, synthetic-fixture, Markdown-link, and 267 unit tests passed. |
| `python3 scripts/phase2/kafka_topics.py` | 0 | Provisioned/synchronized the four Phase 2 topics. |
| `python3 scripts/phase2/kafka_topics.py --verify` | 0 | All four topic contracts verified. |
| `grep -qi "temporary format disposition" docs/architecture/kafka-topics-phase2.md` | 0 | Temporary JSON-format disposition is documented. |
| `timeout 90 make foundation-policy` | 124 | Deferred: the prerequisite foundation image qualification was still running when the bounded command timed out. |

The topic contract verified by the tests and live broker is: four topics, one
partition, replication factor one, `retention.ms=2592000000`, and
`max.message.bytes=1048576`. Provisioning uses Kafka's `--create
--if-not-exists` through `docker compose exec -T kafka`. Broker automatic topic
creation remains disabled.

## Failure mutation and restore

The requested direct Compose mutation command could not interpolate the Compose
model without the generated image environment. The equivalent mutation was
therefore applied to the already-running synthetic Development Kafka container:

| Command | Exit | Result |
|---|---:|---|
| `docker exec dcim-build-kafka-1 /opt/kafka/bin/kafka-configs.sh --bootstrap-server localhost:9092 --alter --entity-type topics --entity-name dcim.normalized.events --add-config retention.ms=1000` | 0 | Broker reported the topic configuration update completed. |
| `python3 scripts/phase2/kafka_topics.py --verify` | 1 | Failed closed and reported `retention.ms='1000', expected 2592000000`. |
| `python3 scripts/phase2/kafka_topics.py` | 0 | Restored the declared topic configuration. |
| `python3 scripts/phase2/kafka_topics.py --verify` | 0 | Restored topic contract verified green. |

## Restore steps

Run `python3 scripts/phase2/kafka_topics.py`, then
`python3 scripts/phase2/kafka_topics.py --verify`. Both restore commands were
run above and exited zero.

## Limitations

- This evidence covers the synthetic single-broker Development profile only;
  it provides no HA, SLA, durability, Staging, or Production claim.
- C-07 remains OPEN pending its complete caps, alerts, and load/smoke usage
  evidence and owner disposition.
