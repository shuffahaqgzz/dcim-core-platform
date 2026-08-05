# Task 14 — Core Capability Profile Compose Integration

## Scope

Added the DEV-BUILD `core` capability-profile definitions for the Asset
Repository and CMDB. Each service uses the qualified local services image,
service-scoped PostgreSQL role secret, shared internal API token, read-only
source mounts, no host-published ports, and the accepted Development resource
cap. Prometheus now has in-plane `/metrics` scrape jobs. The Phase 3 smoke
skeleton defines `/health` and `/ready` checks for both service names.

## Verification

- `make foundation-policy`: PASS.
- `make phase0-check`: PASS.
- `make phase3-test`: PASS.
- Docker Compose runtime QA: not run in this sandbox. This evidence therefore
  makes structural-only assertions and does not claim that containers started
  or that HTTP endpoints responded at runtime.

## Boundary and limitations

The configuration is synthetic DEV-BUILD-only and adds no published host port,
source connection, credential value, runtime state, HA, SLA, Staging, or
Production claim. C-07 remains OPEN pending the required measured full-profile
usage evidence and owner disposition.
