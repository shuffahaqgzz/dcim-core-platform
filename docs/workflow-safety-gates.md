# Workflow Safety Gates

This design doc specifies the safety gate model for workflow automation in the DCIM Core Platform. It implements [ADR-0005](adr/0005-dry-run-automation.md) (dry-run automation, human approval), [ADR-0025](adr/0025-automation-execution-preconditions.md) (five conjunctive execution preconditions), and the [ADR-0016 addendum](adr/0016-workflow-engine-split.md) (TraceCat+Temporal = SOAR path; n8n non-destructive only). The [Automation Safety Boundary](security/automation-safety-boundary.md) remains the authoritative policy; this doc defines the gate implementation model.

Engines: n8n (general, non-destructive only), Temporal (durable pipeline), TraceCat (SOAR/security). All engines stay in dry-run mode until Phase 6.

## Gate stages

Every workflow run passes through five ordered stages. Failure at any stage halts the run.

**Stage 1: Dry-run default.** All workflows default to producing notifications, ticket drafts, recommendations, or mock actions only. This is the **only available mode** in Phases 0 through 5.

**Stage 2: Recommendation.** The engine computes a recommended action set with blast-radius declaration and rollback plan per step. No action executes. The recommendation is advisory only.

**Stage 3: Approval.** A named human approver explicitly authorizes execution. Approval alone is insufficient; all five ADR-0025 preconditions must hold simultaneously.

**Stage 4: Execution window.** The approved run must occur inside an active, time-bounded maintenance window. Window bounds are checked at execution time, not only at approval time. Expired or unopened windows block the run.

**Stage 5: Post-check.** After execution, the system validates expected vs. actual outcome, rollback status, and audit record completeness. A failed post-check triggers the kill-switch escalation path.

## Blast-radius declaration

Every execution-proposing workflow must produce a blast-radius report before action proceeds:

| Field | Description |
|---|---|
| affected_cis | CI IDs impacted by the proposed action |
| impact_scope | single-CI, service-group, site-wide, platform-wide |
| dependency_chain | CIs transitively dependent on the affected set |
| estimated_blast_duration | Expected impact duration |
| blast_radius_confidence | high, medium, low (based on dependency graph completeness) |

The report is immutable once generated. Incomplete dependency graphs must be flagged in the confidence field and acknowledged by the approver.

## Rollback specification

Every executable step must have a paired rollback action documented and linked in the run plan. A step without a rollback rejects the workflow entirely (ADR-0025 precondition 4).

Requirements: per-step rollback (global-only is not sufficient), tested in dry-run before approval, automatic trigger on step failure with outcome recorded, manual trigger available during the execution window, all rollback attempts recorded in the immutable audit record.

## Audit record fields

Every run reaching Stage 2 or beyond generates an immutable, append-only, tamper-evident audit record:

| Field | Description |
|---|---|
| run_id | Unique workflow run identifier |
| workflow_id | Workflow definition identifier |
| engine | n8n, Temporal, TraceCat |
| trigger | alert, manual, scheduled, API |
| dry_run | Boolean: true if dry-run mode |
| recommendation | Recommended action set from Stage 2 |
| blast_radius | Blast-radius report reference |
| approval | Approver identity, timestamp, conditions (null if dry-run) |
| maintenance_window | Window ID, start, end (null if dry-run) |
| steps | Ordered step list, each with rollback link |
| outcome | Per-step and overall: success, partial, failed, rolled-back |
| post_check | pass, fail, partial |
| prohibited_class_rejected | Prohibited operation class and rejection reason, if attempted |
| kill_switch_triggered | Boolean; if true, includes escalation details |
| created_at | UTC ISO 8601 timestamp |
| tamper_evidence | Hash chain or equivalent mechanism |

The record is written **before** execution begins (ADR-0025 precondition 5). Outcome fields are appended after execution. No field may be deleted or overwritten after creation.

## Kill-switch escalation

If a workflow bypasses or exceeds the safety boundary, or if a post-check fails:

1. **Immediate halt.** Execution window closed; in-progress steps terminated.
2. **Disable offending path.** Workflow suspended; no further runs until root cause identified.
3. **Revoke over-privileged identity.** Compromised credentials revoked.
4. **Preserve audit metadata.** Private audit data preserved outside Git, following the [Emergency Collector Kill Switch](security/emergency-collector-kill-switch.md) stop sequence.
5. **Reopen after owner approval.** Reactivation requires root cause analysis, negative tests, and explicit owner approval.

Escalation applies to all engines equally.

## Prohibited operation classes

**Permanently prohibited regardless of approval**, per ADR-0005, ADR-0025, and the Automation Safety Boundary:

- SNMP SET
- Redfish / ISAPI write or action methods
- power / reset actions
- firmware updates or flashing
- PTZ (pan-tilt-zoom) camera control
- network configuration changes
- raw shell execution against infrastructure
- privileged SQL execution

A workflow containing a prohibited operation class is rejected even if all five preconditions are satisfied. The rejection is recorded in the audit record.

## Negative tests required

Each gate stage must have negative tests proving it blocks execution when its precondition is missing:

- execute without approval → blocked
- execute outside the maintenance window → blocked
- execute without a documented rollback plan → blocked
- execute a prohibited operation class → blocked regardless of all other preconditions

## Conditions advanced

This doc advances [C-09](governance/CONDITIONS-REGISTER.md) (connector polling/source-impact controls) and [C-04](governance/CONDITIONS-REGISTER.md) (read-only credentials, negative write tests). No condition is marked CLOSED.

## Status

- **Phase 1 (current):** Design-only. No executable gate code exists.
- **Phase 6 (future):** Enforcement. The safety layer (policy gate service, dry-run simulator, approval service, rollback orchestrator, append-only audit store) is designed, accepted, and tested. Execution capability is gated behind this layer.
- **Phases 0 through 5:** Dry-run is the only mode. No workflow may mutate infrastructure state.
