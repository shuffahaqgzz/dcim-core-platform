# Risk Register — DCIM Core Platform Program

**Tanggal:** 2026-07-28  
**Skor:** Likelihood (1–5) × Impact (1–5) = Risk Score (1–25).  
**Threshold:** ≥15 = high, ≥20 = critical.

---

## 1. Critical Risks (Score ≥ 20)

| ID | Risk | Likelihood | Impact | Score | Evidence | Owner | Mitigation | Status |
|---|---|---|---|---|---|---|---|---|
| R-CR-01 | Hardcoded credentials di repo publik menyebabkan unauthorized access atau credential leak | 5 | 5 | 25 | 20+ scripts ingestion, workflow JSON, `vault/config/` | Security Lead | Rotasi segera; pindah ke Vault/Docker secrets; CI public-safety scan; audit Git history | Open |
| R-CR-02 | n8n workflow mengeksekusi write actions (restart service, decommission, firewall delete) tanpa safety guardrail, menyebabkan outage | 4 | 5 | 20 | `n8n-workflows/Automated-Incident-Remediation-Service-Restart/workflows/*.json`, `Server-Hyper-V-Decommissioning/workflows/*.json` | Workflow Lead | Suspend workflow; implement safety execution layer; dry-run + approval + blast-radius + rollback | Open |
| R-CR-03 | OD-01 (CMDB) dan OD-07 (language/framework) previously blocked service development | 1 | 4 | 4 | [ADR-0007](../adr/0007-cmdb-implementation-for-development.md) and [ADR-0024](../adr/0024-python-fastapi-service-language-baseline.md) accepted 2026-07-28; service READMEs remain implementation backlog | Product Owner/Architect | ~~Lock decisions within 1 week; update ADRs; communicate to team.~~ **[COMPLETED]** Implement service work against the accepted ADRs. | Closed |
| R-CR-04 | Foundation remediation and owner disposition can delay completion of the delivered Phase 2 vertical slice | 2 | 4 | 8 | Issue #20 and #21 remain open; synthetic Phase 2 evidence and `phase2-check` were delivered 2026-08-02 | Tech Lead | Close #20 with minimal verified scope; obtain owner disposition for #21; retain the delivered P1/P2 slice as the baseline | Mitigated |

---

## 2. High Risks (Score 15–19)

| ID | Risk | Likelihood | Impact | Score | Evidence | Owner | Mitigation | Status |
|---|---|---|---|---|---|---|---|---|
| R-HI-05 | Tidak ada CI/CD di satelit repo → bug dan security exposure mencapai main tanpa gate | 5 | 3 | 15 | `.github/workflows/` missing di ingestion, AI, workflow, SIEM, SOAR | DevOps Lead | Add CI minimal: public-safety, lint, unit test, schema validation | Open |
| R-HI-06 | Single author per satelit repo → bus factor rendah dan review quality rendah | 4 | 3 | 12 | `git log` per repo | Engineering Manager | Pair assignment; mandatory PR review; cross-team rotation | Open |
| R-HI-07 | AI agents (Hermes/Synthetic Test) menghasilkan artifact tanpa accountability → churn dan rework | 4 | 3 | 12 | 21/27 wiki commits by Hermes; 98/165 core commits by Synthetic Test; 19 handoff docs | Tech Lead | Limit AI agent to non-decision tasks; require human review for architecture/requirements changes | Open |
| R-HI-08 | Version and technology drift antara wiki, core, ingestion, AI menyebabkan integration conflict | 4 | 3 | 12 | ES 8.x vs 9.3.1; Vue 3 vs React; TraceCat vs n8n; v4.6.1 vs v4.5.2 vs v3.5.5 | Architect | Technology decision matrix; alignment ADRs; update wiki reference designs | Open |
| R-HI-09 | SIEM/SOAR stub tidak dapat memenuhi acceptance criteria; security visibility gap | 4 | 4 | 16 | SIEM 6 files, 2 commits; SOAR 3 files, 6 commits; no Kafka output | Security Lead | Rebuild with proper Wazuh→Kafka→TraceCat stack; atau scope down to integration-only | Open |
| R-HI-10 | API analytics banyak stub → AI/ML tidak terintegrasi ke dashboard/workflow | 4 | 3 | 12 | `api/routers/*.py` return 501; `llm/models/` empty | AI Lead | Prioritize API endpoints; define model artifact storage; stub → implementation | Open |
| R-HI-11 | Data ingestion pipeline tidak memiliki integration test → silent drops atau schema drift tidak terdeteksi | 4 | 4 | 16 | Only 1 test file (`test_circuit_breaker.py`); no pipeline tests | QA Lead | Add integration tests for poller → Kafka → normalizer → ES/PG/TSDB | Open |
| R-HI-12 | Private IP addresses dan internal topology bocor di repo publik | 4 | 3 | 12 | Private IP references in ingestion commits and configs | Security Lead | Public-safety scan; remove/rewrite history; rotate where possible | Open |

---

## 3. Medium Risks (Score 8–14)

| ID | Risk | Likelihood | Impact | Score | Evidence | Owner | Mitigation | Status |
|---|---|---|---|---|---|---|---|---|
| R-ME-13 | Resource limits di core Compose tidak sesuai ADR-0021 | 3 | 2 | 6 | `deploy/compose/dev-build/compose.yaml` vs `ADR-0021` | Tech Lead | Update Compose; policy test | Open |
| R-ME-14 | NiFi flows disimpan sebagai binary gzip → tidak dapat direview | 3 | 3 | 9 | `nifi/flow.json.gz` | Ingestion Lead | Export flows as XML/JSON; version control; review process | Open |
| R-ME-15 | AI agent framework (`ai_agent/`) detached dari pipeline | 3 | 2 | 6 | `ai_agent/README.md` empty; no integration found | AI Lead | Integrate atau archive | Open |
| R-ME-16 | Documentation drift: wiki tidak sinkron dengan code | 3 | 3 | 9 | 201 archived files, 10 superseded arch docs | Wiki Lead | Lock wiki after Phase 2; update only after code changes | Open |
| R-ME-17 | Demo path tidak executable | 3 | 2 | 6 | `deploy/compose/demo/README.md` only | Tech Lead | Create demo compose profile | Open |
| R-ME-18 | Dependabot PRs unmerged | 3 | 1 | 3 | PR #17, #18 open | Tech Lead | Review/merge atau dismiss | Open |

---

## 4. Low Risks (Score ≤ 7)

| ID | Risk | Likelihood | Impact | Score | Evidence | Owner | Mitigation | Status |
|---|---|---|---|---|---|---|---|---|
| R-LO-19 | License dispositions perlu diperbarui setiap kali base image berubah | 2 | 2 | 4 | `deploy/compose/derived-images/license-dispositions.json` | Tech Lead | Pin image; automate SBOM diff | Open |
| R-LO-20 | Markdown link drift di wiki | 2 | 1 | 2 | 148 pages; manual wikilinks | Wiki Lead | Periodic lint; no action critical | Open |

---

## 5. Risk Heat Map

```
Impact
  5 │  R-CR-01          R-CR-02  R-CR-03  R-CR-04
    │  R-HI-09
  4 │  R-HI-11          R-HI-12
    │  R-HI-05  R-HI-10
  3 │  R-HI-06  R-HI-07  R-HI-08
    │  R-ME-14  R-ME-16
  2 │  R-ME-13  R-ME-15  R-ME-17
    │
  1 │  R-LO-19  R-LO-20
    └────────────────────────────────────────────
      1   2   3   4   5
              Likelihood
```

---

## 6. Risk Trends

- **R-CR-01** harus ditangani sebelum repo publik digunakan lebih luas; setiap hari tertunda meningkatkan exposure.
- **R-CR-02** dan **R-CR-04** saling terkait: Phase 1 tidak stabil karena Phase 2 juga tidak jelas, dan workflow berbahaya terus aktif.
- **R-HI-05** adalah enabler risk: tanpa CI, risiko credential/safety tidak akan terdeteksi otomatis.

---

## 7. Recommended Risk Response Strategy

| Risk | Strategy | Priority |
|---|---|---|
| R-CR-01 | Avoid (remove secrets) + Mitigate (rotate + scan) | P0 |
| R-CR-02 | Avoid (suspend) + Mitigate (safety layer) | P0 |
| R-CR-03 | Avoid (decide now) | P0 |
| R-CR-04 | Mitigate (scope lock + rebase) | P0 |
| R-HI-05 | Mitigate (CI/CD) | P1 |
| R-HI-09 | Mitigate (rebuild) atau Accept (scope down) | P1 |
| R-HI-11 | Mitigate (tests) | P1 |
| R-HI-12 | Mitigate (public-safety scan + history rewrite) | P1 |
| R-HI-06 | Mitigate (pair/review) | P2 |
| R-HI-07 | Mitigate (human review gates) | P2 |
| R-HI-08 | Mitigate (decision matrix) | P2 |
| R-HI-10 | Mitigate (API implementation) | P2 |

---

*Lihat juga: `STATUS-SUMMARY.md`, `GAP-ANALYSIS.md`, `ARCHITECTURE.md`, `PRD.md`, `IMPLEMENTATION-PLAN.md`, `DELIVERY-VELOCITY-ANALYSIS.md`, `DECISION-LOG-REVIEW.md`.*
