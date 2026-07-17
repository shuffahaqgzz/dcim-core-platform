# ADR-0006: Canonical Event Contract dan Stable Identity

- Status: Accepted
- Date: 2026-07-16
- Owner: shuffahaqgzz

## Context

Banyak source merepresentasikan equipment yang sama dengan inconsistent name dan mutable address. Tanpa canonical envelope dan stable identity, correlation, lineage, replay, serta CMDB context menjadi tidak reliable.

## Decision

Gunakan JSON Schema untuk external/API event contract. Internal Avro contract hanya diizinkan dengan versioned mapping. Event mencakup unique ID, UTC event/observation timestamp, source, event type, priority, correlation ID, payload, enrichment, validation, dan lineage.

Asset identity memakai native UUID atau manufacturer plus serial. CI identity memakai source system plus native device ID/UUID. Hostname, FQDN, dan IP merupakan time-bounded alias dengan source confidence dan collision handling; IP tidak pernah menjadi primary identity.

## Consequences

- Producer dan consumer wajib lulus contract/compatibility tests.
- Invalid event menerima explicit DLQ/quarantine reason dan disposition.
- Alias history dan identity collision memerlukan dedicated tests serta operator visibility.
- Persisted contract change memerlukan migration dan rollback planning.

## Alternatives

Hostname/FQDN/IP sebagai primary identity ditolak karena mutable/collision-prone. Vendor-specific contract tanpa canonical mapping ditolak.

## Security Impact

Stable identity memperbaiki audit/correlation tetapi identifier asli tetap Restricted. Public fixture wajib synthetic dan alias history tidak boleh mengungkap topology.

## Operational Impact

Producer/consumer, Asset Repository, CMDB, dan API wajib konsisten pada identity/collision/lineage semantics serta versioned migration.

## Revalidation Trigger

Contract/schema/persistence change, new source identity model, collision evidence, atau migration incompatibility.
