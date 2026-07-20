# Phase 1 Derived Image Qualification — GO for Development

Date: 2026-07-20

Scope: synthetic `dcim-build` Development foundation only. This record does not
claim Staging or Production readiness.

## Decision and inputs

ADR-0013 authorized constrained local derived images for PostgreSQL, Apache
Kafka, Grafana OSS, and PostgreSQL exporter without changing accepted service
versions, interfaces, topology, or vulnerability policy. Public recipes and
immutable inputs are recorded in
[`deploy/compose/derived-images/recipes.json`](../../deploy/compose/derived-images/recipes.json).
Derived image publication is prohibited.

Prometheus and JMX exporter Java runtime remain their qualified official pinned
images. A clean official upstream image remains the preferred future
replacement for every derivative.

## Qualification result

One pinned Trivy scanner and recorded vulnerability/Java database snapshot
evaluated the effective six-image set. Every effective image is rescanned under
that frozen snapshot; derived reports are not reused for this final gate. Every
image passed unchanged policy:

- Critical findings: `0`;
- fixable High findings: `0`;
- unfixed High findings without approved disposition: `0`.

Each derived recipe built twice, including a clean second build. Image IDs and
required OCI labels matched. External lock provenance records public source,
base/build images, both build IDs, vulnerability counts, manifest digest, and
`publication: false`.

Package-level license reports and CycloneDX SBOMs were parsed fail-closed and
bound to evidence hashes. Restricted, reciprocal, and unknown categories retain
the accepted ADR-0013 local-only/no-publication disposition; this does not close
OD-06 or constitute distribution approval. Raw scanner reports, SBOMs, build
artifacts, image IDs, and runtime state remain beneath
`${DCIM_RUNTIME_ROOT}/dev-build`; none are committed.

## Runtime verification

Synthetic checks passed with the effective image lock:

- normalized Compose policy and public-boundary enforcement;
- PostgreSQL write/read round trip;
- Kafka KRaft produce/consume and JVM/JMX metrics;
- Prometheus targets, rules, and controlled alert;
- Grafana health and provisioning contract;
- PostgreSQL and Kafka restart/replay;
- PostgreSQL dump/restore checksum recovery.

## Disposition

Image blockers from the original official set are resolved for the local Phase
1 Development foundation. Gate policy was not weakened and architecture was not
changed. OD-06, official repin cadence, source-signature coverage, issue/PR
review, and all Production conditions remain open or separately governed.

Public-safety review found no credential, endpoint, host identity, raw payload,
log, dump, screenshot, or connected-source data in this evidence.
