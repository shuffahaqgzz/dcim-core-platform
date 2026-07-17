# ADR-0005: Dry-Run Automation dan Human Approval

- Status: Accepted
- Date: 2026-07-16
- Owner: shuffahaqgzz

## Context

DCIM alert dapat memicu workflow pada masa depan, tetapi unsafe automation dapat mengganggu network, power, storage, camera, atau server infrastructure.

## Decision

Development automation dibatasi pada notification, ticket draft, approval simulation, recommendation, dan dry-run/mock action. Automation tidak menjalankan infrastructure shell command, privileged SQL, SNMP SET, Redfish/ISAPI write/action, firmware, power/reset, PTZ, network configuration, atau OT action.

Workflow/SOAR tetap menjadi future execution boundary; human approval wajib untuk governed action.

## Consequences

- End-to-end demo membuktikan decision flow dan auditability, bukan autonomous remediation.
- Idempotency, retry, approval, dan failure disposition tetap dapat diuji dengan aman.
- Future action tool memerlukan threat model, ADR, authorization model, dan environment gate terpisah.

## Alternatives

Autonomous remediation dan direct device/OT action ditolak. Manual action di luar platform tidak dianggap capability Development dan tetap mengikuti authority operasional terpisah.

## Security Impact

Menghapus source-to-sink path untuk shell, SQL write, SNMP SET, Redfish/ISAPI write/action, PTZ, firmware, power, dan network control.

## Operational Impact

Demo hanya menunjukkan recommendation, notification, ticket draft, approval simulation, atau dry-run dengan audit trail.

## Revalidation Trigger

Proposal action tool, workflow execution, SOAR integration, privileged identity, atau Production use case.
