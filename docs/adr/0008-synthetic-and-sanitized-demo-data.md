# ADR-0008: Synthetic and Sanitized Demo Data

- Status: Accepted
- Date: 2026-07-17
- Owner: shuffahaqgzz

## Context

Demo publik dapat mengungkap identity, topology, timestamp pattern, free text, atau security posture walau direct identifier dihapus.

## Decision

Gunakan synthetic data sebagai default. Sanitized snapshot hanya future exception dengan private provenance/approval, deterministic pseudonymization, documentation IP/domain, generic location, controlled timestamp offset, regenerated message, dan public-safety review. `dcim-demo` tidak memiliki Production route/credential.

## Alternatives

Live Production demo dan ad-hoc masking ditolak. Aggregation saja tidak cukup untuk small population.

## Consequences

Demo reproducible dan public-safe, tetapi realism serta temporal fidelity terbatas. Sanitized release memerlukan approval dan residual de-anonymization review.

## Security Impact

Mengurangi disclosure langsung; correlation/linkability tetap residual risk yang harus ditinjau per dataset/salt/audience.

## Operational Impact

Sanitizer, fixture provenance, tests, evidence checklist, retention, dan deletion menjadi release gate.

## Revalidation Trigger

Dataset/salt/transformation/audience berubah atau re-identification concern ditemukan.
