# Phase 1 Derived Image Qualification — GO for Development

Verified UTC: 2026-07-20T11:51:49Z  
Implementation commit: `9d68483c32214397421900825140f8576c91f6c3`  
Issues: #10, parent #9; owner-approved exception: ADR-0013

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

## Reproducible commands and measurements

Commands used a protected external `${DCIM_RUNTIME_ROOT}` and synthetic
foundation data only:

```text
make foundation-images-qualify
python3 scripts/foundation_supply_chain.py --runtime-root ${DCIM_RUNTIME_ROOT} --derived-lock ${DCIM_RUNTIME_ROOT}/dev-build/derived-images-lock.json
make preflight DCIM_RUNTIME_ROOT=${DCIM_RUNTIME_ROOT}
```

Clean second builds used BuildKit `--no-cache`; both OCI exports used timestamp
rewrite. The external lock binds both build IDs and public input provenance.
Fresh six-image supply-chain scan took approximately 130 seconds by command
wall clock. Final recovery test reported `90.4s`; earlier fast smoke reported
`94.4s`. Final preflight passed 69 unit/contract tests, public-safety, JSON,
fixture, Markdown, qualification, fresh supply-chain, policy, health, and
recovery gates.

Synthetic provenance: repository fixtures and generated `dcim-build` runtime
material from `foundation-bootstrap`; image provenance comes from the immutable
public recipe manifest. No sanitized or connected-source artifact was used.

Owner status: ADR-0013 Accepted. Read-only Standards, Spec, and Security reviews
completed; hard findings for stale scan reuse, database identity, license/SBOM
validation, policy bypasses, evidence fields, health checks, and stale docs were
reconciled before this record. This is not `DEV-APPROVED` or merge approval.

## Disposition

Image blockers from the original official set are resolved for the local Phase
1 Development foundation. Gate policy was not weakened and architecture was not
changed. OD-06, official repin cadence, source-signature coverage, issue/PR
review, and all Production conditions remain open or separately governed.

PostgreSQL and Kafka derivatives consume immutable official release image
digests while their public source archives are checksum-verified for provenance;
they do not independently reproduce every upstream application binary from
source. Replacement or stricter source-to-binary verification remains a
revalidation trigger.

Public-safety review found no credential, endpoint, host identity, raw payload,
log, dump, screenshot, or connected-source data in this evidence.
