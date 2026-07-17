# ADR-0001: Docker Compose Profiles for Development

- Status: Accepted
- Date: 2026-07-16
- Owner: shuffahaqgzz

## Context

The prototype/alpha milestone runs on one Ubuntu 24.04 VM with bounded resources. The immediate goal is compact deployability and integrated evidence, not Kubernetes parity or Production orchestration.

## Decision

Use Docker Compose with explicit profiles for Development. Separate DEV-BUILD, DEV-INTEGRATION-RO, and DEV-DEMO with distinct project names, networks, volumes, environment files, and credentials. Pin images and document resource limits, health checks, retention, and disk watermarks.

Kubernetes is deferred until Staging planning or until the owner creates a specific Development parity criterion.

## Consequences

- Faster bootstrap and simpler troubleshooting for a solo developer.
- Compose behavior and recovery must be reproducible and tested.
- Production scalability/HA cannot be inferred from this environment.
- A later Kubernetes design requires a separate ADR and migration/parity plan.
