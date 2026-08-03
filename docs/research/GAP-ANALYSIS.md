# Gap Analysis — DCIM Core Platform Program

**Tanggal:** 2026-07-28  
**Metode:** Membandingkan target dari `dcim-wiki` (reference designs, use-case analysis, SLA framework) dengan implementasi aktual di `dcim-core-platform`, `DCIM_SRV_DATA_COLLECTION`, `dcim_project`, `n8n-workflows`, `SIEM`, `SOAR`.  
**Kode severity:** P1 = blokir milestone / safety; P2 = high functional gap; P3 = medium / completeness; P4 = documentation / polish.

---

## 1. Summary Matrix

| Komponen | Wiki Target (B#) | Implementasi Aktual | Overall Gap | Blocker P1 |
|---|---|---|---|---|
| Core Platform foundation | B1 Infrastructure Provisioning | Compose dev-build + derived images + 205 passing tests; synthetic Phase 2 vertical-slice evidence delivered 2026-08-02 | Kecil | #20 and owner disposition for #21 |
| Data Ingestion & Integration | B2 + DII UC Analysis 14 UCs | Pipeline v4.6.1 fungsional, tetapi credential crisis | Sedang–Besar | Credential exposure, no CI, no tests |
| Asset Repository | B3 + 15 UCs | Hanya placeholder `services/asset-repository/README.md` | Besar | Belum ada service |
| CMDB | B4 + 16 UCs | Scaffold `services/cmdb/`; OD-01 accepted 2026-07-28 ([ADR-0007](../adr/0007-cmdb-implementation-for-development.md)) | Besar | Belum ada service code |
| Web Dashboard | B5 + 7 views | Hanya placeholder `web/README.md` | Besar | Belum ada UI |
| SIEM/SOC | B6 + 20 UCs | Stub SIEM repo 6 file | Sangat besar | Tidak ada correlation engine, Kafka contract |
| Analytics & AI Engine | B7 + 26 UCs | Kode anomaly/RCA, API banyak stub | Sedang–Besar | LLM/RAG API, capacity/energy, forecasting stub |
| Workflow Automation | B8 + 17 UCs | n8n workflow restart/decommission fungsional | Sedang | Safety boundary violation, no dry-run/rollback |
| External Integrations | B9 + adapter pattern | `itop/` integration di ingestion; ServiceNow/Jira/SAP/Oracle tidak ada | Besar | Hanya iTop |
| SOAR | SIEM SOAR reference design | Prototype 3 file | Sangat besar | No deployable Wazuh integration, no containment |

---

## 2. Core Platform (`dcim-core-platform`)

| ID | Requirement / Target | Implemented | Severity | Evidence |
|---|---|---|---|---|
| CP-01 | Phase 0 safety baseline DEV-APPROVED | ✅ Yes | — | `docs/phase0/phase0-checklist.md` |
| CP-02 | Phase 1 foundation lifecycle (issue #9) | ⚠️ Closed 2026-07-23, tetapi remediation #20 open | P1 | `docs/phase1/ISSUE-9-CLOSURE-PACKAGE.md`, PR #22 |
| CP-03 | First synthetic P1/P2 vertical slice (issue #21) | ✅ Delivered as synthetic Development evidence; owner disposition pending | P1 | [`docs/evidence/2026-08-02-phase2-vertical-slice.md`](../evidence/2026-08-02-phase2-vertical-slice.md), `make phase2-check` |
| CP-04 | Canonical event envelope schema | ✅ Yes | — | `schemas/event-envelope.schema.json` |
| CP-05 | Asset / CI identity schema | ✅ Yes | — | `schemas/asset.schema.json`, `schemas/ci.schema.json` |
| CP-06 | CMDB service | ❌ Scaffold only (OD-01 accepted 2026-07-28, [ADR-0007](../adr/0007-cmdb-implementation-for-development.md)) | P1 | `services/cmdb/` |
| CP-07 | Asset Repository service | ❌ Placeholder only | P2 | `services/asset-repository/README.md` |
| CP-08 | API service | ❌ Placeholder only | P2 | `services/api/README.md` |
| CP-09 | Analytics service | ❌ Placeholder only | P2 | `services/analytics/README.md` |
| CP-10 | Workflow service | ❌ Placeholder only | P2 | `services/workflow/README.md` |
| CP-11 | Web dashboard (React/Vue) | ❌ Placeholder only | P2 | `web/README.md`; ADR-0017 accepted |
| CP-12 | Connector code (Redfish/SNMP) | ✅ Fixture-replay adapters delivered; live activation remains out of scope | P2 | [`docs/evidence/2026-08-02-phase2-vertical-slice.md`](../evidence/2026-08-02-phase2-vertical-slice.md), `connectors/redfish/`, `connectors/snmp/`; C-01/C-09 remain open |
| CP-13 | Elasticsearch integration | ❌ Placeholder only | P2 | ADR-0018 accepted; no code |
| CP-14 | Resource limits in Compose match ADR-0021 | ⚠️ Values still older | P3 | `deploy/compose/dev-build/compose.yaml` vs `docs/adr/0021-foundation-resource-limits.md` |
| CP-15 | Demo path executable | ❌ README only | P3 | `deploy/compose/demo/README.md` |
| CP-16 | Deterministic identity collision tests | ⚠️ ADR-0020 accepted, tests pending | P3 | C-06 open |

---

## 3. Data Ingestion & Integration (`DCIM_SRV_DATA_COLLECTION` vs B2 Reference Design)

| ID | Wiki Target | Actual v4.6.1 | Severity | Evidence |
|---|---|---|---|---|
| DI-01 | 14 use cases (DII UC Analysis FINAL) | ⚠️ Pipeline operational, tetapi fitur-to-UC mapping informal | P3 | `technical-requirements/dii-use-case-analysis-final.md` vs `src/` |
| DI-02 | 99.95% uptime SLA, 10K EPS | ❌ No HA, single broker historically | P2 | `comparisons/v4.4-pipeline-architecture-komparasi.md` (remaining gaps: Prometheus+Grafana, SIEM, RBAC, circuit breaker, data classification) |
| DI-03 | Schema Registry with `.avsc` contract | ⚠️ Schema Registry container ada, schema hanya string Python | P2 | `src/schemas/avro_schemas.py` vs `schema-registry/docker-compose.yml` |
| DI-04 | Validation processor | ⚠️ `configs/data_quality_schema.yaml` spec only; no runtime validator | P2 | `src/skills/telemetry/normalizer/executor.py` |
| DI-05 | SIEM consumer / Kafka topic contract | ⚠️ `siem_es_consumer` exists, no deployable Wazuh config | P2 | `SIEM/` stub |
| DI-06 | ITSM/ERP/DMS connectors (B9) | ❌ Only iTop | P2 | `itop/sync/` |
| DI-07 | Prometheus + Grafana metrics | ⚠️ Stack operational, tetapi metrics ingestion gap masih P2 | P2 | `comparisons/v4.4-pipeline-architecture-komparasi.md` |
| DI-08 | RBAC / data classification | ❌ Not implemented | P2 | — |
| DI-09 | Circuit breaker pattern | ✅ Implemented | — | `src/utils/circuit_breaker.py` |
| DI-10 | Credential management via Vault | ❌ Hardcoded passwords in 20+ scripts | P1 | `scripts/*`, `src/utils/circuit_breaker.py`, `configs/secrets/` |
| DI-11 | Test suite / CI gates | ❌ 1 test file, no GitHub Actions | P1 | `tests/test_circuit_breaker.py`; `.github/workflows/` missing |
| DI-12 | NiFi flows source-controlled & reviewable | ⚠️ `nifi/flow.json.gz` binary only | P3 | `nifi/flow.json.gz` |
| DI-13 | AI agent integrated | ❌ `ai_agent/` scaffold detached | P3 | `ai_agent/README.md` empty |
| DI-14 | Version consistency | ⚠️ Header v4.6.1, table v4.5.2, docs v3.5.5 | P4 | `README.md` |

---

## 4. Asset Repository (`dcim-core-platform` vs B3)

| ID | Requirement | Implemented | Severity | Evidence |
|---|---|---|---|---|
| AR-01 | PostgreSQL schema 4 tables (asset, location, contract, lifecycle) | ❌ No code | P1 | `services/asset-repository/README.md` placeholder |
| AR-02 | CRUD API + bulk import | ❌ No code | P1 | — |
| AR-03 | Reconciliation engine | ❌ No code | P2 | — |
| AR-04 | Redis cache enrichment API | ❌ No code | P2 | — |
| AR-05 | 15 use cases | ❌ No code | P1 | `technical-requirements/asset-repository-use-case-analysis-final.md` |

---

## 5. CMDB (`dcim-core-platform` vs B4)

| ID | Requirement | Implemented | Severity | Evidence |
|---|---|---|---|---|
| CM-01 | CI data model 11 types + 7 relationship types | ❌ No code | P1 | `services/cmdb/README.md` placeholder |
| CM-02 | Topology & impact analysis engine | ❌ No code | P1 | — |
| CM-03 | CI CRUD API | ❌ No code | P1 | — |
| CM-04 | Reconciliation with Asset + Discovery | ❌ No code | P2 | — |
| CM-05 | Service mapping / health dashboard | ❌ No code | P2 | — |
| CM-06 | Keputusan implementasi (iTop vs NetBox vs custom) | ✅ ADR-0007 Accepted 2026-07-28 — custom PostgreSQL CMDB | — | `docs/adr/0007-cmdb-implementation-for-development.md` |

---

## 6. Web Dashboard (`dcim-core-platform` vs B5)

| ID | Requirement | Implemented | Severity | Evidence |
|---|---|---|---|---|
| DB-01 | React frontend scaffold (ADR-0017) | ❌ No code | P1 | `web/README.md` placeholder |
| DB-02 | 7 views (NOC/SOC/Facilities/CMDB/SLA/Logs/Tasks) | ❌ No code | P1 | — |
| DB-03 | API Gateway + RBAC/SSO | ❌ No code | P1 | — |
| DB-04 | WebSocket real-time | ❌ No code | P2 | — |

---

## 7. SIEM/SOC (`SIEM` repo vs B6 + `siem-soar.md`)

| ID | Requirement | Implemented | Severity | Evidence |
|---|---|---|---|---|
| SI-01 | Wazuh ingestion → Kafka `dcim.siem.events` | ❌ No Kafka output config | P1 | `SIEM/wazuh-manager/ossec.conf` hanya `<integration>` ke Shuffle webhook |
| SI-02 | 10 correlation engine rules | ❌ 2 custom rules only | P1 | `SIEM/wazuh-manager/rules/local_rules.xml` |
| SI-03 | 450K-entry threat-intel CDB lists | ❌ Claimed, missing files | P1 | `SIEM/README.md` |
| SI-04 | Incident response workflow 6 states | ❌ No code | P1 | — |
| SI-05 | SOC API 12 endpoints | ❌ No code | P1 | — |
| SI-06 | CIS benchmark compliance | ❌ No code | P2 | — |
| SI-07 | 20 use cases | ❌ 2 rules only | P1 | `technical-requirements/siem-use-case-analysis-final.md` |

---

## 8. Analytics & AI Engine (`dcim_project` vs B7)

| ID | Requirement | Implemented | Severity | Evidence |
|---|---|---|---|---|
| AI-01 | Time-series pipeline Kafka → TimescaleDB | ✅ `metrics_consumer.py` | — | `implementation/dcim_ai_v2_rag/stream/metrics_consumer.py` |
| AI-02 | Anomaly detection ensemble | ✅ `services/anomaly_service.py` | — | — |
| AI-03 | RCA engine | ✅ `root_cause/rca_engine.py` | — | — |
| AI-04 | Model registry DB-backed | ✅ `registry/model_registry.py` | — | — |
| AI-05 | FastAPI analytics endpoints | ⚠️ Skeleton, beberapa router stub | P2 | `api/main.py` |
| AI-06 | Predictive maintenance API | ❌ Stub `501` | P2 | `api/routers/predictions.py` |
| AI-07 | Capacity forecasting API | ❌ Stub `501` | P2 | `api/routers/capacity.py` |
| AI-08 | Energy / PUE optimization API | ❌ Stub `501` | P2 | `api/routers/energy.py` |
| AI-09 | LLM/RAG inference service API | ❌ Stub `501` | P1 | `api/routers/llm.py` |
| AI-10 | Fine-tuned model weights | ❌ `llm/models/` empty | P3 (Phase 4 — ADR-0027) | — |
| AI-11 | RAG system v2 | ❌ Empty directory | P2 | `dcim_ai_v2_rag/rag/` |
| AI-12 | 26 use cases | ⚠️ Partial | P2 | `technical-requirements/analytics-ai-use-case-analysis-final-v2.md` |
| AI-13 | Async queue worker + retry | ❌ Documented only | P2 | `task_objective/MT-023_LLM_Inference_Service_Revised.md` |
| AI-14 | 32 acceptance criteria | ⚠️ Some criteria not testable | P2 | — |

---

## 9. Workflow Automation (`n8n-workflows` vs B8)

| ID | Requirement | Implemented | Severity | Evidence |
|---|---|---|---|---|
| WF-01 | State machine 10 states | ⚠️ Implisit dalam n8n, tidak formal | P2 | workflow JSON |
| WF-02 | Multi-level approval chains | ✅ Gmail 3-level untuk decommission | — | `Server-Hyper-V-Decommissioning/workflows/*.json` |
| WF-03 | ITSM integration (ServiceNow/Jira) | ❌ iTop CMDB only, no ServiceNow/Jira | P2 | — |
| WF-04 | Runbook engine | ❌ No code | P2 | — |
| WF-05 | Auto-remediation with safety guards | ❌ Guards missing; service restart no approval | P1 | `Automated-Incident-Remediation-Service-Restart/workflows/*.json` |
| WF-06 | Dry-run / blast-radius / rollback | ❌ No | P1 | — |
| WF-07 | OT-safe enforcement (no auto-reboot for critical systems) | ❌ Violated | P1 | workflow melakukan `systemctl restart` |
| WF-08 | Core platform REST API / Kafka trigger | ❌ Webhook/form only | P2 | workflow JSON |
| WF-09 | 17 use cases | ⚠️ 2–3 operational scenarios only | P2 | `technical-requirements/workflow-automation-use-case-analysis-final-v2.md` |
| WF-10 | Audit trail / RBAC | ❌ No | P2 | — |

---

## 10. External Integrations (B9)

| ID | Requirement | Implemented | Severity | Evidence |
|---|---|---|---|---|
| EX-01 | Adapter framework (10 connectors: ServiceNow, Jira, SAP, Oracle, DMS, NMS, cloud) | ❌ Only iTop | P1 | `itop/`, `reference-designs/block9-external-integrations.md` |
| EX-02 | Normalizer + DLQ + health monitoring | ⚠️ Partial in ingestion, not generic adapter | P2 | — |
| EX-03 | YAML mapping configs | ⚠️ `configs/metric_mapping.yaml` | P3 | — |

---

## 11. SOAR (`SOAR` repo vs `siem-soar.md` reference)

| ID | Requirement | Implemented | Severity | Evidence |
|---|---|---|---|---|
| SO-01 | TraceCat SOAR / Temporal workflow engine | ❌ n8n prototype only | P1 | `SOAR/N8N Workflow/SOAR.json` |
| SO-02 | Wazuh → Kafka `dcim.siem.alerts` → SOAR | ❌ No deployable Wazuh config | P1 | — |
| SO-03 | OT-safe playbook enforcement | ❌ No containment actions committed | P1 | — |
| SO-04 | Case management (IRIS) | ⚠️ DFIR-IRIS case creation node exists | P2 | workflow JSON |
| SO-05 | 100+ connectors | ❌ 3 integrations only | P2 | — |
| SO-06 | MCP AI agent integration | ❌ No | P2 | — |

---

## 12. Integration Contract Gaps

| ID | Contract | Defined in Wiki | Defined in Code | Severity |
|---|---|---|---|---|
| IC-01 | Canonical event envelope `dcim.normalized.events` | ✅ | ⚠️ Schema only in Python | P2 |
| IC-02 | Raw topics `dcim.raw.*` | ✅ | ✅ | — |
| IC-03 | SIEM topic `dcim.siem.alerts` | ✅ | ⚠️ Consumer exists, no producer config | P1 |
| IC-04 | Analytics topic `dcim.analytics.metrics` | ✅ | ✅ | — |
| IC-05 | AsyncAPI / OpenAPI contracts | ✅ | ❌ | P2 |
| IC-06 | Webhook contract core → n8n | ❌ | ❌ Webhook ad-hoc | P2 |
| IC-07 | Identity alias resolution API | ✅ | ❌ | P2 |

---

## 13. Safety & Security Gaps

| ID | Requirement | Actual | Severity | Evidence |
|---|---|---|---|---|
| SS-01 | No credentials in public repo | ❌ Hardcoded passwords/tokens in ingestion + workflow | P1 | `scripts/*`, `n8n-workflows/*.json`, `SIEM/wazuh-manager/ossec.conf` |
| SS-02 | Read-only source access | ❌ n8n workflow writes to servers, CMDB, firewall, monitoring | P1 | `n8n-workflows/Server-*-Decommissioning/workflows/*.json` |
| SS-03 | Dry-run automation | ❌ No dry-run | P1 | — |
| SS-04 | Human approval for destructive actions | ⚠️ Gmail approval for decommission, none for restart | P1 | — |
| SS-05 | Audit trail / RBAC | ❌ No | P2 | — |
| SS-06 | Secret management via Vault | ⚠️ Vault container ada, tetapi AppRole files committed + password hardcoded | P1 | `vault/config/`, `src/utils/secrets.py` |

---

## 14. Engineering Maturity Gaps

| ID | Requirement | Actual | Severity | Evidence |
|---|---|---|---|---|
| EM-01 | CI/CD di setiap repo | ❌ Core platform punya CI; satelit tidak | P1 | `.github/workflows/` hanya di core |
| EM-02 | Unit + integration tests | ⚠️ Core: 205 tests; ingestion: 1; AI: benchmark scripts; workflow/SIEM/SOAR: 0 | P1 | — |
| EM-03 | Reproducible builds / pinned deps | ✅ Core; ⚠️ Ingestion (version inconsistency); ❌ AI/workflow | P2 | — |
| EM-04 | Code review / multi-author | ❌ Satelit mostly single-author | P2 | `git log` |
| EM-05 | SBOM / vulnerability scanning | ✅ Core `foundation_supply_chain.py`; ❌ satelit | P2 | — |
| EM-06 | Public-safety scanner | ✅ Core; ❌ Satelit | P1 | `scripts/check_public_repo_safety.py` |

---

## 15. Recommendations per Severity

### P1 — Resolve before any production claim
1. Rotasi semua kredensial yang pernah muncul di repo publik; pindahkan ke Vault/Docker secrets.
2. Hapuskan atau isolasi workflow `systemctl restart` dan decommission sampai memiliki dry-run, approval, rollback, OT-safe enforcement.
3. Bangun CI/CD minimum (public-safety scan, lint, unit test) di setiap repo satelit.
4. ~~Putuskan OD-01 (CMDB) dan OD-07 (service language/framework) di core platform.~~ **[COMPLETED]** OD-01 and OD-07 were accepted 2026-07-28; implement service work against ADR-0007 and ADR-0024.
5. Tutup issue #20 dan #21 dengan scope minimal, verifiable, bukan dengan fitur tambahan.

### P2 — Close before multi-team staging
6. Implementasi Asset Repository, API, Analytics, Workflow, Web Dashboard service code di core platform.
7. Buat `.avsc` / AsyncAPI contract untuk event topics.
8. Bangun SIEM correlation engine + Kafka producer config.
9. Lengkapi AI API endpoints (LLM/RAG, capacity, energy, forecasting).
10. Implementasi adapter framework untuk ServiceNow/Jira/SAP/Oracle/cloud.

### P3 — Polish before governed production
11. Perbaiki inkonsistensi versi ingestion (v4.6.1 vs v4.5.2 vs v3.5.5).
12. Source-control NiFi flows dalam format reviewable.
13. Integrasikan `ai_agent/` scaffold dengan pipeline analytics.
14. Perbaiki resource-limit Compose agar sesuai ADR-0021.

---

*Lihat juga: `STATUS-SUMMARY.md`, `ARCHITECTURE.md`, `PRD.md`, `IMPLEMENTATION-PLAN.md`, `RISK-REGISTER.md`, `DECISION-LOG-REVIEW.md`.*
