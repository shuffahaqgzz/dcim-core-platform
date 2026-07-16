---
name: readonly-connector
description: Use when designing, implementing, or reviewing Redfish, SNMP, REST, syslog, or other source connectors for DCIM Development. Enforces read-only behavior, source protection, and negative tests.
---

# Read-only Connector Workflow

1. Confirm the connector is in the approved source catalog and that authorization/classification is recorded outside the public repository.
2. Define a strict read allowlist. Do not implement generic method dispatch or pass-through commands.
3. Require dedicated read-only credentials, TLS verification where applicable, timeouts, bounded retries with jitter, polling ceilings, concurrency limits, and a kill switch that defaults safe.
4. Normalize through the canonical event envelope; preserve source timestamp, observed timestamp, correlation, lineage, validation status, and explicit error disposition.
5. Add synthetic success, timeout, malformed payload, authentication failure, rate-limit, and duplicate tests.
6. Add negative tests proving write/control methods cannot be called. Include SNMP SET, Redfish write verbs/actions, configuration, reset, power, firmware, PTZ, and shell execution as prohibited classes.
7. Emit operational metrics without exposing endpoint or credential data.
8. Never run the connector against a live target from CI or an agent session.
