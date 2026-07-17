# ADR-0002: Public Code, Private Runtime

- Status: Accepted
- Date: 2026-07-16
- Owner: shuffahaqgzz

## Context

The repository is public while DCIM sources and operational context can expose credentials, identities, topology, security posture, and sensitive telemetry.

## Decision

Keep generic code, schemas, synthetic fixtures, templates, and sanitized evidence in Git. Keep live endpoints, identities, topology, credentials, raw payloads/logs/captures/dumps, certificates, screenshots, operational prompts, source authorizations, and runtime state outside Git and outside public automation.

CI uses synthetic data and GitHub-hosted runners only. Runtime environment files and volumes are created outside the repository.

## Consequences

- Public-safety scanning and manual review are mandatory.
- Live defects must be reproduced with synthetic/sanitized cases before public discussion.
- Connected integration and its evidence need a private governed store.
- Accidental publication is an incident requiring credential rotation and history cleanup.
