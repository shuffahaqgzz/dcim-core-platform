# ADR-0013: Derived Hardened Foundation Images for Development

- Status: Accepted
- Date: 2026-07-20
- Owner: shuffahaqgzz
- Decision source: owner acceptance in the issue #10 blocker-resolution task
- Issues: #10, parent #9
- Clarified by: [ADR-0014](0014-official-release-binary-source-provenance.md)

## Context

Issue #10 qualified the official-upstream image set selected for the synthetic
Phase 1 foundation. Prometheus and the Eclipse Temurin runtime passed the
accepted vulnerability gate. PostgreSQL, JVM Kafka, Grafana, and the PostgreSQL
exporter did not: the pinned official images contained Critical findings or High
findings with available fixes.

Waiting for upstream rebuilds preserves the original official-image policy but
blocks issues #11 and #12. Lowering the gate would conflict with the Development
baseline: a Critical quality or security gate failure is NO-GO. Replacing JVM
Kafka with Kafka Native would change the accepted JVM/JMX observability contract
and still would not resolve the other failing images.

The owner requested and accepted a temporary path that does not change the
existing service architecture. Implementation follows separately and remains
subject to every build, test, evidence, and license constraint in this ADR.

## Decision drivers

- Preserve the existing services, application versions, interfaces, Capability
  Profiles, networks, volumes, lifecycle commands, health contracts, and JVM/JMX
  observability design.
- Preserve the existing vulnerability gate without exceptions.
- Keep all execution synthetic-only inside `dcim-build`.
- Make every build input and output reproducible, attributable, reviewable, and
  public-safe.
- Avoid claiming official upstream status for project-built artifacts.
- Avoid silently resolving repository license decision OD-06.

## Decision

Permit project-built **derived hardened images** for failing Phase 1 components
under the constraints below. A derived hardened image uses the exact selected
upstream release inputs with only evidence-backed security remediation needed to
remove blocking findings. ADR-0014 accepts immutable official PostgreSQL and
Kafka release binaries plus checksum-verified source provenance; Grafana OSS and
PostgreSQL exporter remain full source builds. A derivative is not an
architecture, feature, API, schema, or configuration redesign.

### Scope

- Development `dcim-build` Runtime Plane only.
- Synthetic data only; no office or Production route, identity, credential, or
  artifact.
- Limited initially to PostgreSQL, JVM Kafka, Grafana OSS, and PostgreSQL
  exporter because those official images failed issue #10.
- Prometheus, Eclipse Temurin, Trivy, and the JMX Exporter artifact remain pinned
  to their qualified upstream artifacts unless a later scan blocks them.
- No Staging, Production, connected-source, HA, SLA, or hardening-completion
  claim.

### Build contract

Each derived image must:

1. start from the exact upstream release tag and immutable source commit, using
   the component-specific source-to-binary contract clarified by ADR-0014;
2. use digest-pinned base images and build-tool images;
3. keep a minimal, reviewable patch/dependency delta tied to public vulnerability
   identifiers and fixed versions;
4. change no service feature, external interface, data format, runtime topology,
   or accepted operational contract;
5. build reproducibly through a versioned repository recipe with no secret,
   private package source, mutable download, or host-specific input;
6. carry OCI labels that identify it as a DCIM Development derivative and record
   upstream source, source commit, recipe revision, and build timestamp;
7. produce immutable output digests, SBOM, package-license inventory,
   vulnerability report, and build provenance outside Git;
8. pass with zero Critical findings and zero High findings with available fixes;
9. receive explicit owner disposition and expiry for any unfixable High finding;
10. pass the same normalized Compose policy, health, fast-smoke, recovery, and
    public-safety gates as the official image it replaces.

No derived image may use an upstream image name or imply upstream endorsement.
No derived image may be pushed to a public or shared registry while OD-06 or the
applicable upstream redistribution/source obligations remain unresolved. Local
and ephemeral CI builds must not publish image layers or raw scan evidence.

### Patch boundary

Allowed changes are narrowly limited to:

- rebuilding an unchanged upstream release with a fixed compiler/runtime;
- updating a vulnerable base package to the vendor-fixed version;
- updating a vulnerable transitive dependency to a compatible fixed version;
- replacing a vulnerable bootstrap utility with its compatible fixed build.

Feature backports, interface changes, new plugins, service forks, removal of
required security behavior, and suppression or reclassification of scanner
findings are prohibited. If a remediation cannot stay inside this boundary, stop
and open a separate governed decision.

## Options considered

### 1. Wait for official upstream rebuilds

Lowest maintenance and provenance risk. Rejected for the temporary Development
path because it leaves #10 externally blocked for an unknown duration. Remains
the preferred rollback destination.

### 2. Build constrained derived hardened images

Selected. Preserves runtime design and security gate, but adds build-chain,
maintenance, and license obligations.

### 3. Accept Critical or fixable High findings

Rejected. Conflicts with the accepted Phase 1 policy and the baseline Critical
NO-GO rule.

### 4. Replace services or observability design

Rejected for this decision. The owner explicitly required the existing design
to remain unchanged.

## Security impact

Positive: known blocking findings must be removed without weakening policy.

New risks: the project becomes responsible for compiler, dependency, base-image,
patch, and build-provenance integrity. A compromised or stale build input could
produce an image that appears fixed while adding different vulnerabilities.

Controls:

- immutable inputs and outputs;
- isolated synthetic build context;
- minimal patch review;
- SBOM, provenance, license, and vulnerability evidence;
- no registry publication by default;
- exact contract and negative policy tests;
- replacement by an official clean image when available.

## License impact

OD-06 remains OPEN. Upstream application, base-image, build-tool, and transitive
license obligations apply independently of the repository license. Grafana OSS
requires explicit AGPL review, including modified-source and distribution
obligations. No derived image publication, handover distribution, or release
claim is permitted until those obligations are reviewed and recorded.

## Resource and operational impact

Runtime CPU, memory, disk budgets, ports, networks, capabilities, and persistence
contracts remain unchanged. Build-time CPU, disk, cache, and duration increase
and must be measured. Generated layers, caches, raw reports, and build artifacts
remain outside Git and are removable without affecting persisted service data.

## Migration and rollback

No database schema or data migration is introduced. Re-pin only the image
reference after the derivative passes the full service contract. Preserve named
volumes and verify application-version compatibility before startup.

Rollback uses the last qualified image digest. Prefer replacing each derivative
with a clean official image of the same compatible release line as soon as one
passes the complete gate. Every replacement reruns lifecycle and recovery tests.

## Acceptance evidence

Before implementation may close #10:

- owner marks this ADR Accepted;
- each derived recipe and patch delta receives review;
- reproducibility is demonstrated from a clean synthetic build root;
- exact source, build-input, and output digests are recorded;
- SBOM, license, provenance, and vulnerability gates pass;
- all existing service contracts pass without design changes;
- a public-safe summary records limitations and the upstream-replacement trigger.

## Revalidation triggers

- official upstream publishes a clean replacement;
- source tag, base image, compiler/runtime, dependency, or patch changes;
- Trivy scanner or vulnerability DB changes materially;
- a new Critical or fixable High finding appears;
- image publication, Staging, Production, or handover distribution is requested;
- OD-06 is resolved or a license obligation changes.
