---
name: dcim-baseline
description: Use for planning or implementing any DCIM Core Platform change so work stays aligned with the accepted Development baseline, scope, gates, and open conditions. Do not use to override an explicit newer owner decision.
---

# DCIM Development Baseline

1. Read `docs/baseline/DEVELOPMENT-BASELINE.md`, `docs/governance/CONDITIONS-REGISTER.md`, `docs/governance/OPEN-DECISIONS.md`, and affected ADRs.
2. Classify the task as foundation, ingestion, Asset/CMDB, analytics, workflow, SIEM/SOAR, dashboard/API, Hermes, or handover.
3. State which Development acceptance criteria and conditions it advances.
4. Keep the milestone interpretation narrow: deployable, health-checked, observable, smoke-tested, plus one integrated P1/P2 vertical slice. Do not infer full feature completion, HA, SLA, hardening, or Production readiness.
5. For Production-connected source work, require written authorization, dedicated read-only identity, restricted network/egress, polling limits, sanitization, kill switch, and negative tests for write methods.
6. For automation or AI, permit advisory/draft/dry-run behavior only. Workflow/SOAR remains the execution boundary.
7. Finish with tests, evidence, limitations, and condition-status updates.
