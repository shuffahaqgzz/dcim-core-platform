# Architecture — DCIM Core Platform Program

**Tanggal:** 2026-07-28  
**Scope:** Arsitektur target (sesuai `dcim-wiki` B1–B9) vs arsitektur aktual (dari 6 repo implementasi).  
**Notasi:** Diagram Mermaid (text-based) untuk version control dan review.

---

## 1. Target Architecture (Reference Design B1–B9)

### 1.1 Logical Blocks

| Block | Nama | Fungsi utama | Teknologi target |
|---|---|---|---|
| B1 | Infrastructure Provisioning | Foundation runtime: DB, cache, message bus, data flow, search, monitoring, secret management | PostgreSQL 16, Redis 7, Kafka 3.x KRaft, NiFi 1.x, Elasticsearch 8.x, Prometheus, Grafana, Vault, Docker Compose/K8s |
| B2 | Data Ingestion & Integration | Gateway semua data masuk: protocol adapters, normalizer, validator, DLQ, lineage | NiFi, Kafka, Schema Registry, Avro |
| B3 | Asset Repository | SSOT aset fisik, finansial, kontrak | PostgreSQL, CRUD API, Redis cache, bulk import |
| B4 | CMDB | SSOT Configuration Items, relationships, topology, impact | PostgreSQL, topology engine, reconciliation |
| B5 | Web Dashboard | NOC/SOC/Facilities/CMDB/SLA/Logs/Tasks views | Vue 3, Pinia, ECharts, Tailwind, WebSocket |
| B6 | SIEM/SOC | Security event ingestion, correlation, incident response, compliance | Wazuh, Elasticsearch, correlation engine, SOC API |
| B7 | Analytics & AI Engine | Time-series, anomaly detection, predictive maintenance, RCA, capacity, energy, LLM/RAG | TimescaleDB, scikit-learn, Prophet, LSTM, Ollama/llama.cpp, QLoRA |
| B8 | Workflow Automation | State machine, approval, runbook, remediation, escalation | n8n, Temporal |
| B9 | External Integrations | Adapter framework: ITSM, ERP, DMS, NMS, cloud | ServiceNow, Jira, SAP, Oracle, AWS, GCP, Azure |

### 1.2 Target Component Diagram

```mermaid
flowchart TB
    subgraph Sources["Source Systems"]
        S1[Redfish Servers]
        S2[SNMP UPS / NAS / Network]
        S3[ISAPI CCTV/NVR]
        S4[Wazuh Agents / Syslog]
        S5[ITSM / ERP / DMS / Cloud]
    end

    subgraph B2["B2 Data Ingestion & Integration"]
        NIFI[Apache NiFi]
        KAFKA[Apache Kafka]
        SR[Schema Registry]
        NORM[Normalizer]
        VAL[Validator]
        DLQ[Dead Letter Queue]
        LINEAGE[Lineage Tracker]
    end

    subgraph B1["B1 Infrastructure"]
        PG[(PostgreSQL)]
        REDIS[(Redis)]
        ES[(Elasticsearch)]
        TS[(TimescaleDB)]
        VAULT[HashiCorp Vault]
        PROM[Prometheus]
        GRAF[Grafana]
    end

    subgraph B3B4["B3 Asset Repository + B4 CMDB"]
        AR[Asset Repository API]
        CMDB[CMDB API / Topology]
    end

    subgraph B7["B7 Analytics & AI Engine"]
        AD[Anomaly Detection]
        PM[Predictive Maintenance]
        RCA[RCA Engine]
        CAP[Capacity Forecasting]
        ENE[Energy Optimization]
        LLM[LLM/RAG Inference]
    end

    subgraph B8["B8 Workflow Automation"]
        WF[Workflow Engine n8n/Temporal]
        SM[State Machine]
    end

    subgraph B6["B6 SIEM/SOC"]
        WAZ[Wazuh Manager]
        COR[Correlation Engine]
        SOC[SOC API]
    end

    subgraph B5["B5 Web Dashboard"]
        UI[Vue 3 Frontend]
        GW[API Gateway]
    end

    subgraph B9["B9 External Integrations"]
        ADAPTER[Adapter Framework]
    end

    S1 -->|HTTPS GET| NIFI
    S2 -->|SNMP GET/WALK| NIFI
    S3 -->|ISAPI HTTP| NIFI
    S4 -->|Syslog| NIFI
    S5 -->|REST| ADAPTER

    NIFI -->|dcim.raw.*| KAFKA
    KAFKA --> NORM
    NORM -->|dcim.normalized.events| KAFKA
    KAFKA --> VAL
    VAL -->|failed| DLQ
    VAL -->|ok| KAFKA
    KAFKA --> LINEAGE

    KAFKA -->|enriched events| ES
    KAFKA -->|metrics| TS
    KAFKA --> PG
    KAFKA --> AR
    KAFKA --> CMDB

    AR --> CMDB
    CMDB -->|topology| B7

    TS --> AD
    AD --> PM
    AD --> RCA
    TS --> CAP
    TS --> ENE
    TS --> LLM

    AD -->|alerts| KAFKA
    COR -->|alerts| KAFKA

    KAFKA --> WF
    WF -->|approved remediation| B9
    WF -->|notifications| UI

    WAZ --> COR
    COR --> SOC
    SOC --> WF

    UI --> GW
    GW --> AR
    GW --> CMDB
    GW --> B7
    GW --> B8
    GW --> SOC

    VAULT -.->|secrets| NIFI
    VAULT -.->|secrets| B7
    VAULT -.->|secrets| WF

    PROM -->|metrics| GRAF
```

### 1.3 Target Data Flow (Telemetry Path)

```mermaid
sequenceDiagram
    participant D as Device
    participant N as NiFi ExecuteProcess
    participant KR as Kafka Raw Topic
    participant NR as Normalizer
    participant KN as Kafka Normalized Topic
    participant ER as Enrichment
    participant KE as Kafka Enriched Topic
    participant ES as Elasticsearch
    participant PG as PostgreSQL
    participant TS as TimescaleDB
    participant AI as Analytics Engine

    D->>N: Poll / trap
    N->>KR: JSON event
    KR->>NR: consume
    NR->>KN: Avro NormalizedEvent
    KN->>ER: consume
    ER->>KE: Avro EnrichedEvent
    KE->>ES: index
    KE->>PG: lineage / CI
    KE->>TS: metrics
    TS->>AI: train / infer
    AI->>KE: anomaly alert
```

### 1.4 Target Event Topics

| Topic | Format | Producer | Consumers | Purpose |
|---|---|---|---|---|
| `dcim.raw.*` | JSON | NiFi / pollers | Normalizer | Raw telemetry |
| `dcim.normalized.events` | Avro | Normalizer | ES consumer, SQL consumer, enrichment, analytics bridge | Normalized + validated |
| `dcim.enriched.events` | Avro | Enrichment | ES, SQL, analytics bridge | Enriched with asset/CI context |
| `dcim.analytics.metrics` | JSON | Analytics bridge | Stream processor | AI-ready metrics |
| `dcim.siem.events` | JSON | Wazuh | Correlation engine | Security events |
| `dcim.siem.alerts` | Avro | Correlation engine | SOAR | Security alerts |
| `dcim.dlq.*` | Raw | Normalizer / iTop consumer | DLQ consumer | Parse/delivery failures |
| `dcim.nvr.*` | Avro/JSON | NVR connectors | Asset Repository | NVR discovery/health/events |

---

## 2. As-Is Architecture (Actual Implementation)

### 2.1 Component Distribution Across Repos

```mermaid
flowchart LR
    subgraph Core["dcim-core-platform"]
        C_SCHEMA[Schemas]
        C_COMPOSE[Dev Compose]
        C_TESTS[Tests]
        C_GOV[Governance]
        C_SVC[Service placeholders]
    end

    subgraph Ingestion["DCIM_SRV_DATA_COLLECTION"]
        I_NIFI[NiFi]
        I_KAFKA[Kafka 3-node]
        I_SR[Schema Registry]
        I_POLL[Redfish/SNMP/ISAPI pollers]
        I_NORM[Normalizer]
        I_ES[Elasticsearch]
        I_PG[PostgreSQL]
        I_TS[TimescaleDB]
        I_VAULT[Vault]
        I_PROM[Prometheus]
        I_GRAF[Grafana]
        I_ITOP[iTop consumer]
    end

    subgraph AI["dcim_project"]
        A_API[FastAPI skeleton]
        A_ANOM[Anomaly service]
        A_RCA[RCA engine]
        A_REG[Model registry]
        A_FT[QLoRA fine-tune]
        A_BENCH[Benchmarks]
    end

    subgraph WF["n8n-workflows"]
        W_RESTART[Service Restart]
        W_DECOM[Decommission]
    end

    subgraph SIEM["SIEM"]
        S_WAZ[Wazuh stub]
        S_RULE[2 custom rules]
    end

    subgraph SOAR["SOAR"]
        SO_N8N[n8n prototype]
    end

    C_SCHEMA -->|copied manually| I_KAFKA
    I_NIFI --> I_KAFKA
    I_POLL --> I_NIFI
    I_KAFKA --> I_NORM
    I_NORM --> I_KAFKA
    I_KAFKA --> I_ES
    I_KAFKA --> I_PG
    I_KAFKA --> I_TS
    I_KAFKA --> I_ITOP
    I_TS --> A_ANOM
    A_ANOM --> A_API
    I_PROM --> I_GRAF
    W_RESTART -->|ssh systemctl restart| I_POLL
    W_DECOM -->|iTop CMDB| I_ITOP
    W_DECOM -->|prometheus.yml edit| I_PROM
    S_WAZ -.->|Shuffle webhook| SO_N8N
```

### 2.2 As-Is Data Flow

Per the ingestion repo README:

```
Device → NiFi ExecuteProcess → Kafka Raw (JSON) → dcim-normalizer →
Kafka Normalized (Avro) → NiFi Enrichment + FastAPI → Kafka Enriched (Avro) →
Elasticsearch / PostgreSQL / TimescaleDB
```

AI bridge consumes `dcim.analytics.metrics` into TimescaleDB.

### 2.3 As-Is Integration Contracts

| Contract | Status | Mechanism | Evidence |
|---|---|---|---|
| Event envelope | ⚠️ Schema file exists in core, but not enforced in ingestion | Manual copy | `schemas/event-envelope.schema.json` vs `src/schemas/avro_schemas.py` |
| Kafka topic names | ✅ Mostly consistent | Conventional naming | `src/skills/telemetry/normalizer/executor.py` |
| Avro schema registry | ⚠️ Container exists, no `.avsc` files | Python string registration | `schema-registry/docker-compose.yml`, `src/schemas/avro_schemas.py` |
| REST API between services | ❌ Not defined | — | — |
| Core → Workflow trigger | ❌ Not defined | Grafana webhook / n8n form | `n8n-workflows/*.json` |
| SIEM → SOAR | ⚠️ Shuffle webhook ad-hoc | Wazuh `<integration>` | `SIEM/wazuh-manager/ossec.conf` |
| Analytics ↔ CMDB | ❌ Not defined | Direct PG queries | `implementation/dcim_ai_v2_rag/llm/dataset_generator.py` |

---

## 3. Architecture Gap: Target vs As-Is

### 3.1 What is Implemented

- **B1 Infrastructure:** Mostly implemented in `DCIM_SRV_DATA_COLLECTION` (Kafka, NiFi, PostgreSQL, ES, TimescaleDB, Prometheus, Grafana, Vault containers). Core platform memiliki `dev-build` compose yang lebih ketat (no host ports, pinned images, SBOM).
- **B2 Data Ingestion:** Pipeline operational untuk 5 protokol, 49 devices. Normalizer, lineage, DLQ, circuit breaker ada.
- **B7 Analytics:** Anomaly detection, RCA, model registry, dataset generator, benchmark scripts.
- **B8 Workflow Automation:** n8n workflows untuk restart service dan decommission server.
- **B6 SIEM:** Stub Wazuh custom rules.

### 3.2 What is Missing

- **B3 Asset Repository:** No service code.
- **B4 CMDB:** No service code; decision accepted (OD-01, [ADR-0007](../adr/0007-cmdb-implementation-for-development.md)).
- **B5 Web Dashboard:** No frontend code.
- **B6 SIEM:** Correlation engine, Kafka output, agent deployment, 450K threat-intel lists.
- **B7 Analytics:** API endpoints banyak stub, LLM/RAG inference, capacity/energy, forecasting, fine-tuned weights.
- **B8 Workflow:** State machine formal, runbook engine, dry-run/rollback, OT-safe enforcement, core platform contract.
- **B9 External:** Adapter framework hanya iTop.
- **SOAR:** TraceCat/Temporal, deployable Wazuh config, containment playbooks.

### 3.3 Mismatch Diagram

```mermaid
flowchart TB
    subgraph Target["Target (Confirmed 2026-07-28)"]
        T1[9 complete blocks]
        T2[TraceCat + Temporal SOAR + n8n non-destructive]
        T3[React + TypeScript Dashboard]
        T4[Custom PostgreSQL CMDB + Asset Services]
        T5[OT-safe automation]
        T6[Adapter framework 10 connectors]
    end

    subgraph Actual["As-Is (Repos)"]
        A1[Ingestion pipeline v4.6.1]
        A2[Analytics skeleton]
        A3[n8n workflows with writes]
        A4[SIEM stub]
        A5[SOAR prototype]
        A6[Core platform foundation only]
    end

    T1 -.->|gaps| A1
    T2 -.->|gaps| A5
    T3 -.->|gaps| A6
    T4 -.->|gaps| A6
    T5 -.->|violated| A3
    T6 -.->|gaps| A1
```

---

## 4. Security & Safety Architecture

### 4.1 Target Safety Boundary (Confirmed 2026-07-28)

Sesuai `ADR-0005` dan `DEVELOPMENT-BASELINE.md`, dengan owner confirmation:

- **Default mode is dry-run / recommendation.** Any automation first produces a simulated impact report.
- **Direct OT/IT control** (service restart, power reset, VM deletion, firewall change, CMDB status update) is allowed only after explicit human approval + maintenance window + blast-radius check + rollback plan.
- Read-only source connectors only.
- Secrets live outside Git (Vault / Docker secrets / environment).
- Immutable audit trail for every step.

### 4.2 As-Is Safety Boundary

| Layer | Target | As-Is | Status |
|---|---|---|---|
| Source connectors | Read-only GET/WALK | ✅ Read-only | ✅ OK |
| Automation | Default dry-run; execution only with approval + window + blast-radius + rollback | ❌ Direct `systemctl restart`, VM export, firewall rule deletion, CMDB status update, Prometheus reload | ❌ Violation |
| Secrets | Outside Git | ❌ Hardcoded passwords/tokens in repo | ❌ Violation |
| Approval | Explicit human approval for destructive actions | ⚠️ Decommission has Gmail approval; restart has none | ❌ Partial |
| Dry-run / rollback | Required | ❌ Absent | ❌ Violation |
| Audit trail | Immutable for every step | ❌ Absent | ❌ Violation |

### 4.3 Safety Architecture Diagram

```mermaid
flowchart LR
    subgraph SafeZone["Safe Zone (core platform)"]
        CORE[Core Platform]
        GATE[Policy Gate]
        DRY[Dry-run Simulator]
        AUDIT[Audit Log]
    end

    subgraph DangerZone["Current Workflow Repos"]
        WF1[Service Restart]
        WF2[Decommission]
        WF3[SOAR prototype]
    end

    CORE -->|event / alert| GATE
    GATE -->|approved + dry-run OK| DRY
    DRY -->|simulated impact| AUDIT
    DRY -.->|actual execution| WF1
    DRY -.->|actual execution| WF2
    WF1 -->|ssh systemctl restart| INFRA[Infrastructure]
    WF2 -->|CMDB update obsolete| CMDB
    WF2 -->|firewall rule delete| FW
    WF2 -->|prometheus.yml edit| MON
```

The dashed lines from Dry-run to actual execution represent the current missing safety layer.

---

## 5. Deployment Topology

### 5.1 Target Environments

Sesuai `reference-designs/staging-production-environment.md`:

```
┌─────────────────────────────────────────────────────────┐
│                    Management VLAN                       │
│  (CI/CD, Bastion, Admin Tools, Vault)                   │
└─────────────────────────────────────────────────────────┘
        │
┌───────┴────────┐  ┌──────────────┐  ┌────────────────────┐
│   Staging      │  │  Production  │  │   DMZ / Sources    │
│ (isolated)     │  │  (isolated)  │  │ (devices, SNMP,      │
│                │  │              │  │  Redfish, ISAPI)     │
└────────────────┘  └──────────────┘  └────────────────────┘
```

### 5.2 As-Is Environment

- Ingestion repo menyebutkan RFC1918 private IP addresses sebagai production endpoints di file konfigurasi dan commit history.
- Workflow repo melakukan SSH langsung ke RFC1918 private IP addresses untuk update CMDB, monitoring, dan firewall.
- Core platform `dev-build` compose hanya internal Docker network, no host ports.

**Gap:** Tidak ada transisi yang jelas dari `dev-build` internal ke staging/production; private IP addresses dari production sudah bocor di repo publik.

---

## 6. Network & Data Classification

Sesuai `DATA-HANDLING.md` core platform:

| Classification | Allowed in Git | Examples | Current Issue |
|---|---|---|---|
| Public | ✅ | Code, schemas, ADRs, synthetic fixtures | OK |
| Internal | ❌ | Hostnames, topology, device serials | Private IPs committed in ingestion + SIEM |
| Confidential | ❌ | Credentials, tokens, API keys | Hardcoded passwords/tokens |
| Restricted | ❌ | Raw payloads, logs, captures | Some logs in `_archived/` |

---

## 7. Integration Patterns

### 7.1 Target: Canonical Event Bus

Semua komponen berkomunikasi melalui Kafka dengan Avro + Schema Registry.

### 7.2 As-Is: Hybrid Point-to-Point

| Path | Pattern | Issue |
|---|---|---|
| Device → Ingestion | NiFi ExecuteProcess | OK |
| Ingestion → Analytics | Kafka → TimescaleDB | OK |
| Ingestion → CMDB | Kafka → custom CMDB API | ❌ Currently Kafka → iTop write consumer |
| Monitoring → Workflow | Grafana webhook | Ad-hoc, no contract |
| Wazuh → SOAR | Shuffle webhook | Ad-hoc, private IP |
| Workflow → Core | None | Silo |
| Core → Workflow | None | Silo |

---

## 8. Technology Stack Alignment

| Layer | Confirmed Target | Actual Ingestion | Actual AI | Actual Core | Gap |
|---|---|---|---|---|---|
| DB | PostgreSQL 17.x (16 minimum floor) | PostgreSQL 15 (`postgres:15-alpine`) | PostgreSQL 12+ | PostgreSQL 17.10 in dev-build | Ingestion must upgrade to 17; AI ≥16 acceptable for Phase 0 |
| Cache | Redis 7 | Redis used | Redis used | Redis not yet in dev-build | Add Redis to dev-build |
| Kafka | 3.x KRaft | 3.7.0 KRaft 3-node | Kafka used | Single broker dev-build | HA gap (dev stays single) |
| NiFi | 1.x | Custom NiFi image | — | — | OK |
| ES | 9.x | 9.3.1 | — | — | Update wiki to 9.x |
| TSDB | TimescaleDB | `latest-pg15` | — | — | OK |
| Monitoring | Prometheus + Grafana | ✅ | ✅ Prometheus | ✅ | OK |
| Vault | HashiCorp Vault | ✅ container | — | External runtime root | Secrets still in repo |
| Frontend | React + TypeScript + Vite (ADR-0017) | — | — | React (ADR-0017) | Implement `web/` |
| Workflow | TraceCat + Temporal for durable/SOAR; n8n for operational non-destructive (ADR-0016 addendum) | n8n only | — | n8n/Temporal (ADR-0016) | Add Temporal/TraceCat |
| SIEM | Wazuh + ES 9.x (ADR-0026) | Stub Wazuh | — | — | Not integrated |
| SOAR | TraceCat + Temporal | n8n prototype | — | — | Replace with TraceCat+Temporal |
| LLM | Private Ollama/llama.cpp on 2×RTX A5000 24 GB (ADR-0027) | Ollama/llama.cpp | Ollama/llama.cpp | — | Size GPU sizing doc; abstraction layer |

---

## 9. API & Contract Strategy

### 9.1 Target API Groups

| Service | API Group | Example Endpoints |
|---|---|---|
| Asset Repository | `/api/v1/assets` | CRUD, bulk import, search |
| CMDB | `/api/v1/cis` | CRUD, topology, impact |
| Analytics | `/api/v1/analytics` | anomaly, predictions, rca, capacity, energy, models |
| Workflow | `/api/v1/workflows` | create, execute, approve, state |
| SIEM/SOC | `/api/v1/soc` | alerts, cases, correlation |
| Dashboard | `/api/v1/dashboard` | views, widgets, real-time |

### 9.2 As-Is API

- AI repo: FastAPI skeleton dengan router `/api/v1/analytics/anomalies`, `/predictions`, `/rca`, `/capacity`, `/energy`, `/models`, `/llm` — banyak stub `501`.
- Ingestion: FastAPI enrichment API (`src/skills/inventory/enrichment/executor.py`) 129 LOC.
- Workflow: webhook n8n, bukan REST API yang konsisten.
- Core: belum ada service.

---

## 10. Architecture Actions (Confirmed Decisions Applied)

1. **Adopt canonical event bus.** Jadikan `dcim-core-platform/schemas/*.schema.json` source of truth; generate `.avsc` dan AsyncAPI contract; buat CI gate yang memastikan ingestion + analytics + SIEM/SOAR mematuhi contract.
2. **Implement core services in Python/FastAPI.** Confirmed OD-07 ([ADR-0024](../adr/0024-python-fastapi-service-language-baseline.md)). Buat template service di `services/`; gunakan TypeScript/React untuk `web/`.
3. **Implement custom PostgreSQL CMDB service.** Confirmed OD-01 / Q1 ([ADR-0007](../adr/0007-cmdb-implementation-for-development.md)). Refactor ingestion iTop consumer menjadi generic CMDB adapter; iTop/NetBox sebagai discovery source.
4. **Replace SOAR platform.** Confirmed Q3 ([ADR-0016 addendum](../adr/0016-workflow-engine-split.md)). Pindahkan dari n8n prototype ke TraceCat + Temporal; n8n tetap untuk operational non-destructive workflows.
5. **Implement safety execution layer.** Confirmed Q4 ([ADR-0025](../adr/0025-automation-execution-preconditions.md)). Letakkan policy gate / dry-run simulator; semua write action memerlukan approval + maintenance window + blast-radius check + rollback + audit log.
6. **Align technology versions.** Confirmed Q8 ([ADR-0026](../adr/0026-program-technology-version-baseline.md)). Target matrix: PostgreSQL 17.x (program target; 16 minimum floor for satellite components; core dev-build pinned `postgres:17.10-bookworm`), Elasticsearch 9.x, Kafka 3.x, Redis 7. Update wiki reference designs.
7. **Size private LLM for 2×RTX A5000.** Confirmed Q7 ([ADR-0027](../adr/0027-private-llm-serving-baseline.md)). Update `(MT-023) Private LLM Platform.md` dengan VRAM 24 GB per GPU dan abstraction layer untuk managed-API fallback.
8. **Define environment promotion path.** Pisahkan `dev-build` (core) → `integration-ro` → `demo` → staging → production dengan network/VLAN boundary; hapus semua private IP dari repo.

---

*Lihat juga: `STATUS-SUMMARY.md`, `GAP-ANALYSIS.md`, `PRD.md`, `IMPLEMENTATION-PLAN.md`, `RISK-REGISTER.md`, `DECISION-LOG-REVIEW.md`.*
