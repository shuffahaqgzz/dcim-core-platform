# Product Requirements Document (PRD) — DCIM Core Platform

**Tanggal:** 2026-07-28  
**Status:** v1.0 — owner-confirmed 2026-07-28.  
**Sumber:** `dcim-wiki` (reference designs B1–B9, use-case analysis final, SLA frameworks, product description), `dcim-core-platform` governance, dan audit implementasi 6 repo.

---

## 1. Product Vision

**DCIM Core Platform** adalah platform Data Center Infrastructure Management untuk **visibility, control, automation, analytics, dan audit** atas infrastruktur fisik dan virtual di pusat data.

Platform menyatukan:
- **Data Ingestion & Integration** dari server (Redfish), UPS/NAS/network (SNMP), CCTV/NVR (ISAPI), dan security events (syslog/Wazuh).
- **Asset Repository** sebagai SSOT aset fisik, finansial, dan kontrak.
- **CMDB** sebagai SSOT Configuration Items, relasi, topology, dan impact analysis.
- **Analytics & AI Engine** untuk anomaly detection, predictive maintenance, RCA, capacity forecasting, energy optimization, dan LLM/RAG explanation layer.
- **Workflow Automation** untuk ticketing, approval, runbook, remediation, dan escalation.
- **SIEM/SOC** untuk security event ingestion, correlation, incident response, dan compliance.
- **Web Dashboard** untuk NOC, SOC, Facilities, CMDB Explorer, SLA/KPI, Logs, dan Tasks.
- **External Integrations** dengan ITSM, ERP, DMS, NMS, dan cloud providers.

---

## 2. Goals & Objectives

| Goal | Measurable Objective | Priority |
|---|---|---|
| G1 Visibility | 100% P1 critical assets discoverable and monitored in real time | P1 |
| G2 Control | All changes to asset/CI state go through approved workflow with audit trail | P1 |
| G3 Automation | Auto-remediation with OT-safe enforcement; human approval for destructive actions | P1 |
| G4 Intelligence | Predict failure 24–48 h ahead; detect anomaly ≤15 min; PUE drift detection | P1 |
| G5 Compliance | CIS benchmark alignment, audit trail, data retention policy | P2 |
| G6 Scale | 10K EPS security events, 99.95% uptime ingestion SLA | P2 |

---

## 3. Personas

| Persona | Needs | Primary Touchpoint |
|---|---|---|
| NOC Operator | Real-time dashboard, alert triage, asset search | Web Dashboard (B5) |
| SOC Analyst | Security correlation, case management, threat intel | SIEM/SOC (B6) + SOAR |
| Facilities Engineer | UPS, cooling, CCTV, energy/PUE metrics | Web Dashboard + Analytics |
| DCIM Admin | CMDB/Asset reconciliation, workflow approval, policy | CMDB + Workflow Automation |
| Infrastructure Manager | SLA/KPI, capacity planning, cost | Dashboard + Analytics |
| Compliance Officer | Audit trail, retention, CIS benchmark evidence | SIEM/SOC + Asset Repository |

---

## 4. Use Cases (Summary from Wiki)

### 4.1 Data Ingestion & Integration (14 UCs)

| ID | Use Case | Priority |
|---|---|---|
| DII-UC1 | Collect server telemetry via Redfish | P1 |
| DII-UC2 | Collect UPS power metrics via SNMPv3 | P1 |
| DII-UC3 | Collect NAS/storage metrics via SNMP | P1 |
| DII-UC4 | Collect network device metrics via SNMP | P2 |
| DII-UC5 | Collect CCTV/NVR health/events via ISAPI | P2 |
| DII-UC6 | Validate and normalize events to canonical schema | P1 |
| DII-UC7 | Route enriched events to ES/PG/TSDB | P1 |
| DII-UC8 | Handle parse/delivery failures via DLQ | P1 |
| DII-UC9 | Track event lineage end-to-end | P2 |
| DII-UC10 | Provide metrics for Prometheus/Grafana | P2 |
| DII-UC11 | Integrate with SIEM syslog input | P2 |
| DII-UC12 | Bulk import asset data from CSV/JSON | P2 |
| DII-UC13 | Adapter framework for ITSM/ERP/DMS | P3 |
| DII-UC14 | Schema evolution and compatibility | P2 |

### 4.2 Asset Repository (15 UCs)

| ID | Use Case | Priority |
|---|---|---|
| AR-UC1 | CRUD asset records | P1 |
| AR-UC2 | Bulk import assets | P1 |
| AR-UC3 | Search and filter assets | P1 |
| AR-UC4 | Asset lifecycle transitions | P1 |
| AR-UC5 | Contract and warranty tracking | P2 |
| AR-UC6 | Depreciation and financial data | P2 |
| AR-UC7 | Reconciliation with CMDB | P1 |
| AR-UC8 | Reconciliation with discovery | P2 |
| AR-UC9 | Enrichment API with Redis cache | P2 |
| AR-UC10 | NOC dashboard view | P2 |
| AR-UC11 | Workflow integration | P2 |
| AR-UC12 | Compliance reporting | P3 |
| AR-UC13 | Audit trail | P2 |
| AR-UC14 | NVR camera discovery | P3 |
| AR-UC15 | Location validation | P3 |

### 4.3 CMDB (16 UCs)

| ID | Use Case | Priority |
|---|---|---|
| CM-UC1 | CRUD Configuration Items | P1 |
| CM-UC2 | CI relationship management | P1 |
| CM-UC3 | Topology discovery | P2 |
| CM-UC4 | Impact analysis | P2 |
| CM-UC5 | Service mapping | P2 |
| CM-UC6 | CI lifecycle management | P1 |
| CM-UC7 | Reconciliation with Asset Repository | P1 |
| CM-UC8 | Reconciliation with discovery | P2 |
| CM-UC9 | Health dashboard | P2 |
| CM-UC10 | Data quality rules | P2 |
| CM-UC11 | NOC integration | P2 |
| CM-UC12 | SIEM enrichment | P2 |
| CM-UC13 | Workflow integration | P2 |
| CM-UC14 | Audit trail | P2 |
| CM-UC15 | Bulk import/export | P3 |
| CM-UC16 | API for external systems | P2 |

### 4.4 Analytics & AI Engine (26 UCs)

| ID | Use Case | Priority |
|---|---|---|
| AI-UC1 | Time-series ingestion to TSDB | P1 |
| AI-UC2 | Real-time anomaly detection | P1 |
| AI-UC3 | Predictive failure alerting | P1 |
| AI-UC4 | Capacity optimization | P2 |
| AI-UC5 | Energy/PUE anomaly detection | P2 |
| AI-UC6 | Root cause analysis (RCA) | P2 |
| AI-UC7 | Capacity forecasting | P2 |
| AI-UC8 | Energy optimization | P2 |
| AI-UC9 | Model training lifecycle | P2 |
| AI-UC10 | Model registry | P2 |
| AI-UC11 | LLM/RAG natural language explanation | P3 |
| AI-UC12–AI-UC26 | Fine-grained analysis, correlation, drift, simulation, etc. | P2–P3 |

### 4.5 Workflow Automation (17 UCs)

| ID | Use Case | Priority |
|---|---|---|
| WF-UC1 | Create workflow from template | P2 |
| WF-UC2 | Execute workflow with state machine | P2 |
| WF-UC3 | Multi-level approval | P1 |
| WF-UC4 | ITSM ticket creation | P2 |
| WF-UC5 | Runbook execution | P2 |
| WF-UC6 | Auto-remediation with safety guards | P1 |
| WF-UC7 | Escalation rules | P2 |
| WF-UC8 | Service restart (dry-run first) | P1 |
| WF-UC9 | Server decommission | P1 |
| WF-UC10 | Maintenance window check | P2 |
| WF-UC11 | Blast-radius check | P2 |
| WF-UC12 | Audit trail | P2 |
| WF-UC13 | RBAC | P2 |
| WF-UC14 | Notification channels | P2 |
| WF-UC15 | Workflow analytics | P3 |
| WF-UC16 | API for external triggers | P2 |
| WF-UC17 | Integration with SIEM alerts | P2 |

### 4.6 SIEM/SOC (20 UCs)

| ID | Use Case | Priority |
|---|---|---|
| SI-UC1 | Wazuh agent log ingestion | P1 |
| SI-UC2 | Syslog/CEF ingestion | P1 |
| SI-UC3 | Threat-intel correlation | P1 |
| SI-UC4 | Detection rules | P1 |
| SI-UC5 | Alert triage and enrichment | P2 |
| SI-UC6 | Case management | P2 |
| SI-UC7 | Incident response workflow | P2 |
| SI-UC8 | MITRE ATT&CK mapping | P2 |
| SI-UC9 | UEBA baselines | P3 |
| SI-UC10 | Compliance reporting | P2 |
| SI-UC11 | Kafka output to SOAR | P1 |
| SI-UC12 | SOC API | P2 |
| SI-UC13 | Physical-cyber correlation | P3 |
| SI-UC14 | Threat hunting | P3 |
| SI-UC15–SI-UC20 | Deception, XDR, OT-safe, etc. | P3 |

---

## 5. Functional Requirements

### 5.1 Data Ingestion (FR-DI)

| ID | Requirement | Acceptance Criteria | Priority |
|---|---|---|---|
| FR-DI-01 | Support Redfish, SNMPv2c/v3, ISAPI, syslog ingestion | Each protocol has a poller; traffic is read-only | P1 |
| FR-DI-02 | Normalize to canonical event envelope | 100% of P1 events pass schema validation | P1 |
| FR-DI-03 | Validate required fields per device type | Reject invalid events to DLQ with error classification | P1 |
| FR-DI-04 | Enrich events with asset/CI context | ≥95% enrichment success for P1 sources | P1 |
| FR-DI-05 | Route to ES, PostgreSQL, TimescaleDB | No silent drops; p95 <5s for traps/events, <30s for polling | P1 |
| FR-DI-06 | DLQ handling | Parse-failure and delivery-failure topics with retry policy | P1 |
| FR-DI-07 | Event lineage tracking | Every event has lineage_id; queryable end-to-end | P2 |
| FR-DI-08 | Schema registry with `.avsc` | Backward/forward compatibility checks in CI | P2 |
| FR-DI-09 | Polling controls | Per-class ceiling, circuit breaker, kill switch | P1 |
| FR-DI-10 | Metrics exporter | Prometheus metrics for ingestion health | P2 |

### 5.2 Asset & CMDB (FR-AM)

| ID | Requirement | Acceptance Criteria | Priority |
|---|---|---|---|
| FR-AM-01 | Asset CRUD API | REST endpoints for asset lifecycle | P1 |
| FR-AM-02 | CI CRUD API | REST endpoints for 11 CI types | P1 |
| FR-AM-03 | Relationship & topology | API to query impact graph | P2 |
| FR-AM-04 | Reconciliation engine | Match discovered data to asset/CI; resolve conflicts | P1 |
| FR-AM-05 | Bulk import/export | CSV/JSON; async job | P2 |
| FR-AM-06 | Audit trail | Every change logged with actor, timestamp, before/after | P2 |
| FR-AM-07 | Redis enrichment cache | <50ms enrichment lookup | P2 |
| FR-AM-08 | Identity alias resolution | Deterministic confidence + conflict quarantine | P1 |

### 5.3 Analytics & AI (FR-AI)

| ID | Requirement | Acceptance Criteria | Priority |
|---|---|---|---|
| FR-AI-01 | Time-series store | Kafka → TimescaleDB pipeline operational | P1 |
| FR-AI-02 | Anomaly detection | Ensemble model; >5% anomaly detected ≤15 min | P1 |
| FR-AI-03 | Predictive failure | Alert 24–48 h before critical failure | P1 |
| FR-AI-04 | RCA engine | Causal chain + confidence score | P2 |
| FR-AI-05 | Capacity forecasting | Trend + forecast API | P2 |
| FR-AI-06 | Energy / PUE optimization | PUE drift detection | P2 |
| FR-AI-07 | Model registry | DB-backed registry; active model promotion | P2 |
| FR-AI-08 | LLM/RAG inference | Natural language query over DCIM data | P3 |
| FR-AI-09 | API endpoints | All analytics capabilities exposed via REST | P1 |

### 5.4 Workflow (FR-WF)

| ID | Requirement | Acceptance Criteria | Priority |
|---|---|---|---|
| FR-WF-01 | State machine | 10 states; deterministic transitions | P2 |
| FR-WF-02 | Approval chains | Multi-level approval with timeout and escalation | P1 |
| FR-WF-03 | Runbook engine | Reusable runbook templates | P2 |
| FR-WF-04 | Dry-run mode | Simulate execution without side effects | P1 |
| FR-WF-05 | Blast-radius check | Identify affected CIs before remediation | P2 |
| FR-WF-06 | OT-safe enforcement | No auto-reboot for critical systems | P1 |
| FR-WF-07 | Audit log | Immutable log of every step | P2 |
| FR-WF-08 | Integration with core API | Triggered by canonical events, not ad-hoc webhooks | P1 |

### 5.5 SIEM/SOC (FR-SI)

| ID | Requirement | Acceptance Criteria | Priority |
|---|---|---|---|
| FR-SI-01 | Wazuh ingestion | Agent logs and syslog to Kafka | P1 |
| FR-SI-02 | Correlation engine | 10+ detection rules; Kafka output | P1 |
| FR-SI-03 | Threat-intel lists | CDB lists loaded and updated | P1 |
| FR-SI-04 | SOC API | 12 endpoints for alert/case management | P2 |
| FR-SI-05 | Case management | Create/update/close cases with IRIS | P2 |
| FR-SI-06 | Compliance reporting | CIS benchmark evidence | P3 |
| FR-SI-07 | Kafka → SOAR | `dcim.siem.alerts` topic | P1 |

### 5.6 Dashboard (FR-DB)

| ID | Requirement | Acceptance Criteria | Priority |
|---|---|---|---|
| FR-DB-01 | NOC view | Real-time asset/alert status | P1 |
| FR-DB-02 | SOC view | Security alert triage | P2 |
| FR-DB-03 | Facilities view | UPS, cooling, energy, CCTV | P2 |
| FR-DB-04 | CMDB explorer | Topology and impact graph | P2 |
| FR-DB-05 | SLA/KPI view | Dashboards with drill-down | P3 |
| FR-DB-06 | RBAC | Role-based view permissions | P2 |

---

## 6. Non-Functional Requirements

| ID | Requirement | Target | Priority |
|---|---|---|---|
| NFR-01 | Ingestion uptime | 99.95% | P1 |
| NFR-02 | Security event throughput | 10K EPS (phased 1K→5K→15K) | P2 |
| NFR-03 | Event-to-dashboard latency | p95 <5s for traps/events, <30s for polling | P1 |
| NFR-04 | Anomaly detection latency | ≤15 min | P1 |
| NFR-05 | API response time | p95 <200ms for read APIs | P2 |
| NFR-06 | Data retention | Hot 30d, warm 60d, cold 90d, archive 1y | P2 |
| NFR-07 | Backup/restore | RPO ≤15 min, RTO ≤1h for critical data | P2 |
| NFR-08 | Public repo safety | No credentials, no private IPs, no raw payloads | P1 |
| NFR-09 | CI/CD | All repos run lint/test/security scan on every PR | P1 |
| NFR-10 | Auditability | Every state change immutable, queryable | P1 |

---

## 7. Owner-Confirmed Decisions (2026-07-28)

The open questions below were confirmed by the owner. The table summarizes the decisions; detailed rationale remains under each question.

| ID | Decision | Owner Answer | Status |
|---|---|---|---|
| Q1 | CMDB implementation ([ADR-0007](../adr/0007-cmdb-implementation-for-development.md)) | Custom PostgreSQL CMDB service for Phase 1–2; iTop/NetBox as read-only discovery sources | ✅ Accepted |
| Q2 | Service language/framework ([ADR-0024](../adr/0024-python-fastapi-service-language-baseline.md)) | Python/FastAPI for core services; TypeScript/React for frontend | ✅ Accepted |
| Q3 | SOAR platform ([ADR-0016 addendum](../adr/0016-workflow-engine-split.md)) | TraceCat + Temporal for production SOAR; n8n kept for operational non-destructive workflows | ✅ Accepted |
| Q4 | Safety boundary for automation ([ADR-0025](../adr/0025-automation-execution-preconditions.md)) | Dry-run/recommendation by default; execution requires human approval + maintenance window + blast-radius check | ✅ Accepted |
| Q5 | Satellite repo governance | Keep repos separate for ownership; mandatory CI/CD + contract compatibility gate in each | ✅ Confirmed (cross-repo follow-up) |
| Q6 | iTop vs custom CMDB direction | Refactor ingestion iTop consumer to generic CMDB adapter; iTop as discovery source only | ✅ Confirmed (cross-repo follow-up) |
| Q7 | AI model serving ([ADR-0027](../adr/0027-private-llm-serving-baseline.md)) | Private host on 2×RTX A5000 24 GB VRAM; abstraction layer allows managed-API fallback | ✅ Accepted |
| Q8 | Elasticsearch & technology versions ([ADR-0026](../adr/0026-program-technology-version-baseline.md)) | Elasticsearch 9.x; PostgreSQL 17.x target / 16 floor | ✅ Accepted |
| Q9 | Frontend framework (ADR-0017) | Follow [ADR-0017](../adr/0017-react-noc-dashboard-frontend.md): React + TypeScript + Vite | ✅ Accepted |
| Q10 | Phase 2 scope | Minimal P1 server health → dashboard end-to-end vertical slice | ✅ Confirmed (Phase 2 scope freeze) |

### Q1 — CMDB Implementation
**Question:** Apakah CMDB akan diimplementasikan sebagai (a) thin custom PostgreSQL service, (b) iTop, (c) NetBox, atau (d) hybrid?  
**Why it matters:** OD-01 (sekarang Accepted, [ADR-0007](../adr/0007-cmdb-implementation-for-development.md)) sebelumnya memblokir CI enrichment, topology, dan impact analysis.  
**Recommendation:** Pilih custom PostgreSQL service untuk Phase 1–2 agar aligns dengan B4 reference design; iTop/NetBox sebagai read-only discovery sources.

### Q2 — Service Language / Framework
**Question:** Apakah core services (Asset, CMDB, API, Workflow) ditulis dalam Python/FastAPI, Go, atau TypeScript/NestJS?  
**Why it matters:** OD-07 (sekarang Accepted, [ADR-0024](../adr/0024-python-fastapi-service-language-baseline.md)) sebelumnya menghambat semua service implementation.  
**Recommendation:** Python/FastAPI untuk consistency dengan analytics + ingestion; TypeScript/React untuk frontend (ADR-0017).

### Q3 — SOAR Platform
**Question:** Apakah SOAR tetap di n8n atau dipindahkan ke TraceCat + Temporal sesuai wiki `siem-soar.md`?  
**Why it matters:** Current SOAR repo adalah prototype n8n; wiki mensyaratkan TraceCat + Temporal untuk OT-safe, playbook-as-code, audit. Evidence: `reference-designs/siem-soar.md` vs `SOAR/N8N Workflow/SOAR.json`.  
**Recommendation:** Adopt TraceCat + Temporal untuk production; n8n tetap untuk workflow operational non-destructive jika diharden.

### Q4 — Safety Boundary for Automation
**Question:** Apakah workflow `Automated-Incident-Remediation-Service-Restart` yang melakukan `systemctl restart` via SSH diizinkan, atau harus diubah menjadi read-only recommendation/dry-run?  
**Why it matters:** Ini melanggar `ADR-0005` dan `DEVELOPMENT-BASELINE.md`. Evidence: `n8n-workflows/Automated-Incident-Remediation-Service-Restart/workflows/*.json`.  
**Recommendation:** Ubah menjadi dry-run/recommendation; hanya execute dengan explicit human approval + maintenance window + blast-radius check.

### Q5 — Satellite Repo Governance
**Question:** Apakah komponen satelit (ingestion, AI, workflow, SIEM, SOAR) akan di-merge ke monorepo `dcim-core-platform`, atau tetap sebagai repo terpisah dengan mandatory CI/CD?  
**Why it matters:** Saat ini tidak ada shared gate, version alignment, atau safety boundary.  
**Recommendation:** Tetap terpisah untuk ownership, tetapi setiap repo harus memiliki CI/CD minimal yang sama dengan core (public-safety, lint, test) dan event contract compatibility gate.

### Q6 — iTop vs Custom CMDB Direction
**Question:** Jika custom CMDB dipilih, apakah iTop consumer di ingestion repo (`scripts/dcim_itop_unified_consumer.py`) diubah menjadi CMDB consumer, atau dipertahankan sebagai discovery-only?  
**Why it matters:** Saat ini iTop adalah write target; ini mengunci CMDB ke iTop. Evidence: `DCIM_SRV_DATA_COLLECTION/scripts/dcim_itop_unified_consumer.py` (1399 LOC).  
**Recommendation:** Refactor menjadi generic CMDB adapter yang dapat mengarah ke custom CMDB API; iTop sebagai discovery source.

### Q7 — AI Model Serving
**Question:** Apakah model LLM akan di-host secara private (2×RTX 3070 Ti dengan Ollama/llama.cpp) atau menggunakan managed API? *(hardware final: 2×RTX A5000 24 GB — ADR-0027)*  
**Why it matters:** Hardware sizing dan API design bergantung pada keputusan ini. Evidence: `(MT-023) Private LLM Platform.md` (private host), `api/routers/llm.py` (stub).  
**Recommendation:** Private host untuk data sovereignty; buat abstraction layer sehingga dapat fallback ke managed API jika GPU tidak tersedia.

### Q8 — Elasticsearch Version
**Question:** Wiki target Elasticsearch 8.x, tetapi ingestion menggunakan 9.3.1. Apakah target diupdate ke 9.x atau ingestion diturunkan ke 8.x?  
**Why it matters:** Version drift membuat compatibility dan license review tidak konsisten.  
**Recommendation:** Align ke 9.x jika fitur/security membutuhkan; update wiki reference design.

### Q9 — Frontend Framework
**Question:** Wiki B5 mensyaratkan Vue 3, tetapi core ADR-0017 memilih React + TypeScript + Vite. Mana yang menjadi target?  
**Why it matters:** Tech stack drift menghambat team assignment. Evidence: `reference-designs/block5-web-dashboard.md` vs `docs/adr/0017-react-as-noc-dashboard-frontend.md`.  
**Recommendation:** Ikuti ADR-0017 (React) karena sudah accepted; update wiki B5.

### Q10 — Phase 2 Scope
**Question:** Apakah Phase 2 first vertical slice mencakup (a) end-to-end P1 server health → dashboard, (b) P1+P2 combined, atau (c) hanya foundation evidence consolidation?  
**Why it matters:** Issue #21 masih open dan branch `feat/phase2-first-vertical-slice` berisi 63 commit dalam satu hari. Evidence: GitHub issue #21, `git log --all`.  
**Recommendation:** Scope minimal (a) agar dapat stabil dan di-verify oleh `make preflight`.

---

## 8. Out of Scope (for Current Phase)

- HA/DR multi-site production deployment.
- Autonomous remediation without human approval.
- Production-connected source integration (Dev-Integration-RO gate C-01 still open).
- Hermes agentic AI shadow (OD-05 deferred).
- Cloud-native multi-tenant SaaS.

---

## 9. Dependencies

| PRD Item | Depends On | Decision Status |
|---|---|---|
| Asset/CMDB services | OD-01 | ✅ Confirmed Q1 — custom PostgreSQL CMDB |
| All service code | OD-07 | ✅ Confirmed Q2 — Python/FastAPI |
| SOAR case management | SOAR platform | ✅ Confirmed Q3 — TraceCat + Temporal |
| Auto-remediation | Safety boundary | ✅ Confirmed Q4 — dry-run + approval |
| LLM/RAG API | Model serving | ✅ Confirmed Q7 — private 2×RTX A5000 |
| Web dashboard | Frontend framework | ✅ Confirmed Q9 — React |
| Phase 2 vertical slice | Phase 1 remediation | ✅ Confirmed Q10 — minimal P1 server health slice |

### New Action Items from Confirmation

1. ✅ **Done.** ADR-0007 updated to Accepted with addendum (2026-07-28). See [`docs/adr/0007-cmdb-implementation-for-development.md`](../adr/0007-cmdb-implementation-for-development.md).
2. ✅ **Done.** ADR-0024 created and accepted (2026-07-28). See [`docs/adr/0024-python-fastapi-service-language-baseline.md`](../adr/0024-python-fastapi-service-language-baseline.md).
3. Refactor `DCIM_SRV_DATA_COLLECTION/scripts/dcim_itop_unified_consumer.py` to generic CMDB adapter. **Cross-repo follow-up ticket** (satellite repo `DCIM_SRV_DATA_COLLECTION`, outside core Phase 0 scope; see D-5).
4. Update wiki `reference-designs/block5-web-dashboard.md` and `siem-soar.md` to align with React and TraceCat+Temporal. **Wiki workstream** (separate repo, branches W1/W3).
5. Update technology version matrix (ES 9.x, PostgreSQL 17.x target / 16 minimum floor) in wiki and ingestion repo. **ADR-0026** accepted; wiki update in workstream W2.
6. Document private LLM sizing for 2×RTX A5000 in `(MT-023) Private LLM Platform.md` or equivalent. **ADR-0027** accepted; wiki update in workstream W4; GPU capacity is a Phase 4 item.
7. Freeze Phase 2 scope to P1 server health → dashboard; archive unstable branch commits after rebase. **Phase 2 scope-freeze issue** (to be opened/tracked separately).

---

*Lihat juga: `STATUS-SUMMARY.md`, `GAP-ANALYSIS.md`, `ARCHITECTURE.md`, `IMPLEMENTATION-PLAN.md`, `DECISION-LOG-REVIEW.md`.*
