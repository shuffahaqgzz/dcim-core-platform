# NOC Web Dashboard

## Status

OD-03 is **resolved**. The frontend uses **React + TypeScript + Vite** per
[ADR-0017](../docs/adr/0017-react-noc-dashboard-frontend.md), reaffirmed by
[ADR-0024](../docs/adr/0024-python-fastapi-service-language-baseline.md).

## First-slice view scope (synthetic data only)

- Component health
- Data freshness
- P1/P2 events
- Capacity
- Quality/DLQ status
- Asset/CI context
- Workflow drafts

All views consume synthetic fixtures from `fixtures/synthetic/`. No real
endpoints, credentials, or runtime data.

## Planned directory layout

Target layout for Phase 2 implementation (no files created in Phase 0):

```text
src/                  application entry point and configuration
src/components/       shared, reusable UI components
src/views/            page-level views (health, events, capacity, etc.)
src/api/              API client, request helpers, generated types
```

API types will be generated from `../schemas/*.schema.json` using a JSON
Schema-to-TypeScript code generator.

## Server state

TanStack Query handles all server-state fetching and caching (per ADR-0017).
No global client store is introduced until a proven need exists.

## Phase 0 decision: no `package.json`

**No `package.json` or lockfile lands in Phase 0.** Rationale: introducing a
dependency-review surface with zero application code adds audit cost and
supply-chain risk with no offsetting benefit. Phase 2 introduces the manifest
with pinned, reviewed dependency versions.
