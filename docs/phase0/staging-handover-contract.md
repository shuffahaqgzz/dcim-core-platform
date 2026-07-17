# Staging Handover Contract

Future Staging handover memerlukan named Product/Architecture, Platform/SRE, Data/Integration, Security, QA/UAT, dan domain owners. `DEV-APPROVED` bukan Staging approval.

Deliverables minimum:

- reproducible images dengan immutable digest dan provenance;
- versioned deployment manifests/config templates tanpa secret;
- versioned schemas/API dan compatibility policy;
- migration, rollback, clean rebuild, backup/restore, serta measured recovery evidence;
- unit/contract/integration/E2E, performance, security, dependency/license, dan public-safety evidence;
- masked/sanitized data approval serta private source authorization reference;
- health/readiness, metrics, logs, alerts, capacity/retention, monitoring, dan kill-switch runbook;
- named team owners, RACI, incident/escalation, support window, dan environment-specific approval.

Handover ditolak bila Critical gate gagal, owner belum dinamai, real data tidak memiliki approval, artifact tidak pinned, atau write/control path ke source tersedia.
