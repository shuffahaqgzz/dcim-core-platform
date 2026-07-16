---
name: schema-change
description: Use for JSON Schema, Avro mapping, event envelope, Asset identity, CI identity, alias, lineage, or persistence contract changes in DCIM Core Platform.
---

# Schema and Identity Change

1. Identify producer, consumer, storage, dashboard, replay, DLQ, and migration impact.
2. Use JSON Schema for external/API contracts. An internal Avro representation requires a documented versioned mapping.
3. Preserve required event fields: event ID, UTC event timestamp, observation timestamp, source, event type, priority, correlation ID, payload, and enrichment/lineage.
4. Keep stable identity rules:
   - Asset: native UUID, otherwise manufacturer plus serial number.
   - CI: source system plus native device ID/UUID.
   - hostname/FQDN/IP are time-bounded aliases; IP is never the primary key.
5. Define compatibility classification, validation behavior, defaulting, unknown-field policy, and DLQ/quarantine reason.
6. Add valid/invalid fixtures, collision tests, alias-history tests, and consumer contract tests.
7. Require a migration and rollback plan before changing persisted fields.
8. Record the change in an ADR or contract changelog when externally visible.
