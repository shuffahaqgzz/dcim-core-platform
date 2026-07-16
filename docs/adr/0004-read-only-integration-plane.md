# ADR-0004: Pinned Read-only Integration Plane

- Status: Accepted
- Date: 2026-07-16
- Owner: shuffahaqgzz

## Context

Some Development validation may eventually require office/Production telemetry. Mutable Development code or broad credentials would create unacceptable source and data risk.

## Decision

Any connected integration is a separately promoted DEV-INTEGRATION-RO plane using pinned artifacts, dedicated read-only identities, restricted routes and egress, private runtime storage, polling ceilings, source-impact metrics, audit metadata, and an immediate kill switch. CI and agent sessions do not connect to live sources.

Each connector exposes only allowlisted read methods and includes negative tests proving prohibited operations are unavailable.

## Consequences

- Source authorization and environment separation are prerequisites, not later hardening.
- Integration feedback is slower because promotion is explicit.
- Private operational runbooks/evidence are required outside this repo.
- A write-capable path is a separate governed exception and is not part of this milestone.
