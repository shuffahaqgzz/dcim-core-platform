# ADR Index dan Phase 0 Crosswalk

Nomor ADR existing dipertahankan agar accepted history dan ADR 0007 milik owner tidak rusak. Crosswalk conceptual decisions Phase 0:

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
| Repository license pending | [ADR-0011](0011-public-repository-license-decision-pending.md) (superseded by ADR-0019) |
| Internal Grafana Development access | [ADR-0012](0012-internal-grafana-development-access.md) |
| Derived hardened foundation images | [ADR-0013](0013-derived-hardened-foundation-images.md) |
| Official release binary and source provenance | [ADR-0014](0014-official-release-binary-source-provenance.md) |
| Full-source Prometheus gRPC remediation | [ADR-0015](0015-full-source-prometheus-grpc-remediation.md) |
| Custom PostgreSQL CMDB (OD-01) | [ADR-0007](0007-cmdb-implementation-for-development.md) |
| Workflow engine split (OD-02) | [ADR-0016](0016-workflow-engine-split.md) |
| React NOC dashboard frontend (OD-03) | [ADR-0017](0017-react-noc-dashboard-frontend.md) |
| Elasticsearch search platform (OD-04) | [ADR-0018](0018-elasticsearch-search-platform.md) |
| Apache-2.0 repository license (OD-06) | [ADR-0019](0019-apache-2-0-repository-license.md) |
| Identity alias/conflict resolution (C-06) | [ADR-0020](0020-identity-alias-conflict-resolution.md) |
| Foundation resource limits/retention (C-07) | [ADR-0021](0021-foundation-resource-limits-retention.md) |
| Connector polling/source-impact controls (C-09) | [ADR-0023](0023-connector-polling-source-impact-controls.md) |
| Python/FastAPI service language baseline (OD-07) | [ADR-0024](0024-python-fastapi-service-language-baseline.md) |
| Automation execution preconditions (PRD Q4) | [ADR-0025](0025-automation-execution-preconditions.md) |
| Program technology version baseline (PRD Q8) | [ADR-0026](0026-program-technology-version-baseline.md) |
| Private LLM serving baseline (PRD Q7) | [ADR-0027](0027-private-llm-serving-baseline.md) |
| Duplicate disposition and deterministic identity | [ADR-0028](0028-duplicate-disposition-and-deterministic-identity.md) |

ADR-0007 adalah keputusan OD-01 yang diterima (Accepted 2026-07-28). ADR-0022 tetap dicadangkan dan tidak digunakan.
