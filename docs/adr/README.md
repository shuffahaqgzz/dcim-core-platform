# ADR Index dan Phase 0 Crosswalk

Nomor ADR existing dipertahankan agar accepted history dan proposed ADR 0007 milik owner tidak rusak. Crosswalk conceptual decisions Phase 0:

| Phase 0 decision | Governing ADR |
|---|---|
| Public code/private runtime data | [ADR-0002](0002-public-code-private-runtime.md) |
| Production-connected Development read-only | [ADR-0004](0004-read-only-integration-plane.md) |
| Three logical runtime planes | [ADR-0001](0001-compose-profiles-for-development.md) + [ADR-0004](0004-read-only-integration-plane.md) |
| Development single-broker Kafka | [ADR-0003](0003-single-broker-kraft-development.md) |
| Synthetic/sanitized demo data | [ADR-0008](0008-synthetic-and-sanitized-demo-data.md) |
| Asset/CI identity | [ADR-0006](0006-canonical-contract-and-identity.md) |
| Hermes read-only shadow after gate | [ADR-0009](0009-hermes-read-only-shadow-after-gate.md) |
| No direct device/OT action | [ADR-0005](0005-dry-run-automation.md) |
| Solo Dev to multi-team handover | [ADR-0010](0010-solo-dev-to-multiteam-handover.md) |
| Repository license pending | [ADR-0011](0011-public-repository-license-decision-pending.md) |
| Internal Grafana Development access | [ADR-0012](0012-internal-grafana-development-access.md) |
| Derived hardened foundation images | [ADR-0013](0013-derived-hardened-foundation-images.md) |
| Official release binary and source provenance | [ADR-0014](0014-official-release-binary-source-provenance.md) |
| Full-source Prometheus gRPC remediation | [ADR-0015](0015-full-source-prometheus-grpc-remediation.md) |

ADR 0007 tidak dicantumkan karena merupakan proposed CMDB decision (OD-01), bukan fixed Phase 0 decision.
