# ADR-0003: Single-Broker Kafka KRaft pada Development

- Status: Accepted
- Date: 2026-07-16
- Owner: shuffahaqgzz

## Context

Milestone memerlukan event backbone pada satu Development VM. High availability berada di luar objective saat ini.

## Decision

Gunakan satu Kafka broker dalam KRaft mode untuk Development. Konfigurasikan conservative retention, segment size, disk watermark alert, bounded message size, explicit topic setting, dan observable consumer lag. Persist data hanya untuk Development recovery/replay evidence.

## Consequences

- Footprint compact dan service lebih sedikit dibanding separate ZooKeeper deployment.
- Broker loss dapat mengganggu platform; risiko ini diterima untuk Development.
- Durability, HA, throughput, atau Production claim dilarang.
- Staging topology, replication, security, dan disaster recovery memerlukan design baru.

## Alternatives

Multi-broker Development dan ZooKeeper-based deployment ditolak karena resource/operational cost tanpa Phase 0 benefit. Tanpa event backbone tidak memenuhi later vertical-slice objective.

## Security Impact

Broker tetap isolated pada Development; tidak menerima Production data pada Phase 0. Access, retention, dan artifact provenance wajib dibatasi.

## Operational Impact

Single point of failure diterima hanya pada Development. Disk watermark, retention, lag, backup/replay assumption, dan resource headroom harus terukur sebelum Phase 1 claim.

## Revalidation Trigger

Staging design, HA/durability requirement, workload/headroom failure, atau Kafka major-version change.
