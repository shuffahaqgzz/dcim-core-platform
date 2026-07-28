# ADR-0016: Workflow Engine Split for Development and Beyond

- Status: Accepted
- Date: 2026-07-27
- Owner: shuffahaqgzz
- Decision reference: OD-02
- Decision source: owner direction in the 2026-07-27 governance review
- Related ADRs: ADR-0005 (dry-run automation), ADR-0019 (repository license)
- Related conditions: C-07, C-10

## Context

The Development baseline scopes workflow automation to draft/dry-run outputs:
notifications, ticket drafts, approval simulations, recommendations, and
mock actions. ADR-0005 prohibits direct device/OT action, and the baseline
keeps Workflow/SOAR as the execution boundary with mandatory human approval.

The owner expects **50+ workflows** over time and directed a split-use strategy
rather than a single engine:

- general/integration workflows with broad platform connectors;
- durable, idempotent core pipeline workflows;
- security workflows adjacent to the SIEM/SOAR boundary.

## Decision drivers

- Match engine strengths to workflow classes instead of forcing one engine.
- Durability and idempotency for pipeline-critical flows.
- Operator UX and integration breadth for general automation.
- Security-team fit for incident/SOAR-adjacent flows.
- License compatibility with the permissive direction of OD-06.
- Single-VM Development footprint (C-07); engines must be phased, not all at
  once.
- Preserve the dry-run/draft-only boundary and human-approval gate.

## Decision

Adopt a **three-engine split**, phased:

1. **n8n — general/integration workflows.** Broad connector catalog, visual
   operator UX, self-hosted. n8n uses the Sustainable Use License
   (source-available, not OSI-permissive): internal use is permitted, but the
   project must not offer n8n as a commercial hosted service. License
   obligations are recorded in the dependency inventory.
2. **Temporal — durable core pipeline workflows.** MIT-licensed. Provides
   durable execution, idempotency, retries, and audit-grade history for
   pipeline-critical flows (event processing, reconciliation, recovery).
3. **Tracecat — security workflows.** Open-source security automation
   (Tines/SOAR-adjacent class), built on Temporal, allowing engine sharing
   with item 2. Exact license and footprint must be verified in the
   implementation spike before acceptance evidence is recorded.

Phasing: n8n first (general workflows have the earliest demand), Temporal when
the first durability-critical pipeline flow is designed, Tracecat together with
the SIEM/SOAR smoke integration scope. Engines share the baseline PostgreSQL
where supported, with separate databases/roles per engine.

## Options considered

### 1. Single engine: n8n for everything

Rejected. n8n durability/idempotency is weaker for pipeline-critical flows, and
its license is not permissive; making it the sole engine concentrates license
and reliability risk.

### 2. Single engine: Temporal for everything

Rejected. Temporal is code-first; operator UX for 50+ general workflows would
require building a custom console, and security teams expect SOAR-native
tooling.

### 3. Split use (selected)

Selected by owner direction. Higher operational surface, mitigated by phasing
and by Tracecat sharing Temporal.

## Security impact

- All engines remain inside the draft/dry-run boundary of the baseline and
  ADR-0005; no engine gains a write/control path to infrastructure.
- Each engine gets least-privilege credentials and its own database role.
- Tracecat operates at the security boundary; its network egress is restricted
  and reviewed with the SIEM/SOAR smoke integration.

## License impact

- Temporal: MIT — compatible.
- n8n: Sustainable Use License — internal use only; recorded as a
  source-available dependency; not a blocker for internal Development.
- Tracecat: license to be verified at spike; if not permissive-compatible,
  revisit this ADR before adoption.

## Resource and operational impact

Three engines add meaningful VM footprint. Phasing keeps Development within
C-07 caps: only n8n runs initially; Temporal and Tracecat join when their
workflow class activates. Per-engine memory/CPU caps are set in ADR-0021
follow-on updates. Idle engines must be stoppable without affecting the
foundation.

## Migration and rollback

Workflow definitions are portable per engine (n8n JSON export; Temporal code
in Git; Tracecat YAML/DSL). Removing an engine does not affect the canonical
event contract or the foundation plane.

## Acceptance evidence

- owner marks this ADR Accepted;
- n8n deployed in the Development profile with a synthetic dry-run workflow;
- per-engine license entries recorded in the dependency inventory;
- Tracecat license/footprint verification recorded before its activation.

## Revalidation triggers

- Tracecat license or architecture proves incompatible;
- workflow count or durability needs outgrow the split;
- a hosted/commercial offering of the platform is proposed (n8n license
  re-review).

## Addendum 2026-07-28: owner decision on SOAR platform roles

- Owner confirmed 2026-07-28 (source: `docs/research/PRD.md` §7 Q3): **TraceCat + Temporal** is the SOAR/security-automation path. TraceCat refers to the product spelled **Tracecat** in the accepted body.
- **n8n is retained only for non-destructive operational workflows** and is **not** the SOAR platform.
- TraceCat license/footprint verification remains a precondition to activation, unchanged from the accepted body.
- The Wazuh → Kafka `dcim.siem.events` producer remains the SIEM output design.
- Phasing is unchanged and remains bounded by C-07.
