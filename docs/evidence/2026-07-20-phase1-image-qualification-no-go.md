# Phase 1 Foundation Image Qualification — NO-GO

- Date: 2026-07-20
- Verification window: 2026-07-20 07:12:51–07:17:08 UTC
- Subject: worktree at `6957ce85b0b130a4c4855f77291a22dd2053ea3e`
- Issues: #10, parent #9
- Scope: official-upstream foundation images for `linux/amd64`
- Status: NO-GO; owner review pending

## Decision

The current complete image set does not satisfy the accepted vulnerability
gate. No image was re-pinned, no vulnerability policy was weakened, and no
derived image was introduced. Issues #11 and #12 remain blocked by #10.

This record binds to an uncommitted Phase 1 worktree snapshot, not an immutable
milestone commit. It is evidence of the blocker only and makes no acceptance,
Staging, Production, HA, or P1/P2 claim.

## Reproduction

The protected runtime root resolved outside the repository. Raw SBOM, license,
and vulnerability reports remained there and were not promoted to Git.

```text
make foundation-supply-chain DCIM_RUNTIME_ROOT=<external-protected-root>
```

Scanner:
`aquasec/trivy:0.72.0@sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f`.
The scanner returned `NO-GO`. Artifact timestamps measured a minimum evidence
generation duration of 4 minutes 17 seconds; the current script did not record
exact end-to-end wall time.

## Gate result

| Component | Critical | High with fix | Result |
|---|---:|---:|---|
| PostgreSQL 17.10 Bookworm | 16 | 14 | FAIL |
| Apache Kafka 4.3.1 | 0 | 10 | FAIL |
| Prometheus 3.13.1 | 0 | 0 | PASS |
| Grafana OSS 13.1.0 | 0 | 49 | FAIL |
| PostgreSQL exporter 0.20.1 | 0 | 1 | FAIL |
| Eclipse Temurin JRE 21.0.11+10 | 0 | 0 | PASS |

Any Critical finding is blocking. Any High finding with an available fix is
blocking. Counts above come from the external Trivy JSON summary; raw findings
remain outside Git.

## Official variant checks

Three narrower official variants were scanned to test whether base-image choice
alone could remove the blocker:

| Candidate | Critical | High with fix | Disposition |
|---|---:|---:|---|
| PostgreSQL 17.10 Alpine 3.24 | 1 | 14 | FAIL |
| Grafana 13.1.0 distroless-slim | 0 | 3 | FAIL |
| Apache Kafka Native 4.3.1 | 0 | 0 | Not selected |

Kafka Native passes this vulnerability count, but selecting it would change the
accepted JVM/JMX observability contract. It cannot silently replace the current
Kafka image. It also does not remove the independent PostgreSQL, Grafana, and
PostgreSQL exporter blockers.

## Provenance and license review

Exact tags, top-level digests, and `linux/amd64` manifest digests were checked
against primary registry records. Release and ownership sources:

- [Trivy 0.72.0](https://github.com/aquasecurity/trivy/releases/tag/v0.72.0)
- [PostgreSQL 17.10](https://www.postgresql.org/docs/17/release-17-10.html)
- [Apache Kafka downloads](https://kafka.apache.org/community/downloads/)
- [Prometheus 3.13.1](https://github.com/prometheus/prometheus/releases/tag/v3.13.1)
- [Grafana 13.1.0](https://github.com/grafana/grafana/releases/tag/v13.1.0)
- [PostgreSQL exporter 0.20.1](https://github.com/prometheus-community/postgres_exporter/releases/tag/v0.20.1)
- [Eclipse Temurin 21.0.11+10](https://github.com/adoptium/temurin21-binaries/releases/tag/jdk-21.0.11%2B10)
- [Prometheus JMX Exporter 1.6.0](https://github.com/prometheus/jmx_exporter/releases/tag/v1.6.0)

Inventory license values describe the primary project or runtime, not every
package in a composite OCI image. Full package-level license inventories remain
external. Grafana's AGPL review remains explicit, and OD-06 remains OPEN.

## Context7 current-documentation review

Context7 was queried on 2026-07-20 as a documentation index. Its output was
treated as untrusted MCP input and retained only where it linked to public
upstream documentation. Context7 did not provide immutable registry digests,
vulnerability-database freshness, or authoritative proof of the latest stable
release for every component; it therefore cannot replace registry resolution
and scanning.

| Component | Context7 library | Qualification guidance from upstream docs | Remaining gap |
|---|---|---|---|
| PostgreSQL image | `/websites/hub_docker_postgres` | Exact patch and OS variants exist; qualify one exact variant rather than a mutable major tag. | Supported-major policy, rebuild cadence, digest, and vulnerability response were not surfaced. |
| PostgreSQL exporter | `/prometheus-community/postgres_exporter` | PostgreSQL 9.1–18 support is documented; secret-file delivery and UID/GID 65534 are documented. | Quick start uses an unversioned image; current fixed release and digest were not surfaced. |
| Kafka | `/apache/kafka` | JVM and Native images are distinct. Native remains experimental and intended for local development/testing. | No documented basis to replace the accepted JVM/JMX path or claim a latest fixed JVM image. |
| JMX Exporter | `/prometheus/jmx_exporter` | Current examples use the `1.6.0` Java agent and JMX MBeans. | Exact Kafka MBean/rule compatibility and current release-index proof were not surfaced. |
| Eclipse Temurin | `/websites/adoptium_net` | Official curated images and JCK/AQAvit validation are documented. | Current tag matrix and Kafka Java compatibility were not surfaced. |
| Prometheus | `/websites/prometheus_io` | Preserve `/-/ready`, `promtool check healthy`, and `/etc/prometheus` configuration behavior after any re-pin. Supported LTS lines receive security fixes for one year. | No official slim/distroless variant or exact latest stable tag/digest was surfaced. |
| Grafana | `/websites/grafana_grafana` | Official docs cover Alpine and Ubuntu images. Alpine is smaller but may have musl compatibility limits; provisioning must be retested per variant. | No documented distroless/slim equivalent, current fixed release, security channel, or digest was surfaced. |
| Trivy | `/aquasecurity/trivy` | Severity filters, failing exit codes, vulnerability DB refresh, and `--ignore-unfixed` are documented. | Scanner release currency, DB timestamp/freshness, vendor severity precedence, and digest semantics were not surfaced. |

Primary documentation surfaced by Context7:

- [PostgreSQL Official Image](https://hub.docker.com/_/postgres)
- [PostgreSQL exporter documentation](https://github.com/prometheus-community/postgres_exporter/blob/master/README.md)
- [Kafka official Docker images](https://github.com/apache/kafka/blob/trunk/docs/getting-started/docker.md)
- [Kafka Native limitations](https://github.com/apache/kafka/blob/trunk/docker/native/README.md)
- [JMX Exporter deployment modes](https://github.com/prometheus/jmx_exporter/blob/main/website/docs/deployment/modes.md)
- [Adoptium FAQ](https://adoptium.net/docs/faq)
- [Prometheus 3.13 management API](https://prometheus.io/docs/prometheus/3.13/management_api)
- [Prometheus release cycle](https://prometheus.io/docs/introduction/release-cycle)
- [Grafana Docker configuration](https://grafana.com/docs/grafana/latest/setup-grafana/configure-docker)
- [Grafana provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning)
- [Trivy image command](https://github.com/aquasecurity/trivy/blob/main/docs/guide/references/configuration/cli/trivy_image.md)
- [Trivy cache and DB cleanup](https://github.com/aquasecurity/trivy/blob/main/docs/guide/references/configuration/cli/trivy_clean.md)

The asymmetric parent policy must remain explicit: every Critical finding
blocks, while a High finding blocks when a fix exists. Applying Trivy's global
`--ignore-unfixed` option alone would also hide unfixed Critical findings and
would not implement that policy. Continue to evaluate the JSON findings by
severity and fixed-version state.

### Re-qualification order

1. Resolve a supported official patch+OS tag from upstream release documents.
2. Resolve its immutable top-level and `linux/amd64` manifest digests from the
   official registry.
3. Refresh and record Trivy scanner and vulnerability DB metadata.
4. Scan the complete candidate set under one DB snapshot.
5. Run service contracts after every re-pin: PostgreSQL lifecycle; Kafka KRaft
   plus JVM/JMX metrics; Prometheus readiness and `promtool`; Grafana health and
   file provisioning; exporter backend health.
6. Promote only a reviewed public-safe summary. Keep raw reports external.

Context7 narrows this process but does not remove the official-image blocker.
The original official-image result in this record remains NO-GO. ADR-0013 now
provides the separately qualified Development disposition recorded in
[`2026-07-20-phase1-derived-image-qualification.md`](2026-07-20-phase1-derived-image-qualification.md).

## Blocker disposition

Owner acceptance of ADR-0013 permits qualification to resume with constrained
derived hardened images for the four failing components. The build must preserve
the existing service versions and runtime contracts, pass the unchanged gate,
and satisfy ADR-0013 build, provenance, license, lifecycle, and rollback
requirements. Rerun the complete pinned set under one scanner database snapshot;
do not combine independently qualified results.

Weakening the vulnerability gate, replacing the JVM/JMX Kafka design, publishing
derived images, or resolving OD-06 remain outside this ticket's accepted scope.
A clean official upstream image remains the preferred replacement. C-03, C-05,
and C-07 remain unchanged.

## Public-repository boundary

Only counts, immutable public image identifiers, primary-source links, and the
synthetic Development scope are recorded here. No credential, private endpoint,
host identity, topology, raw report, payload, dump, or connected-source data was
read or persisted in the repository.
