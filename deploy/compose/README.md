# Development Compose Profiles

The actual `compose.yaml` is intentionally deferred to the Day 2 issue so image versions/digests, licenses, health checks, resource limits, retention, and recovery behavior are reviewed together.

Required profile intent:

- `core`: API and minimal platform services;
- `data`: PostgreSQL, optional Redis, Kafka KRaft and ingestion dependencies;
- `observability`: Prometheus/Grafana and data-quality metrics;
- `dashboard`: NOC-oriented web/API presentation;
- `workflow`: dry-run workflow and SIEM/SOAR smoke adapters;
- `hermes`: read-only shadow, disabled by default and gated;
- `connectors-synthetic`: fixture/simulator connectors;
- `connectors-integration-ro`: separate pinned plane, never started by CI.

Requirements: explicit project names per logical plane, isolated networks/volumes, external runtime env files, fixed image versions then digest pinning, health checks, CPU/memory limits, disk watermarks, conservative retention, no host network, no privileged containers, no Docker socket mount, and no live source route in DEV-BUILD.
