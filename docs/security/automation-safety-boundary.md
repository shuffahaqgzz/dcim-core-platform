# Automation Safety Boundary

DCIM Core Platform automation layer is advisory only in Phases 0–5. No workflow may mutate infrastructure state. This policy implements [ADR-0005](../adr/0005-dry-run-automation.md) and extends it through [ADR-0025](../adr/0025-automation-execution-preconditions.md).

## Default automation modes

The only currently available automation modes are:

- notification
- recommendation
- ticket draft
- approval simulation
- dry-run / mock action

**Dry-run / recommendation is the default mode.** Every workflow defaults to producing advice, notifications, or simulated output. Execution capability is not available.

## Execution preconditions

Any future execution path requires **all five preconditions simultaneously**. A single missing precondition blocks the run.

1. **Explicit human approval with recorded actor.** A named human approver must authorize the run, and the approver identity must be recorded in the immutable audit record.
2. **Active maintenance window.** The run must occur inside an approved, time-bounded maintenance window. The window bounds are checked at execution time, not only at approval time.
3. **Blast-radius report on affected CIs.** The system must compute and present the set of affected Configuration Items before the action proceeds.
4. **Documented rollback action per step.** Every executable step must have a paired rollback action documented in the run plan. A step without a rollback rejects the workflow.
5. **Immutable audit record.** The planned action, preconditions, approval, window, blast-radius, rollback links, and outcome must be written to an append-only, tamper-evident audit record before execution.

## Prohibited operation classes

The following operation classes are **prohibited regardless of approval**:

- SNMP SET
- Redfish / ISAPI write or action methods
- power/reset actions
- firmware updates or flashing
- PTZ (pan-tilt-zoom) camera control
- network configuration changes
- raw shell execution against infrastructure
- privileged SQL execution

## Enforcement expectations

The safety layer is planned for Phase 6. Expected controls:

- policy gate service
- dry-run simulator
- approval service
- rollback stubs / orchestrator
- append-only audit store

No execution capability may exist in the repository before the Phase 6 safety layer is designed, accepted, and tested.

## Required negative tests

Execution must be blocked when any precondition is missing:

- execute without approval → blocked
- execute outside the maintenance window → blocked
- execute without a documented rollback plan → blocked

Each prohibited operation class must be rejected even if the five preconditions are otherwise satisfied.

## Escalation and stop path

If a workflow attempts to bypass or exceed this boundary, follow the [Emergency Collector Kill Switch](emergency-collector-kill-switch.md) stop sequence: disable the offending path, revoke any over-privileged identity, preserve private audit metadata outside Git, and reopen only after root cause, negative tests, and owner approval are complete.

## Phase 0 scope

Phase 0 documents the boundary and ships **no executable control**. The satellite n8n `systemctl restart` prototype workflow remains suspended until it is hardened to this standard.
