# Architecture Documentation

Keep public-safe context, logical component diagrams, trust boundaries, data flow, failure handling, and accepted decisions here.

A diagram must not expose real topology, subnets, endpoints, site/rack/camera identifiers, credentials, or source-system inventory. Use generic logical names and reserved domains.

The initial logical flow is:

```text
Synthetic / Authorized Read-only Sources
  -> Connector Boundary
  -> Normalize + Validate
  -> DLQ/Quarantine or Enrich
  -> Asset/CMDB Context
  -> PostgreSQL / Kafka Development Core
  -> Analytics / Workflow Draft / SIEM Smoke
  -> API + NOC Dashboard
  -> Hermes Read-only Shadow (after gate)
```
