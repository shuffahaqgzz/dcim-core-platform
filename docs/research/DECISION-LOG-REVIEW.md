# Decision Log Review — DCIM Core Platform Program

**Tanggal:** 2026-07-28  
**Sumber:** `docs/adr/`, `docs/governance/OPEN-DECISIONS.md`, `docs/governance/CONDITIONS-REGISTER.md`, dan audit implementasi 6 repo.

---

## 1. Accepted ADRs

| ID | Title | Status | Decision | Evidence | Impact |
|---|---|---|---|---|---|
| ADR-0001 | Docker Compose Profiles for Development | Accepted | Compose with explicit profiles; separate DEV-BUILD/INTEGRATION-RO/DEMO | `deploy/compose/dev-build/compose.yaml` | Foundation architecture |
| ADR-0002 | Public Code, Private Runtime | Accepted | Code/schemas in Git; live data/credentials outside Git | `DATA-HANDLING.md`, `SECURITY.md` | Public-safety boundary |
| ADR-0003 | Single-Broker Kafka KRaft for Development | Accepted | One Kafka broker in dev-build; conservative retention | `deploy/compose/dev-build/compose.yaml` | Dev-only; HA out of scope |
| ADR-0004 | Pinned Read-Only Integration Plane | Accepted | Connected integration only via manually promoted pinned artifact | `CONDITIONS-REGISTER.md` C-01 | Production integration gate |
| ADR-0005 | Dry-Run Automation and Human Approval | Accepted | Automation limited to notification/recommendation/dry-run; no direct OT/IT control | `DEVELOPMENT-BASELINE.md` | Safety boundary |
| ADR-0006 | Canonical Event Contract and Stable Identity | Accepted | JSON Schema event envelope; UUID asset_id; CI source+native ID | `schemas/*.schema.json` | Integration contract |
| ADR-0008 | Synthetic and Sanitized Demo Data | Accepted | Synthetic default; sanitized snapshot only with approval | `fixtures/synthetic/`, `scripts/sanitize_demo_data.py` | Demo data |
| ADR-0009 | Hermes Read-Only Shadow After Gate | Accepted | Hermes disabled Phase 0; future read-only advisory | `docs/adr/0009-hermes-read-only-shadow-after-gate.md` | AI agent scope |
| ADR-0010 | Solo Development to Multi-Team Handover | Accepted | Solo dev → evidence-backed DEV-APPROVED → handover | `STAGING-HANDOVER.md` | Operating model |
| ADR-0012 | Internal Grafana Development Access | Accepted | Grafana only on internal observability network | `deploy/compose/dev-build/compose.yaml` | Access control |
| ADR-0013 | Derived Hardened Foundation Images | Accepted | Local dev-only derived images; immutable inputs; SBOM | `deploy/compose/derived-images/` | Foundation image gate |
| ADR-0014 | Official Release Binary and Source Provenance | Accepted | Pinned official binaries + checksum verification | `deploy/compose/images.json` | Supply chain |
| ADR-0015 | Full-Source Prometheus gRPC Remediation | Accepted | Build Prometheus from source to remove High finding | `deploy/compose/derived-images/prometheus/Dockerfile` | Security gate |
| ADR-0016 | Workflow Engine Split | Accepted | n8n general; Temporal durable core; Tracecat security workflows | `services/workflow/README.md` | Workflow stack |
| ADR-0017 | React as NOC Dashboard Frontend | Accepted | React + TypeScript + Vite; TanStack Query; types from schemas | `web/README.md` | Frontend stack |
| ADR-0018 | Elasticsearch as Development Search Platform | Accepted | Elasticsearch single-node; API-only; license recorded | `deploy/compose/dev-build/compose.yaml` | Search platform |
| ADR-0019 | Apache-2.0 Repository License | Accepted | Repository under Apache-2.0; runtime licenses independent | `LICENSE`, `NOTICE` | Publication |
| ADR-0020 | Identity Alias and Conflict Resolution | Accepted | Deterministic confidence + validity; quarantine on conflict | `schemas/asset.schema.json`, `schemas/ci.schema.json` | Identity model |
| ADR-0021 | Foundation Resource Limits, Retention, and Disk Watermarks | Accepted | Kafka 30d retention; 85/90/95% watermarks; per-service caps | `docs/adr/0021-foundation-resource-limits.md` | Resource governance |
| ADR-0023 | Connector Polling and Source-Impact Controls | Accepted | Conservative polling ceilings; breaker; kill switch | `docs/adr/0023-connector-polling-controls.md` | Source protection |
| ADR-0007 | Custom PostgreSQL CMDB for Development (OD-01) | Accepted 2026-07-28 | Custom PostgreSQL CMDB service for Phase 1–2; iTop/NetBox as read-only discovery sources | `docs/adr/0007-cmdb-implementation-for-development.md` | CMDB implementation |
| ADR-0024 | Python/FastAPI Service Language Baseline (OD-07) | Accepted 2026-07-28 | Python 3.12 + FastAPI + Pydantic v2 for core services; TypeScript/React for frontend | `docs/adr/0024-python-fastapi-service-language-baseline.md` | Service stack |
| ADR-0025 | Automation Execution Preconditions | Accepted 2026-07-28 | Dry-run default; five conjunctive execution preconditions required | `docs/adr/0025-automation-execution-preconditions.md` | Safety boundary |
| ADR-0026 | Program Technology Version Baseline | Accepted 2026-07-28 | ES 9.x; PG 17.x target / 16 floor; Kafka per ADR-0003; Redis 7 | `docs/adr/0026-program-technology-version-baseline.md` | Version alignment |
| ADR-0027 | Private LLM Serving Baseline | Accepted 2026-07-28 | Private host on 2×RTX A5000 24 GB VRAM; managed-API fallback abstraction | `docs/adr/0027-private-llm-serving-baseline.md` | AI serving |
| ADR-0016 addendum 2026-07-28 | SOAR Platform Roles (Q3) | Accepted 2026-07-28 | TraceCat + Temporal for SOAR; n8n non-destructive operational only | `docs/adr/0016-workflow-engine-split.md` | SOAR stack |

---

## 2. Deferred Decisions

### OD-05 — Hermes Model / Inference

| Attribute | Detail |
|---|---|
| **Decision** | Hermes AI agent shadow |
| **Status** | DEFERRED |
| **Implication** | No Hermes work in dev-v0.1.0 |
| **Next Step** | Revisit after Phase 2 |

> OD-01 (CMDB), OD-02 (Workflow), OD-03 (Frontend), OD-04 (Search), OD-06 (License), OD-07 (Service Language) are now accepted. See §1 Accepted ADRs above.

---

## 3. Conditional-GO Register (C-01 … C-10)

| ID | Condition | Status | Blocks | Evidence | Next Step |
|---|---|---|---|---|---|
| C-01 | Source authorization | OPEN | First DEV-INTEGRATION-RO activation | `CONDITIONS-REGISTER.md` | Owner authorizes private source record outside Git |
| C-02 | Public-repo safety | CLOSED 2026-07-20 | — | `docs/phase0/phase0-checklist.md` | Maintain; re-scan on every change |
| C-03 | Plane separation | OPEN | Structural separation accepted; negative-promotion test still needed | `CONDITIONS-REGISTER.md` | Add negative test for DEV-BUILD → INTEGRATION-RO promotion |
| C-04 | Read-only credentials | OPEN | Private credential record outside Git | `CONDITIONS-REGISTER.md` | Define credential record format; audit ingestion + workflow repos |
| C-05 | Demo data | OPEN | Executable demo path | `CONDITIONS-REGISTER.md` | Create `deploy/compose/demo/compose.yaml` |
| C-06 | Identity aliases | OPEN | Deterministic collision tests | `CONDITIONS-REGISTER.md` | Link collision tests as evidence; close after Phase 2 |
| C-07 | Resource limits | OPEN | Compose caps + load evidence | `CONDITIONS-REGISTER.md` | Update `compose.yaml` to match ADR-0021; run load evidence |
| C-08 | Hermes | DEFERRED | — | `OPEN-DECISIONS.md` | Revisit after Phase 2 |
| C-09 | Connector polling controls | OPEN | Connector policy schema + stop test | `CONDITIONS-REGISTER.md` | Add policy schema and source-impact stop test |
| C-10 | Cost ceiling | DEFERRED | — | `OPEN-DECISIONS.md` | Revisit at staging |

---

## 4. Decisions Implied by Wiki but Not in Core ADRs (Resolved 2026-07-28)

| Topic | Wiki Reference Design | Owner Decision | Status |
|---|---|---|---|
| SOAR platform | TraceCat + Temporal | TraceCat + Temporal for production; n8n for operational non-destructive workflows | ✅ [ADR-0016 addendum](../adr/0016-workflow-engine-split.md) |
| Frontend framework | Vue 3 | Follow ADR-0017: React + TypeScript + Vite | ✅ [ADR-0017](../adr/0017-react-noc-dashboard-frontend.md) |
| Elasticsearch version | 8.x | Align to 9.x across the program | ✅ [ADR-0026](../adr/0026-program-technology-version-baseline.md) |
| PostgreSQL version | 16 | PostgreSQL 17.x as program target; 16 as minimum floor (ingestion currently 15) | ✅ [ADR-0026](../adr/0026-program-technology-version-baseline.md) |
| LLM serving | Ollama / llama.cpp private | Private host on 2×RTX A5000 24 GB VRAM; managed-API fallback allowed via abstraction layer | ✅ [ADR-0027](../adr/0027-private-llm-serving-baseline.md) |
| SIEM output | Kafka `dcim.siem.events` | Implement Wazuh → Kafka producer; keep reference design | ✅ [ADR-0016](../adr/0016-workflow-engine-split.md) |
| Safety boundary | Read-only/dry-run automation | Dry-run/recommendation default; execution requires human approval + maintenance window + blast-radius check | ✅ [ADR-0025](../adr/0025-automation-execution-preconditions.md) |
| Satellite repo governance | Monorepo vs separate | Keep separate; mandatory CI/CD + contract compatibility gate per repo | ✅ Confirmed (cross-repo) |
| iTop consumer role | CMDB write target | Refactor to generic CMDB adapter; iTop as discovery source | ✅ [ADR-0007](../adr/0007-cmdb-implementation-for-development.md) |

### Wiki Update Backlog

> Wiki is a separate repo/workstream: `https://github.com/shuffahaqgzz/dcim-wiki/`. Links below are absolute URLs; no repo-relative links into the wiki.

- [ ] Update [siem-soar.md](https://github.com/shuffahaqgzz/dcim-wiki/blob/master/reference-designs/siem-soar.md) to reflect TraceCat + Temporal + n8n non-destructive role (workstream W3).
- [ ] Update [block5-web-dashboard.md](https://github.com/shuffahaqgzz/dcim-wiki/blob/master/reference-designs/block5-web-dashboard.md) from Vue 3 to React (workstream W1).
- [ ] Update [block1-infrastructure-provisioning.md](https://github.com/shuffahaqgzz/dcim-wiki/blob/master/reference-designs/block1-infrastructure-provisioning.md) to ES 9.x and PostgreSQL 16 floor (workstream W2).
- [ ] Update [block7-analytics-ai-engine.md](https://github.com/shuffahaqgzz/dcim-wiki/blob/master/reference-designs/block7-analytics-ai-engine.md) with 2×RTX A5000 private LLM sizing (workstream W4).

---

## 5. Decision Workflow Recommended

```
Owner Decision Required
        │
        ▼
┌───────────────────┐
│ Is it a durable   │
│ architecture/data │
│ choice?           │
└─────────┬─────────┘
          │
     Yes /│\ No
         │ \
         │  ▼
         │  Update existing ADR or close
         │
         ▼
Draft new ADR → Momus review → Owner approve
         │
         ▼
Update IMPLEMENTATION-PLAN, GAP-ANALYSIS, PRD
         │
         ▼
Implement → evidence → gate
```

---

## 6. Close Conditions per Open Decision

### OD-01 Close Conditions
- [x] Owner selects one option (custom/iTop/NetBox/hybrid) — **Confirmed custom PostgreSQL**.
- [x] ADR-0007 updated to Accepted (addendum 2026-07-28).
- [x] `services/cmdb/README.md` replaced with scaffold.
- [ ] Ingestion `iTop` consumer refactored to generic CMDB adapter; iTop as discovery source. *(Cross-repo follow-up: satellite repo `DCIM_SRV_DATA_COLLECTION`, Phase 1+.)*

### OD-07 Close Conditions
- [x] Owner selects language/framework — **Confirmed Python/FastAPI + TypeScript/React**.
- [x] New ADR created — [ADR-0024](../adr/0024-python-fastapi-service-language-baseline.md) accepted 2026-07-28.
- [x] Service template created in `services/` (scaffolds committed).
- [ ] CI scaffold updated for Python/FastAPI. *(Cross-repo: CI wiring is a Phase 1+ task.)*

### C-01 Close Conditions
- [ ] Private source authorization record created outside Git.
- [ ] Template in `docs/templates/private-source-authorization-register.template.md` filled.
- [ ] Owner signs off.

### C-04 Close Conditions
- [ ] All hardcoded credentials removed from public repos (verified by scan).
- [ ] Runtime credential record defined (Vault / Docker secrets / env).
- [ ] Rotation plan executed for exposed credentials.

### C-07 Close Conditions
- [ ] `deploy/compose/dev-build/compose.yaml` updated to ADR-0021 caps.
- [ ] `foundation_policy.py` passes.
- [ ] Load evidence collected (e.g., `make foundation-smoke`).

### C-09 Close Conditions
- [ ] Connector policy schema committed to `schemas/` or `contracts/`.
- [ ] Source-impact stop test implemented and passing.

---

## 7. Recommendations for Decision Governance

1. **Decision lockdown completed 2026-07-28.** OD-01, OD-07, dan PRD Q1–Q10 confirmed by owner.
2. **Reconcile wiki with core ADRs.** Execute the wiki update backlog in §4; wiki and core ADRs must converge before Phase 2 implementation.
3. **Do not let AI agents make architecture decisions.** Hermes/Synthetic Test dapat men-generate draft ADR, tetapi owner approval harus manusia.
4. **Close decisions with evidence, not just documents.** Setiap decision ditutup dengan test/code/config yang mengimplementasikannya.
5. **Publish a decision matrix.** Buat `docs/research/DECISION-MATRIX.md` yang mencakup semua open/wip decisions, owner, deadline, dan status.

---

*Lihat juga: `STATUS-SUMMARY.md`, `GAP-ANALYSIS.md`, `ARCHITECTURE.md`, `PRD.md`, `IMPLEMENTATION-PLAN.md`, `DELIVERY-VELOCITY-ANALYSIS.md`, `RISK-REGISTER.md`.*
