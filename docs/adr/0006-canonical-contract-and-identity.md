# ADR-0006: Canonical Event Contract and Stable Identity

- Status: Accepted
- Date: 2026-07-16
- Owner: shuffahaqgzz

## Context

Multiple sources represent the same equipment with inconsistent names and mutable addresses. Without a canonical envelope and stable identity, correlation, lineage, replay, and CMDB context become unreliable.

## Decision

Use JSON Schema for external/API event contracts. An internal Avro contract is permitted only with a versioned mapping. Events include unique ID, UTC event/observation timestamps, source, event type, priority, correlation ID, payload, enrichment, validation, and lineage.

Asset identity uses native UUID or manufacturer plus serial. CI identity uses source system plus native device ID/UUID. Hostname, FQDN, and IP are time-bounded aliases with source confidence and collision handling; IP is never a primary identity.

## Consequences

- Producers and consumers must pass contract and compatibility tests.
- Invalid events receive an explicit DLQ/quarantine reason and disposition.
- Alias history and identity collisions need dedicated tests and operator visibility.
- Persisted contract changes require migration and rollback planning.
