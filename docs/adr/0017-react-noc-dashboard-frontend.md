# ADR-0017: React as the NOC Dashboard Frontend Framework

- Status: Accepted
- Date: 2026-07-27
- Owner: shuffahaqgzz
- Decision reference: OD-03
- Decision source: owner request for a final engineer recommendation in the
  2026-07-27 governance review (owner has no framework preference)

## Context

OD-03 leaves the NOC Dashboard frontend framework open between React and Vue.
The owner stated no preference and requested a final engineer recommendation.
The dashboard surfaces health, freshness, capacity, and data-quality views,
including the Phase 2 NOC read model. Grafana already covers operational
dashboarding; the custom frontend focuses on NOC-oriented workflows.

## Decision drivers

- Largest hiring and handover pool for the future multi-team model.
- Ecosystem fit: Grafana itself is React-based, keeping one component model
  across the observability surface and easing future plugin/panel work.
- Testing tooling maturity (Testing Library, Playwright component tests).
- TypeScript-first development for contract-aligned API types.
- Build-time-only footprint: static assets served by the API service; no
  server-side runtime cost on the Development VM.

## Decision

Adopt **React with TypeScript and Vite** for the NOC Dashboard/API
presentation layer.

- State/data: TanStack Query for server state; no global store until a proven
  need exists.
- Styling: plain CSS modules or Tailwind, decided at first implementation;
  no component library lock-in.
- API types generated from the canonical JSON Schemas where practical.

## Options considered

### 1. Vue (rejected)

Vue is technically capable and arguably gentler to learn, but: smaller hiring
pool for the handover team, no synergy with the Grafana (React) surface, and
no compensating advantage for NOC-style data-dense dashboards.

### 2. React (selected)

Selected for ecosystem scale, Grafana synergy, and handover fit.

## Security impact

Static build output only; no new server runtime. Dependency policy: pinned
versions, SBOM and license inventory per the existing supply-chain gate, no
runtime secrets in the bundle.

## License impact

React, Vite, and TanStack Query are MIT-licensed; compatible with the
permissive direction of OD-06 (ADR-0019).

## Resource and operational impact

Node.js is a build-time tool only (CI and local builds); the runtime serves
static assets. No measurable Development VM runtime cost.

## Migration and rollback

No UI exists yet; reversibility is high. Keeping API contracts
framework-neutral preserves the option to replace the frontend later.

## Acceptance evidence

- owner marks this ADR Accepted;
- first dashboard implementation PR follows this stack;
- dependency inventory records the frontend toolchain.

## Revalidation triggers

- handover team composition contradicts the React assumption;
- a future decision adopts a different observability surface without React.
