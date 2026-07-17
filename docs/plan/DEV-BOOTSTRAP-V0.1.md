# Dev Platform Bootstrap v0.1 — 10-Day Task Plan

This plan converts the kickoff baseline into an executable owner-led Development sequence. Estimates assume one developer using Codex for bounded implementation/review support; they are not a promise of full product completion.

## Definition of Done

- all major component boundaries have a build/deploy placeholder or implementation, health contract, observability hook, version record, and smoke test;
- one synthetic P1 and one synthetic P2 flow run end-to-end without silent loss;
- invalid data reaches DLQ/quarantine with reason and disposition;
- valid data receives deterministic Asset/CI context;
- NOC view exposes health, freshness, capacity, and data quality;
- workflow produces draft/dry-run output only; SIEM/SOAR receives a sanitized test event;
- backup/restore and clean-machine rebuild pass;
- required P1 conditions for the claimed scope are closed;
- release candidate has public-safe evidence and handover material.

## Day-by-day plan

| Day | Work package | Key tasks | Acceptance/evidence |
|---:|---|---|---|
| 1 | Repository and governance | Merge safety bootstrap; enable ruleset/security settings; create issue/ADR workflow; establish external runtime directories; close or evidence C-02 | CI/secret/dependency checks pass; no secret in history; owner records repo settings |
| 2 | Compose foundation | Design profiles and project separation; pin image versions/digests; define networks/volumes/health checks/resource limits; no source cut-in | `docker compose config` and synthetic foundation smoke; resource/retention assumptions documented |
| 3 | Stateful core and observability | PostgreSQL, Redis if justified, single-broker KRaft, Prometheus/Grafana; migrations and telemetry | health checks, metrics, disk-watermark alerts, PostgreSQL dump/restore test |
| 4 | Read-only connector framework | Connector SDK/contract; synthetic Redfish/SNMP adapters; allowlists, timeouts, retries, rate ceilings, kill switch; negative writes | synthetic success/failure tests; prohibited operation tests; no live target |
| 5 | Canonical ingestion contract | JSON event envelope, validation, normalization, dedupe/idempotency, lineage, DLQ/quarantine and replay policy | valid/invalid contract suite; zero silent-drop test; reason/disposition evidence |
| 6 | Asset and CMDB context | Stable Asset/CI identity, aliases, validity/confidence, collision handling, persistence and APIs | identity/collision/alias tests; migration/rollback evidence; OD-01 remains explicit if implementation choice unresolved |
| 7 | Analytics and NOC presentation | Capacity/health analytic baseline; freshness and data-quality metrics; API and NOC dashboard slice | synthetic P1/P2 visibility; measured p95 method/results; no unsupported AI claim |
| 8 | Workflow and SIEM/SOAR smoke | Notification/ticket draft/approval simulation/dry-run; sanitized event forwarding contract; idempotency and audit | duplicate/retry tests; no direct execution path; sanitized receiving evidence |
| 9 | Hermes gate, security and recovery | Read-only Hermes shadow policy/eval or defer; threat-model update; dependency/license/SBOM review; recovery/kill-switch drills | C-08 evidence or explicit deferral; no external data egress; restore and stop tests pass |
| 10 | Integrated acceptance and release candidate | clean rebuild; E2E P1/P2; load/latency window; review findings; limitations; tag/handover readiness | all mandatory gates pass; public-safe evidence complete; owner decides `DEV-APPROVED` and `dev-v0.1.0` eligibility |

## Workstream dependencies

```text
Repo safety/governance
  └─> Compose foundation
       ├─> stateful core/observability
       └─> read-only connector framework
             └─> canonical ingestion/DLQ
                    └─> Asset/CMDB context
                           ├─> analytics/NOC view
                           └─> workflow + SIEM/SOAR
                                  └─> Hermes gate/recovery
                                         └─> integrated release evidence
```

## GitHub issue structure

Use one epic plus focused issues small enough for one pull request:

- EPIC: Dev Platform Bootstrap v0.1;
- P1 conditions C-01 through C-05;
- repository settings and CI hardening;
- Compose profile design;
- stateful platform and recovery;
- connector framework and one P1/P2 simulator;
- event contract/DLQ;
- Asset/CI identity;
- analytics/NOC slice;
- workflow/SIEM dry-run;
- Hermes gate;
- integrated acceptance and handover;
- one issue per unresolved ADR.

## Daily Codex loop

1. Select one issue with explicit acceptance criteria.
2. Ask `architect` to map design/risks and list missing decisions.
3. Owner approves or adjusts the plan.
4. Ask `implementer` for the smallest coherent change and tests.
5. Run local checks; ask `reviewer` and `security_reviewer` in parallel for non-trivial changes.
6. Resolve findings and run `make preflight` plus component gates.
7. Ask `evidence_writer` to produce a public-safe summary.
8. Open/update the PR; owner reviews and squash-merges only after checks pass.

## Release naming

- Development candidate branches remain normal feature branches.
- Owner may tag the evidence-backed milestone `dev-v0.1.0`.
- Do not create `v1.0`, `stable`, `production`, or SLA-bearing labels during this milestone.
