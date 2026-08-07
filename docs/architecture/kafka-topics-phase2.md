# Phase 2 Development Kafka topics

This contract provisions exactly four topics on the single-broker KRaft
Development foundation. It makes no high-availability, durability, Staging, or
Production claim. Topic auto-creation remains disabled; operators run
`python3 scripts/phase2/kafka_topics.py` explicitly and use `--verify` for a
read-only contract check.

## Provisioned topology and retention

All topics have one partition, replication factor one, 720 hours (30 days) of
retention, and a 1 MiB message ceiling. The topic retention equals
`2592000000` ms and the message ceiling equals `1048576` bytes.

| Topic | Partitions | Replication factor | `retention.ms` | `max.message.bytes` |
|---|---:|---:|---:|---:|
| `dcim.raw.synthetic` | 1 | 1 | 2592000000 | 1048576 |
| `dcim.normalized.events` | 1 | 1 | 2592000000 | 1048576 |
| `dcim.enriched.events` | 1 | 1 | 2592000000 | 1048576 |
| `dcim.dlq.synthetic` | 1 | 1 | 2592000000 | 1048576 |

Prometheus local retention is also 30 days, as required by
[ADR-0021](../adr/0021-foundation-resource-limits-retention.md). Disk-watermark
alerts and the resource caps remain the operational guardrails for this
Development-only retention window.

## Contract semantics

### Schema and version

`dcim.raw.synthetic` carries repository-authored synthetic source JSON.
`dcim.normalized.events` and `dcim.enriched.events` carry the external/API
event-envelope v0.1.0 JSON contract. Normalized records have passed schema
validation; enriched records retain that envelope version and add Asset/CI
context through its defined enrichment fields. `dcim.dlq.synthetic` may carry
the rejected raw bytes, so consumers must use its reason and disposition
metadata rather than treating the payload as a valid envelope. Unknown schema
versions fail validation and follow the explicit quarantine/DLQ path.

### Idempotency and deduplication

The deduplication key is `event_id`; the persistent claim store is the
authority for first-wins atomic claims across the store lifetime. Replay of the
same canonical content is classified `duplicate`. Reuse of an `event_id` for
different content is quarantined as `event_id_content_conflict`. Kafka offsets
are transport positions, not identity or deduplication keys.

### Timestamp semantics

`occurred_at` is the source event time and `observed_at` is the UTC time the
Development ingestion boundary observed it. Producers preserve both values;
consumers do not replace either with broker append time. Synthetic evidence
records clock source and test-window assumptions where latency is measured.

### Lineage and validation

Every valid normalized/enriched envelope retains source and input lineage plus
the required validation status (`accepted`, `duplicate`, or `quarantined`). A
consumer validates before claiming an `event_id`. Every received input must
reach a durable disposition so the zero-silent-loss ledger can reconcile it.

### Retry, DLQ, and replay

Transport retries never bypass validation or the claim store. Valid replay is
safe through `event_id` claim classification. Invalid input goes to the
synthetic DLQ with an explicit reason, disposition, lineage, and immutable run
correlation; it is not silently dropped or published as a normalized event.
Reprocessing a DLQ record follows the same validate-then-claim order.

### Identity and aliases

Asset identity uses native UUID, falling back to normalized manufacturer plus
serial. CI identity uses source system plus native device ID/UUID. Hostname,
FQDN, and IP remain time-bounded aliases with collision handling; IP is never a
primary identity. Topic choice does not change these ADR-0006/ADR-0028 rules.

### Migration and rollback

A persisted schema change requires producer/consumer compatibility tests and a
documented mapping before rollout. Deploy consumers that can read both forms
before producers emit a new form. Rollback first stops new-form publication,
then restores compatible consumers without deleting accepted events,
dispositions, or lineage. Topic config rollback is a reviewed Compose/policy
change followed by provisioning and `--verify`; reducing retention may destroy
replay evidence and therefore requires owner approval.

## Temporary format disposition

Phase 2/3 Development carries event-envelope v0.1.0 as JSON on
`dcim.normalized.events` and `dcim.enriched.events`. This is a deliberate temporary Development deviation from the research Avro target in
[the research architecture](../research/ARCHITECTURE.md#14-target-event-topics),
which is guidance rather than an accepted ADR. A future Avro migration requires
an accepted schema-registry decision, a versioned JSON-to-Avro mapping, and
producer/consumer compatibility tests under `contracts/README.md`. This is a
later-phase decision. No Avro conformance claim is made by the current
implementation.
