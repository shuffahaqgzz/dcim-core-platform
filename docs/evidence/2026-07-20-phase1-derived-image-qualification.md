# Phase 1 Derived Image Qualification — PASS, Governance Decisions Recorded

Verified UTC: 2026-07-20T14:45:18Z  
Implementation commit: `9d68483c32214397421900825140f8576c91f6c3`  
Security follow-up commit: `513b1ac845f81c46066fc4739f70b809adadd548`  
Issues: #10, parent #9; owner-approved exception: ADR-0013; source-to-binary
clarification: ADR-0014

Scope: synthetic `dcim-build` Development foundation only. This record does not
claim Staging or Production readiness.

## Decision and inputs

ADR-0013 authorized constrained local derived images for PostgreSQL, Apache
Kafka, Grafana OSS, and PostgreSQL exporter without changing accepted service
versions, interfaces, topology, or vulnerability policy. Public recipes and
immutable inputs are recorded in
[`deploy/compose/derived-images/recipes.json`](../../deploy/compose/derived-images/recipes.json).
Derived image publication is prohibited.

The issue #10 owner accepted exact component/category license findings for local
synthetic Development only. The reviewed records are in
[`deploy/compose/derived-images/license-dispositions.json`](../../deploy/compose/derived-images/license-dispositions.json).
Each reviewed record binds its exact count and a canonical identity fingerprint;
inventory replacement with the same aggregate count still fails closed.
Publication, distribution, handover, Staging, and Production remain outside this
disposition. OD-06 remains OPEN.

ADR-0014 accepts immutable official PostgreSQL and Kafka release binaries plus
checksum-verified source provenance for this scope. Grafana OSS and PostgreSQL
exporter remain full source builds. This clarification makes no claim that every
PostgreSQL or Kafka application binary was independently compiled here.

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
base/build images, both build IDs, vulnerability counts, recipe and license
disposition digests, and `publication: false`. Lock schema v2 makes the owner
disposition part of qualification and normalized Compose policy.

Package-level license reports and CycloneDX SBOMs were parsed fail-closed and
bound to evidence hashes. Restricted, reciprocal, and unknown category counts
and canonical identity fingerprints matched the issue #10 owner disposition
exactly across all six effective images. This does not close OD-06 or constitute
publication or distribution approval.
Raw scanner reports, SBOMs, build artifacts, image IDs, and runtime state remain beneath
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
python3 scripts/foundation_supply_chain.py --runtime-root ${DCIM_RUNTIME_ROOT} --derived-lock ${DCIM_RUNTIME_ROOT}/dev-build/derived-images-lock.json --license-dispositions deploy/compose/derived-images/license-dispositions.json
make preflight DCIM_RUNTIME_ROOT=${DCIM_RUNTIME_ROOT}
```

Clean second builds used BuildKit `--no-cache`; both OCI exports used timestamp
rewrite. The external lock binds both build IDs and public input provenance.
Fresh six-image supply-chain scan took approximately 130 seconds by command
wall clock. Final recovery test reported `88.5s`; earlier fast smoke reported
`94.4s`. Final preflight passed 75 unit/contract tests, public-safety, JSON,
fixture, Markdown, qualification, fresh supply-chain, policy, health, and
recovery gates.

Protected runtime material was absent at session start while older synthetic
PostgreSQL and Kafka volumes remained. Their old credentials and cluster identity
could not match newly bootstrapped material. With explicit owner approval, only
those two synthetic volumes were removed; Prometheus state was preserved. The
successful preflight recreated clean synthetic state and then passed recovery.

Synthetic provenance: repository fixtures and generated `dcim-build` runtime
material from `foundation-bootstrap`; image provenance comes from the immutable
public recipe manifest. No sanitized or connected-source artifact was used.

Owner status: ADR-0013 and ADR-0014 Accepted. Component/category license
dispositions are recorded and enforced fail-closed. Prior hard findings for
stale scan reuse, database identity, malformed license/SBOM output, policy
bypasses, evidence fields, health checks, and stale docs remain reconciled.
This is not `DEV-APPROVED`, Staging approval, Production authorization, or merge
approval.

## Disposition

Vulnerability and governance blockers recorded for issue #10 are resolved for
the local Phase 1 Development foundation. Gate policy was not weakened and
runtime architecture was not changed. Issue #10 is ready for review and owner
closure but remains open until that separate GitHub action. OD-06, official repin
cadence, source-signature coverage, issue/PR review, and all Production
conditions remain open or separately governed.

PostgreSQL and Kafka derivatives consume immutable official release image
digests while their public source archives are checksum-verified for provenance;
they do not independently reproduce every upstream application binary from
source. ADR-0014 accepts this bounded contract; replacement or stricter
source-to-binary verification remains a revalidation trigger.

Public-safety review found no credential, endpoint, host identity, raw payload,
log, dump, screenshot, or connected-source data in this evidence.
