# ADR-0014: Official Release Binary and Source Provenance Contract

- Status: Accepted
- Date: 2026-07-20
- Owner: shuffahaqgzz
- Decision source: explicit owner decision in the issue #10 governance-hold task
- Issues: #10, parent #9
- Clarifies: [ADR-0013](0013-derived-hardened-foundation-images.md)

## Context

ADR-0013 permits Development-only derived hardened images and says each
derivative starts from an exact upstream release tag and immutable source
commit. Its introductory wording could also be read as requiring every upstream
application binary to be compiled independently from source.

The qualified PostgreSQL and Apache Kafka recipes instead consume immutable
official release image digests as application-binary inputs. Their matching
public release source archives, tags, commits, and SHA-256 checksums are verified
provenance inputs. The recipes then apply only the narrow security remediation
allowed by ADR-0013. Grafana OSS and PostgreSQL exporter remain full source
builds.

Issue #10 cannot close while this source-to-binary interpretation is implicit.

## Decision drivers

- Preserve qualified official application binaries and existing runtime
  behavior.
- Keep every binary and source-provenance input immutable and reviewable.
- Avoid claiming source-build reproducibility where the recipe does not compile
  the upstream application.
- Preserve ADR-0013 vulnerability, patch-boundary, non-publication, and
  Development-only constraints.
- Avoid a costly rebuild path without evidence that it improves issue #10 risk.

## Decision

For PostgreSQL and Apache Kafka only, an immutable official release image digest
plus checksum-verified source provenance satisfies ADR-0013's source-to-binary
contract for the local synthetic `dcim-build` scope.

The required contract is:

1. exact official release image tag and linux/amd64 manifest digest;
2. matching public release tag and immutable source commit;
3. checksum-verified source archive recorded as provenance input;
4. immutable, checksum-verified remediation inputs;
5. no unsupported claim that the upstream PostgreSQL or Kafka application
   binary was independently compiled by this repository;
6. unchanged reproducibility, OCI label, SBOM, license, vulnerability, policy,
   smoke, recovery, and non-publication gates from ADR-0013.

Grafana OSS and PostgreSQL exporter continue to use full source builds. This ADR
does not authorize converting them to official-binary assembly. Any additional
component or different assembly mode requires a new owner decision.

## Options considered

### 1. Accept immutable official binaries with verified source provenance

Selected. Matches qualified recipes and preserves upstream release artifacts
while keeping source attribution independently verifiable.

### 2. Require full application source builds for PostgreSQL and Kafka

Not selected. It would add compiler, build-system, packaging, runtime-parity,
and maintenance risk and would require a new qualification cycle. Reconsider if
provenance assurance, redistribution, or deployment scope changes.

### 3. Leave ADR-0013 interpretation implicit

Rejected. It permits evidence to overstate how PostgreSQL and Kafka binaries
were produced.

## Consequences

- Issue #10 evidence can describe PostgreSQL and Kafka accurately as
  official-binary derivatives with verified source provenance.
- Reviewers must distinguish source provenance from full source compilation.
- Official image digest, source tag, commit, or archive checksum changes trigger
  full revalidation.
- Publication, distribution, handover, Staging, or Production use remains
  prohibited or separately governed.

## Security, resource, and license impact

Immutable official binaries reduce local compiler-chain exposure but retain
upstream binary trust. Existing vulnerability scans, SBOMs, package-license
reports, and patch-delta review remain mandatory. No runtime CPU, memory, disk,
network, capability, data, or credential boundary changes.

OD-06 remains OPEN. This decision is not a legal conclusion and grants no
publication or redistribution permission.

## Migration and rollback

No image, schema, data, or runtime migration occurs. Documentation and evidence
must use the clarified terminology. Rollback is a governed decision requiring
full PostgreSQL and Kafka source builds, followed by complete requalification.

## Revalidation triggers

- change to an official binary digest, source tag, commit, or archive checksum;
- change to build mode or remediation boundary;
- upstream provenance or binary-integrity concern;
- publication, distribution, handover, Staging, or Production request;
- a newer owner decision supersedes this contract.
