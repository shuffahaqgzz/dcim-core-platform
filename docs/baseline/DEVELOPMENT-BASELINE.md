# DCIM Core Platform — Sanitized Development Baseline v0.4

Date: 2026-07-16  
Status: owner-input consolidated  
Development owner: `shuffahaqgzz`  
Entry recommendation: **CONDITIONAL GO**  
Maturity: **prototype/alpha**

This is the public-safe repository interpretation of the latest kickoff/grill-me decisions. Private source inventories, authorizations, endpoint details, topology, and operational evidence remain outside Git.

## 1. Operating model

**Solo Development → Controlled Handover → Multi-Team Staging → Governed Production**

The Development owner can mark evidence-backed work `DEV-APPROVED`. That decision is not Staging entry or Production authorization. Staging requires named Product/Architecture, Platform/SRE, Data/Integration, Security, QA/UAT, and relevant domain owners.

## 2. Development objective

Deliver a **Dev Platform Bootstrap v0.1** that proves:

- all major components can be built, started in a compact single-VM profile, health-checked, observed, and smoke-tested;
- at least one P1 flow and one P2 flow pass source/simulator → normalize → validate → DLQ/quarantine where invalid → enrich → Asset/CI context → persist → analyze/workflow → NOC view;
- no accepted event is silently dropped;
- invalid payloads receive an explicit reason and disposition;
- backup/restore and clean-machine rebuild are demonstrated;
- every claim is supported by reproducible, public-safe evidence.

The 10-day target does **not** mean full functional completion, HA, SLA, hardening, complete connector breadth, or Production readiness for every module.

## 3. Component breadth

1. Infrastructure/Foundation.
2. Data Ingestion & Integration.
3. Asset Repository.
4. CMDB.
5. Analytics & AI baseline.
6. Workflow Automation in draft/dry-run mode.
7. SIEM/SOAR smoke integration.
8. Web Dashboard/API presentation.
9. Hermes read-only shadow after the pipeline gate.

## 4. Development environment

- Ubuntu Server 24.04 VM.
- 32 vCPU, 64 GB RAM, 500 GB SSD.
- 24 GB VRAM GPU.
- 1 Gbps network.
- Docker Compose with profiles for Development.
- Kubernetes deferred unless parity becomes an explicit Development acceptance criterion; otherwise it belongs to Staging planning.

## 5. Platform baseline

- PostgreSQL as transactional system of record.
- Redis where short-lived cache/coordination is justified.
- Kafka single-broker KRaft for Development only, with conservative retention and disk watermarks.
- Prometheus/Grafana for observability.
- NOC-oriented Web Dashboard/API for health, freshness, capacity, and data-quality visibility.
- Candidate ingestion/orchestration technologies and deeper product choices remain governed by ADRs.

A single-broker Development setup has no HA, durability, or Production claim.

## 6. Source and environment boundary

Office/Production telemetry is an approved exception only after the linked conditions are closed. The required logical planes are:

1. **DEV-BUILD / SIMULATION** — mutable code, synthetic fixtures, no office route.
2. **DEV-INTEGRATION-RO** — pinned artifacts, dedicated read-only identities, restricted network/egress, private runtime storage, manually promoted.
3. **DEV-DEMO** — synthetic or explicitly approved sanitized snapshots only.

Every connector requires written source authorization/classification, a least-privilege read identity, allowlisted methods, rate/poll limits, source-impact monitoring, an immediate kill switch, sanitization, and negative tests that prove write/control operations are unavailable.

P1 candidates include server health, UPS alarm, and network availability. P2 candidates include network utilization, storage capacity, and camera/NVR health unless risk classification elevates them. Exact sources are private and separately governed.

## 7. Canonical data contract

External/API contracts use JSON Schema. Kafka may use Avro internally only with a documented, versioned mapping.

The minimum event envelope includes:

- unique event ID;
- UTC event timestamp and observation timestamp;
- source identity and source instance alias;
- event type and P1/P2/P3 priority;
- correlation ID;
- payload;
- enrichment and lineage/validation metadata.

### Identity rules

- Asset primary identity: native UUID; fallback manufacturer plus serial number.
- CI primary identity: source system plus native device ID/UUID.
- Hostname, FQDN, and IP are aliases with validity periods, source confidence, and collision handling.
- IP is never a stable primary key.

## 8. Quality and latency targets

- Accepted-event schema integrity: 100%.
- Silent drops: zero.
- P1 completeness: at least 99% in the measured test window.
- Enrichment success: at least 95% in the measured test window.
- Every DLQ/quarantine record has a reason and disposition.
- P1 event-to-dashboard p95: under 5 seconds for traps/events and under 30 seconds for polling feeds.

The test window, workload, clock source, percentile method, and exclusions must be recorded with the result.

## 9. Automation and AI boundary

Development workflow may produce notifications, ticket drafts, approval simulations, recommendations, and dry-run/mock actions. It must not perform shell execution against infrastructure, raw SQL against connected systems, SNMP SET, Redfish/ISAPI writes, network/power changes, firmware actions, PTZ control, or OT actions.

Hermes is read-only, non-blocking, and advisory. It enters only after pipeline stability and must have an approved allowlist, audit trail, egress/memory policy, resource limits, and kill switch. Workflow/SOAR remains the execution boundary; human approval remains mandatory for future governed actions.

## 10. Public repository boundary

Public: generic code, schemas, synthetic fixtures, sanitized examples/docs/evidence, templates, and public-safe architecture.

Private: real endpoint/identity/topology data, credentials, community strings, raw payloads/logs/captures/dumps, production screenshots, operational prompts, certificates/keys/tokens, and source authorization records.

GitHub Actions uses synthetic data and GitHub-hosted runners only. A runner connected to an office/Production network is deferred and requires a separate design and approval.

## 11. Mandatory Development gates

- formatting/lint;
- unit tests;
- schema/contract tests;
- integration tests;
- at least one synthetic E2E path;
- secret/public-safety scan;
- dependency and license review;
- database migration check;
- evidence log;
- PostgreSQL dump/restore test;
- pinned dependencies and reproducible clean-machine build.

A critical failure is **NO-GO**.

## 12. Development exit

The target exit package includes tag `dev-v0.1.0`, reproducible build/images, source catalog references, schemas, ADRs, test/security/recovery evidence, security boundary, known limitations, deployment/rollback runbook, and `STAGING-HANDOVER.md`.

The condition register remains the authoritative list of prerequisites and stop conditions for the current milestone.
