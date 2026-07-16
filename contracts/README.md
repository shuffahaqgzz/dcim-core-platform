# Contracts

External/API contracts are defined with JSON Schema under `schemas/`. Internal Kafka Avro contracts may be introduced only with an accepted mapping/versioning decision and compatibility tests.

Every producer and consumer must document:

- schema/version and compatibility behavior;
- idempotency/deduplication key;
- timestamp semantics and clock assumptions;
- lineage and validation status;
- retry, DLQ/quarantine and replay disposition;
- identity/alias behavior;
- migration/rollback impact.
