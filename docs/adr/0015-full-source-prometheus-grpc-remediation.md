# ADR-0015: Full-Source Prometheus gRPC Remediation for Development

- Status: Accepted
- Date: 2026-07-22
- Owner: shuffahaqgzz
- Decision source: explicit owner approval in the issue #9 closure-blocker task
- Issues: #10, parent #9
- Extends: [ADR-0013](0013-derived-hardened-foundation-images.md)
- Follows: [ADR-0014](0014-official-release-binary-source-provenance.md)

## Context

The fresh issue #10 supply-chain qualification found two fixable High results
for `GHSA-hrxh-6v49-42gf` in the official Prometheus v3.13.1 image. The results
come from the `prometheus` and `promtool` binaries, which both contain
`google.golang.org/grpc` v1.81.1. The advisory identifies v1.82.1 as fixed.

Prometheus v3.13.1 is the current pinned upstream release and its source module
still selects gRPC v1.81.1. Waiting for an official rebuild would leave the
accepted zero-Critical and zero-fixable-High gate blocked. ADR-0014 requires a
new owner decision before another component adopts a full-source assembly mode.

## Decision drivers

- Preserve Prometheus v3.13.1 behavior and every existing Compose contract.
- Remove the blocking finding without weakening or suppressing the gate.
- Keep the dependency delta limited to the public fixed gRPC release.
- Make source, UI, dependency, builder, and runtime inputs immutable and
  reproducible.
- Keep all build and runtime use synthetic, local, and non-published.

## Decision

Build a Development-only Prometheus derivative from the exact v3.13.1 source
commit `73ff57ce2b8161059ac7fe5188f03f1c3d22b29a`. Compile both `prometheus` and
`promtool` with Go 1.26.5 and replace only `google.golang.org/grpc` v1.81.1 with
the exact v1.82.1 source commit
`ebd8f06a09426fbece97157c95c3917abff28f4e`.

The recipe must:

1. checksum-verify the exact Prometheus source archive, upstream v3.13.1 web UI
   artifact, and gRPC source archive;
2. use digest-pinned Go builder and official Prometheus v3.13.1 runtime base;
3. perform compilation without network access after locked modules are fetched;
4. preserve binary paths, user, command, volumes, networks, health checks,
   resource limits, persistence, smoke, and recovery contracts;
5. expose the derivative only through the local immutable derived-image lock;
6. record derivative and gRPC remediation OCI labels;
7. pass reproducibility, SBOM, comprehensive license, vulnerability, policy,
   fast-smoke, clean acceptance, recovery, and public-safety gates.

No feature patch, source fork, scanner suppression, registry publication,
Staging, Production, connected-source, or handover distribution is authorized.
OD-06 remains OPEN.

## Options considered

### 1. Full-source v3.13.1 build with a local gRPC v1.82.1 replacement

Selected. It stays inside ADR-0013's dependency-remediation boundary and keeps
the service version and runtime design unchanged.

### 2. Keep the blocked official image

Rejected for the issue #9 closure candidate because the fixable-High result is
a NO-GO under the accepted gate. It remains the rollback input until a clean
official image is available.

### 3. Suppress or reclassify the finding

Rejected. It would weaken the accepted security policy without removing the
vulnerable dependency.

### 4. Upgrade Prometheus beyond v3.13.1 or change observability design

Rejected as unnecessary scope expansion and a runtime compatibility change.

## Consequences

The derived-image set expands from four to five components, and both the main
Prometheus service and observability smoke service must resolve the same local
immutable image ID. Build time and external protected evidence grow because two
binaries and embedded UI assets are rebuilt.

The project assumes additional build-chain and dependency-maintenance risk. A
fresh official same-line image that passes all gates remains the preferred
replacement.

## Security and license impact

The known fixable High dependency is replaced rather than ignored. Immutable
inputs, offline compilation, reproducibility comparison, SBOM validation, and a
fresh vulnerability scan constrain new supply-chain risk.

The full-source binary can change the detected license inventory. Every
category, count, and fingerprint must be revalidated comprehensively and must
fail closed on any unreviewed change. This ADR is not legal advice, does not
resolve OD-06, and permits neither publication nor distribution.

## Migration and rollback

No schema, data, volume, API, port, or configuration migration is introduced.
Activation changes only the immutable image selected through the protected
derived lock. Rollback selects the last qualified compatible image, preserves
the named Prometheus volume, and reruns policy, smoke, and recovery checks.

## Revalidation triggers

- Prometheus tag, commit, source archive, web UI artifact, or runtime digest
  changes;
- gRPC version, commit, checksum, or dependency graph changes;
- Go builder, Dockerfile, recipe, scanner, or vulnerability database changes;
- license category, count, fingerprint, or obligation changes;
- official upstream publishes a clean compatible replacement;
- publication, distribution, handover, Staging, Production, or connected-source
  use is requested;
- OD-06 changes or a newer owner decision supersedes this ADR.
