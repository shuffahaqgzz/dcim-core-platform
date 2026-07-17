# ADR-0003: Single-Broker Kafka KRaft in Development

- Status: Accepted
- Date: 2026-07-16
- Owner: shuffahaqgzz

## Context

The milestone needs an event backbone on a single Development VM. High availability is outside the current objective.

## Decision

Use one Kafka broker in KRaft mode for Development. Configure conservative retention, segment size, disk watermark alerts, bounded message sizes, explicit topic settings, and observable consumer lag. Persist data only for Development recovery/replay evidence.

## Consequences

- Compact footprint and fewer services than a separate ZooKeeper deployment.
- Broker loss can interrupt the platform; this is accepted for Development.
- No durability, HA, throughput, or Production claim may be made.
- Staging topology, replication, security, and disaster recovery require a new design.
