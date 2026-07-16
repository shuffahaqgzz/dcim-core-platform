# ADR-0005: Dry-run Automation and Human Approval

- Status: Accepted
- Date: 2026-07-16
- Owner: shuffahaqgzz

## Context

DCIM alerts may eventually trigger workflows, but unsafe automation can disrupt network, power, storage, camera, or server infrastructure.

## Decision

Development automation is limited to notifications, ticket drafts, approval simulations, recommendations, and dry-run/mock actions. It does not execute infrastructure shell commands, privileged SQL, SNMP SET, Redfish/ISAPI writes/actions, firmware, power/reset, PTZ, network configuration, or OT actions.

Workflow/SOAR remains the future execution boundary; human approval is mandatory for governed actions.

## Consequences

- End-to-end demonstrations prove decision flow and auditability, not autonomous remediation.
- Idempotency, retries, approvals, and failure disposition can still be tested safely.
- Future action tools require a separate threat model, ADR, authorization model, and environment gate.
