# ADR-0025: Automation Execution Preconditions

- Status: Accepted
- Date: 2026-07-28
- Owner: shuffahaqgzz
- Decision source: owner confirmation 2026-07-28 (docs/research/PRD.md §7 Q4)
- Related ADRs: ADR-0005 (extended), ADR-0016 (workflow engines)

## Context

ADR-0005 limited Development automation to notification, ticket draft, approval
simulation, recommendation, and dry-run/mock action. PRD Q4 confirmed the
owner's direction: the `Automated-Incident-Remediation-Service-Restart` n8n
prototype that performs `systemctl restart` via SSH in the satellite repo is a
policy violation, not an accepted execution path. The owner requires a formal
precondition model before any execution capability is added, while keeping the
current platform strictly in dry-run/recommendation mode.

This ADR **extends** ADR-0005; it does not supersede it. ADR-0005 remains
Accepted and unmodified.

## Decision drivers

- Prevent accidental autonomous remediation in a public repository that models
  infrastructure management.
- Make execution so hard to enable that it cannot be triggered by a single
  missing check or a UI default.
- Preserve the satellite repo n8n prototype as a hardening target rather than
  a working execution path.
- Align the acceptance evidence with the safety gate: a passing test must prove
  the control actually blocks execution.
- Keep the decision boundary at the Phase 6 safety layer, so Phases 0–5 do not
  build a half-enabled execution path.

## Decision

### 1. Default mode only

The DCIM Core Platform automation layer currently operates in **dry-run /
recommendation mode only**. A workflow may produce notifications, ticket drafts,
approval simulations, recommendations, and mock actions. It may **not** mutate
infrastructure state. This is the **only** automation mode available in the
repository today.

### 2. Future execution requires all five preconditions simultaneously

Any future execution path must satisfy **all five** preconditions at the same
time (conjunctive, not disjunctive). A single missing precondition blocks
execution:

1. **Explicit human approval with recorded actor.** A named human approver must
   authorize the run, and the approver identity must be recorded in the
   immutable audit record.
2. **Active maintenance window.** The run must fall inside an approved,
   time-bounded maintenance window whose bounds are checked at execution time,
   not only at approval time.
3. **Blast-radius report on affected CIs.** The system must compute and display
   the set of Configuration Items affected by the action before the action is
   allowed to proceed.
4. **Documented rollback action per step.** Every executable step must have a
   paired rollback action documented and linked in the run plan; the workflow
   must be rejected if any step lacks a rollback.
5. **Immutable audit record.** The planned action, preconditions, approval,
   window, blast-radius, rollback links, and outcome must be written to an
   append-only, tamper-evident audit record before execution.

### 3. Execution capability is gated behind the Phase 6 safety layer

Execution-capable code, identity providers, maintenance-window services,
blast-radius engines, rollback orchestrators, and append-only audit stores may
not be introduced into the repository before the Phase 6 safety layer is
designed, accepted, and tested. Phases 0–5 remain recommendation-only.

### 4. Satellite n8n prototype remains suspended

The n8n `systemctl restart` prototype workflow in the satellite repository
remains suspended. It may be reactivated only after it is hardened to this
standard: the five preconditions, the prohibited-operation classes below, and the
negative-test evidence required by this ADR.

### 5. Prohibited operation classes remain prohibited regardless of approval

Even when all five preconditions are met, the following operation classes are
permanently prohibited in the DCIM Core Platform automation layer:

- SNMP SET
- Redfish / ISAPI write or action methods
- power / reset actions
- firmware updates or flashing
- PTZ (pan-tilt-zoom) camera control
- network configuration changes
- raw shell execution against infrastructure
- privileged SQL execution

### 6. ADR-0005 remains authoritative

This ADR extends ADR-0005. ADR-0005 stays Accepted and is not superseded,
amended, or retired by this decision.

## Options considered

### 1. Allow execution with one or two preconditions (rejected)

A disjunctive model (e.g., "approval OR maintenance window") would let a
single compromised control enable real action. Rejected.

### 2. Allow execution now and add controls later (rejected)

Adding the execution code before the safety layer would create an enabled
attack path while the controls are still absent. Rejected.

### 3. Keep execution suspended until all five preconditions are implemented
  and tested (selected)

Selected by owner direction. The model is strict, verifiable, and keeps the
platform in the safe dry-run state until the safety layer is explicitly built
and accepted.

## Security impact

The prohibited-operation classes remove device/OT control paths from the
automation layer. The five-precondition model ensures that even if one control
fails, execution cannot proceed. The immutable audit record provides
non-repudiation and supports incident investigation.

## License impact

No new dependency is introduced by this decision. Existing workflow engines are
governed by their own ADRs (ADR-0016).

## Resource and operational impact

No additional runtime resources are required for Phase 0. The five
preconditions will require dedicated services in Phase 6: approval service,
maintenance-window service, blast-radius engine, rollback orchestrator, and
append-only audit store. These are intentionally deferred to keep Development
lightweight and safe.

## Migration and rollback

The current platform is already in dry-run/recommendation mode, so no migration
is needed. The satellite n8n `systemctl restart` prototype is suspended; its
rollback path is to remain in recommendation mode or to harden to this standard.
No execution state exists to roll back.

## Acceptance evidence

- Owner marks this ADR Accepted.
- Negative tests demonstrate that execution is blocked when any precondition is
  missing:
  - execute without approval → blocked;
  - execute outside the maintenance window → blocked;
  - execute without a documented rollback → blocked.
- Negative tests demonstrate that each prohibited operation class is rejected
  even if the five preconditions are otherwise satisfied.
- The satellite n8n prototype is recorded as suspended in the safety boundary
  documentation.

## Revalidation triggers

- Proposal to add any execution capability.
- Proposal to reduce, bypass, or make disjunctive any of the five preconditions.
- Proposal to remove or narrow a prohibited operation class.
- Proposal to move the execution gate earlier than Phase 6.
- Change in the workflow engine set (ADR-0016).
