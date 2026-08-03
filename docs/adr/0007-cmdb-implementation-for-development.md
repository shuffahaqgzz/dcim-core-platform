# ADR-0007: CMDB Implementation for Development

- Status: Accepted
- Date: 2026-07-17 (accepted 2026-07-28)
- Owner: shuffahaqgzz
- Decision reference: OD-01
- Related conditions: C-02, C-05, C-06, C-07
- Related ADRs: ADR-0001, ADR-0002, ADR-0006
- Issue: pending
- Implementation PR: pending

## Context

The Development baseline requires deterministic Asset/CI context in the synthetic P1 and P2 vertical slices. Current service-boundary READMEs describe the CMDB as owning CI identity, relationships, history, and context APIs and the Asset Repository as owning asset identity, lifecycle, aliases, and public APIs. That ownership split is existing implementation guidance, not an accepted architecture decision. This ADR proposes and tests it rather than treating it as settled. ADR-0006 already fixes canonical identity rules: product row IDs and IP addresses cannot replace canonical Asset/CI identity, and alias validity, confidence, collision handling, and history must be preserved.

OD-01 was accepted on 2026-07-28, selecting a thin custom CMDB service on the baseline PostgreSQL platform for Development. The current implementation status remains a documented service boundary and JSON Schemas, without an implemented relationship/history store or context API; this remains service-delivery backlog, not an open architecture choice.

This is a Development decision for the compact Ubuntu 24.04 single-VM Docker Compose profile. It makes no HA, SLA, hardening, Staging, or Production claim. All evaluation data and evidence must be synthetic and public-safe.

## Decision drivers

- Preserve ADR-0006 identity, aliases, validity, confidence, collision, and lineage semantics.
- Support typed CI relationships, history, deterministic context lookup, idempotent replay, and explicit validation failures.
- Minimize attack surface and prohibit any path from CMDB integration to infrastructure write/control operations.
- Fit with PostgreSQL and the bounded single-VM Development profile without starving Kafka, observability, ingestion, or dashboard services.
- Provide health, metrics, logs, backup/restore, upgrades, rollback, and a rapid disable path.
- Use a license and dependency set compatible with OD-06 once that decision is made.
- Do not silently select the long-term service language/framework governed by OD-07; spike code must be disposable or use an explicitly owner-approved temporary stack.
- Permit migration through a versioned, product-neutral API and canonical export rather than product database IDs.
- Be operable and transferable with clear ownership, runbooks, data dictionary, recovery procedure, and limited specialist knowledge.

## Options considered

### Option 0: retain the boundary-only status quo

No dedicated CMDB implementation is added. Existing schemas and PostgreSQL remain available for later work.

- **Security:** smallest immediate attack surface; no new credentials or dependency chain. It provides no implemented CMDB authorization or audit boundary.
- **Operability:** no additional service to deploy or patch, but reconciliation, lifecycle, and relationship handling remain manual or undefined.
- **Development VM resources:** negligible incremental CPU, memory, and disk use.
- **License:** no new license impact.
- **Migration and reversibility:** no immediate migration; continued delay increases later normalization and backfill cost.
- **Handover:** ownership and operating procedures remain incomplete and person-dependent.

This is a useful benchmark control and a possible time-boxed deferral, but it is not viable for the Development milestone because it cannot prove the required Asset/CI context path.

### Option 1: thin custom CMDB service on baseline PostgreSQL

Build the smallest repository-owned service and schema needed for canonical CIs, typed relationships, history, aliases/crosswalks, and versioned context APIs. Reuse the baseline PostgreSQL and observability stack.

- **Security:** can expose only the required API and enforce exact validation, least privilege, audit, and read-only source-ingestion boundaries. The project must build and maintain authentication, deny-by-default authorization, audit attribution, token lifecycle, validation, role separation, and negative tests.
- **Operability:** one domain-specific service and migrations can stay compact and integrate with existing health/metrics patterns. The project owns every failure mode, upgrade, admin workflow, and on-call procedure.
- **Development VM resources:** likely the lowest incremental footprint because PostgreSQL is reused, but this is a hypothesis requiring measurement under the complete Compose profile. Reuse must still isolate database/schema ownership, roles, connections, backup, and restore blast radius.
- **License:** project code remains subject to unresolved OD-06; every framework, image, and transitive dependency still needs license/SBOM review.
- **Migration and reversibility:** versioned migrations, canonical JSON export, stable internal IDs, and deterministic import can make rollback and replacement direct. Poor schema/API discipline would erase this benefit.
- **Handover:** exact domain fit reduces product-specific knowledge, but custom code, migrations, reconciliation, operator tooling, data dictionary, and support ownership must be transferred.

### Option 2: NetBox behind a canonical CMDB adapter

Deploy NetBox Community as a network/DCIM source-of-truth backend and map it through an adapter to canonical Asset/CI contracts. NetBox documents a network-oriented data model, REST and read-only GraphQL APIs, object-based permissions, multiple authentication backends, and token controls. It describes itself as a network source of truth rather than a general-purpose CMDB.

- **Security:** documented permission/authentication features are available. REST is write-capable, so both token configuration and associated user/object permissions must deny writes; effective access is their intersection. Tokens must be scoped, expiring, revocable, and network-restricted. Configuration such as `EXEMPT_VIEW_PERMISSIONS` must be audited, and GraphQL can be disabled. Web, API, authentication, import, plugin, worker, and dependency surfaces expand patch and audit scope.
- **Operability:** documented UI, APIs, ecosystem, and community deployment can improve operator workflow. Deployment adds the application, workers, Redis/Valkey, HTTP/TLS, upgrades, backup, monitoring, and plugin/version compatibility work. Community support is community-led.
- **Development VM resources:** official installation documents list PostgreSQL and Redis dependencies, but no authoritative CPU/RAM/storage sizing was found. Full-profile idle/load measurements are required. The spike must compare dedicated stateful services with any proposed sharing; shared PostgreSQL/Redis cannot weaken credential isolation, connection limits, recovery isolation, or blast radius.
- **License:** NetBox Community is Apache-2.0. Images, plugins, and dependencies need separate review, and compatibility remains conditional on OD-06.
- **Migration and reversibility:** REST extraction and exports are available, but NetBox's official FAQ warns that normal exports are not directly re-importable and may omit relationship context. A canonical adapter, ID crosswalk, neutral export, PostgreSQL backup, and tested round trip are mandatory.
- **Handover:** mature documentation and UI help. Mapping rules, custom fields/plugins, version matrix, restore procedure, and responsibility boundaries add product-specific knowledge.

NetBox is strongest when network/DCIM/IPAM objects dominate and its curated model represents required relationships without extensive plugins or sidecars.

### Option 3: another extensible source-of-truth product

An alternative such as Nautobot may offer a mature UI, API, jobs, and application/plugin model. It remains viable only if official-source research and the same synthetic spike demonstrate better semantic or operational fit than NetBox and the custom service.

This option has not received enough primary-source license, security, deployment, migration, or resource analysis in this proposal. It remains a comparison candidate, not a basis for selection.

### Option 4: iTop (added 2026-07-27 from owner-team evaluation)

The owner's team is evaluating iTop as CMDB to connect relationships and CIs to sources. Primary-source research (2026-07-27) established: iTop is a PHP 8.x ITSM platform with a generic-CI CMDB core (custom CI classes via XML datamodel modules, first-class impact analysis), running on **MySQL/MariaDB — not PostgreSQL**; its REST API supports full CI CRUD with token auth; webhooks require a separately installed AGPL extension; and **no official Docker image exists** (community images only).

- **Security:** REST is write-capable; scoped read-only tokens and permission audits required. Supply-chain risk from community-maintained container images.
- **Operability:** mature ITIL product, but heavier process orientation (incident/change/problem) than a DCIM source-of-truth needs; adds a second database engine (MySQL/MariaDB) to the VM.
- **Development VM resources:** 2 vCPU / 4 GB RAM for <50k CIs — acceptable, but alongside its own MySQL/MariaDB instance.
- **License:** **AGPL-3.0** (extensions also AGPL). API-only integration does not trigger copyleft on project code, but it compounds the license-compliance surface already flagged for Grafana AGPL, conflicts with the permissive direction of OD-06 (ADR-0019), and burdens downstream adopters.
- **Migration and reversibility:** CI export possible; ITSM-coupled model raises mapping cost to the canonical contract.
- **Handover:** mature documentation, but PHP/XML-datamodel skills are narrower than Django/Python.

Assessment: iTop's generic CI model and impact analysis are genuinely strong, but AGPL-3.0, the MySQL/MariaDB requirement (against the PostgreSQL baseline), and the absence of an official container image make it a weaker fit than NetBox for this platform's constraints. It remains in the comparison for completeness; the spike gates below apply unchanged if the owner still wants it evaluated.

## Comparison summary

| Criterion | Status quo | Custom PostgreSQL service | NetBox adapter | Other product |
|---|---|---|---|---|
| Canonical model fit | Missing implementation | Exact by design; project-owned correctness | Mapping/customization risk | Unproven |
| Security surface | Lowest, but no CMDB controls | Small; controls must be built | Larger; mature controls available | Unproven |
| Operability | No service, no milestone capability | Compact; full ownership burden | Mature UX/docs; larger stack and patch burden | Unproven |
| VM resource use | Negligible | Expected low; measure | Unknown; measure complete stack | Unknown |
| License | No change | Conditional on OD-06 and dependencies | Apache-2.0 core; review full BOM | Unproven |
| Migration | Deferred cost | Controlled migrations/neutral export | Adapter/export required; round-trip concern | Unproven |
| Reversibility | Easy now, cost grows | High if neutral contracts enforced | Moderate if product IDs/plugins stay isolated | Unproven |
| Handover | Weak/undefined | High custom ownership burden | Better operator UX, product expertise required | Unproven |

## Proposed decision

Treat a **thin custom CMDB service on the baseline PostgreSQL platform for Development** as the leading hypothesis, behind versioned product-neutral Asset/CI/Relationship/history contracts. Propose the current service ownership split: Asset Repository owns stable asset identity/lifecycle/aliases; CMDB owns CI identity, typed relationships/history, and context lookup. Contract tests must prove the boundary does not fork canonical identity or alias history.

No implementation is selected before owner acceptance. A bounded synthetic spike must compare the hypothesis with NetBox using identical fixtures and recorded methods. Both candidates must first pass canonical-semantics, security, license, recovery, neutral-round-trip, and Development-VM-headroom gates. Passing candidates are scored: canonical relationship/history fit 20%, security 20%, operability and delivery effort 15%, VM resource use 15%, migration 10%, reversibility 10%, and handover 10%. Each score needs a recorded measure or rubric; no unsupported score is allowed. Highest total becomes the recommendation. A tie within five percentage points goes to the candidate with lower measured peak RAM; if still tied, lower custom-code/plugin surface wins. Owner reviews the evidence and alone accepts, rejects, or requests revision.

Regardless of selected backend:

- canonical Asset/CI IDs remain authoritative;
- backend IDs remain crosswalk values and IP remains an alias, never a primary key;
- pipeline and dashboard consumers use the versioned context API, not backend tables or product APIs directly;
- canonical export/import is an acceptance criterion;
- Production-connected sources, credentials, payloads, and topology are excluded from the spike;
- CMDB record mutation is permitted only for synthetic spike data through scoped service identities; no CMDB component, generic outbound client, plugin, script, or job may reach infrastructure write/control methods;
- runtime egress is denied by default and any required destination/method is allowlisted;
- resource limits, health checks, backup/restore, migration/rollback, disable procedure, license inventory, and handover runbook are required.

## Acceptance and condition mapping

- **ADR acceptance evidence:** candidate gate results, weighted comparison, pinned primary-source references, license/BOM disposition, migration and neutral round-trip, recovery, resource headroom, security tests, and handover exercise. These decide OD-01 only.
- **C-06:** canonical identity, alias validity/confidence/history, collision, relationship, and deterministic resolution evidence.
- **C-07:** full-profile Compose limits, retention/disk assumptions, measured headroom, connection limits, alerts, and load evidence.
- **C-02 and C-05:** synthetic provenance, summarized/sanitized results, public-safety scan, and manual diff review. No generated credential value, raw payload/log, scanner output, screenshot, endpoint, identifier, or topology is evidence for this public ADR.
- **Day 6 plan:** persistence/API, identity/collision/alias, migration, and rollback proof.
- **Milestone gates:** the eventual implementation must also pass the baseline's complete contract, integration, E2E P1/P2, latency, DLQ, secret/public-safety, dependency/license, migration, and recovery gates. The spike's 95% enrichment check alone does not satisfy milestone acceptance.

## Consequences

### Positive

- Best direct fit with accepted identity and history semantics.
- Reuses the accepted PostgreSQL baseline and can minimize Development footprint.
- Keeps canonical contracts independent of a third-party product and makes later replacement testable.
- Avoids making a network-focused product the implicit authority for broader CI semantics before model-fit evidence exists.

### Negative

- Project owns CMDB schema correctness, authorization, audit, reconciliation, migrations, APIs, operator tooling, security response, and support.
- Mature product UX, ecosystem, and documentation are not obtained automatically.
- Resource and delivery advantages remain hypotheses until measured.
- Repository licensing under OD-06 and service language/framework selection under OD-07 can still constrain the custom stack.

### Risks and mitigations

- **Underbuilt CMDB:** restrict initial scope to milestone contracts and one P1/P2 slice; do not claim general-purpose CMDB completeness.
- **Custom ownership burden:** require data dictionary, OpenAPI, migration/recovery runbook, common failure drills, and second-operator handover exercise.
- **Product lock-in later:** require canonical IDs, adapter boundary, crosswalks, and verified neutral export/import.
- **Identity divergence:** use ADR-0006 contract tests across persistence and API boundaries.
- **VM contention:** impose Compose limits and benchmark with the full Development profile before acceptance.

## Synthetic spike evidence required before acceptance

1. **Common corpus:** seeded synthetic assets and CIs covering native UUID, manufacturer-plus-serial fallback, hostname/FQDN/IP changes, collisions, confidence, non-network CIs, typed relationships, cycles, invalid endpoints, deletes, and tombstones.
2. **Mapping matrix:** each canonical field and invariant mapped to custom PostgreSQL and NetBox as native, custom, sidecar, transformed, or lost.
3. **API/contract tests:** create/upsert, lookup, traversal, history, pagination/filtering, idempotent replay, concurrency conflicts, invalid input, and version compatibility.
4. **Integrated enrichment:** synthetic P1 and P2 paths with zero silent loss, at least 95% enrichment success, and recorded p50/p95/p99 method, clock, test window, exclusions, and repeats.
5. **Resource benchmark:** same host and Compose workload; idle/load CPU and RSS, startup time, disk growth, DB connections, image sizes, and coexistence with Kafka, Prometheus, Grafana, ingestion, and dashboard. Record limits, headroom, and watermarks.
6. **Security evidence:** ports and trust boundaries; actor/role matrix; deny-by-default access; separate read, ingest-write, and migration/admin identities; database/schema roles with no cross-service grants; token TTL/rotation/revocation; audit attribution; connection limits; egress deny/allowlist; and disable/kill path. Negative tests cover unauthenticated access, horizontal and vertical escalation, forbidden CI/relationship mutations, source POST/PUT/PATCH/DELETE and bulk/import paths, scripts/jobs/plugins, GraphQL state, token expiry/revocation, and network restrictions. Permitted synthetic CMDB mutation remains distinct from prohibited source-infrastructure write/control.
7. **Recovery/migration:** clean rebuild, backup/restore, migration up/down, failed-migration recovery, canonical export/import round trip with counts and checksums, ID/crosswalk preservation, downtime, and explicit RPO/RTO assumptions.
8. **Operability/handover:** readiness/health, metrics/logs, common failure and upgrade drills, inventory of custom code/plugins, runbook task completed by a second operator, and recorded support ownership.
9. **Supply chain and license:** core, images, base images, frameworks, transitive dependencies, and plugins; pinned provenance and signature/digest verification; SBOM; vulnerability severity gate and remediation owner/time target; lifecycle status; notices and source obligations; compatibility matrix against each remaining OD-06 direction; commercial support/cost noted separately if considered. Critical unresolved findings are NO-GO.
10. **Reproducibility and public safety:** pinned versions/digests and artifact sources, workload seed and size, commands, results, limitations, and public-safe evidence paths. Use synthetic credentials/endpoints only. Commit no secret values, raw payloads/logs/screenshots, topology, or raw scanner output; summarize and sanitize evidence, then run the public-safety scan and manual diff review.

Acceptance must be NO-GO if canonical semantics are lost, neutral round-trip fails, prohibited source write/control is reachable, critical security/recovery gates fail, or the full VM profile lacks documented headroom.

## Migration and rollback outline

1. Freeze versioned canonical contracts before backend-specific work.
2. Create backend-neutral IDs and a backend crosswalk table.
3. Load only the synthetic corpus and validate counts, constraints, aliases, relationships, and history.
4. Take a backend-specific full-fidelity database backup and separately export canonical records plus checksums before each migration. Neutral export is not a database backup.
5. Apply forward migration; verify API and integrated enrichment tests.
6. On failure, stop the isolated CMDB profile. Restore its dedicated database/database namespace from the backend-specific backup, redeploy the pinned prior application version, and rerun checksums and smoke tests. Use schema downgrade only where the migration explicitly proves it safe; otherwise restore. A NetBox rollback restores its compatible application/database pair, while a custom-service rollback restores its compatible service/schema pair.
7. A future backend replacement must use canonical export/import and crosswalk reconciliation, not direct product-table coupling.

Exact downtime, RPO, and RTO targets require owner input and measured spike results.

## Handover requirements

- architecture and trust-boundary diagram using generic names;
- ownership/RACI for schema, service, database, security patches, and incident response;
- data dictionary, relationship vocabulary, API specification, and compatibility policy;
- deploy, health, backup, restore, migration, rollback, disable, and upgrade runbooks;
- pinned version and dependency/license inventory;
- capacity assumptions, limits, alerts, and measured headroom;
- known limitations and deferred product features;
- second-operator recovery and common-task evidence.

## Official primary sources used

NetBox Community v4.6.1, release commit `64d3b114bc68e152869b964d54b220ecf1d50880`, was evaluated on 2026-07-17. Commit-pinned sources support material product claims. The spike must still pin every deployed image, plugin, and dependency independently.

- [NetBox v4.6.1 official release](https://github.com/netbox-community/netbox/releases/tag/v4.6.1)
- [NetBox v4.6.1 data models](https://github.com/netbox-community/netbox/blob/64d3b114bc68e152869b964d54b220ecf1d50880/docs/development/models.md)
- [NetBox v4.6.1 object-based permissions](https://github.com/netbox-community/netbox/blob/64d3b114bc68e152869b964d54b220ecf1d50880/docs/administration/permissions.md)
- [NetBox v4.6.1 authentication](https://github.com/netbox-community/netbox/blob/64d3b114bc68e152869b964d54b220ecf1d50880/docs/administration/authentication/overview.md)
- [NetBox v4.6.1 REST API and token controls](https://github.com/netbox-community/netbox/blob/64d3b114bc68e152869b964d54b220ecf1d50880/docs/integrations/rest-api.md)
- [NetBox v4.6.1 GraphQL API](https://github.com/netbox-community/netbox/blob/64d3b114bc68e152869b964d54b220ecf1d50880/docs/integrations/graphql-api.md)
- [NetBox v4.6.1 installation dependencies](https://github.com/netbox-community/netbox/blob/64d3b114bc68e152869b964d54b220ecf1d50880/docs/installation/index.md)
- [NetBox v4.6.1 upgrade and backup guidance](https://github.com/netbox-community/netbox/blob/64d3b114bc68e152869b964d54b220ecf1d50880/docs/installation/upgrading.md)
- [Official NetBox Docker deployment](https://github.com/netbox-community/netbox-docker)
- [NetBox v4.6.1 Apache-2.0 license](https://github.com/netbox-community/netbox/blob/64d3b114bc68e152869b964d54b220ecf1d50880/LICENSE.txt)
- [NetBox export/re-import limitation](https://github.com/netbox-community/netbox/wiki/Frequently-Asked-Questions), mutable official wiki accessed 2026-07-17; no release-pinned full-fidelity neutral round-trip guarantee was found

## Unresolved owner inputs

- Required CI classes and relationship vocabulary beyond current schemas.
- Inventory size, query/write rates, retention, concurrency, and growth assumptions.
- Development recovery objectives and acceptable migration downtime.
- Whether operator UI/IPAM/DCIM workflows are milestone requirements or later capabilities.
- Staffing, on-call ownership, and acceptable custom-code burden.
- OD-06 direction and any commercial support budget.
- OD-07 service language/framework direction or explicit approval for a disposable spike stack.
- ADR issue link required by the open-decision process; no implementation PR may proceed while it remains pending.

~~Owner must explicitly change this ADR to `Accepted` or `Rejected`.~~ **[COMPLETED]** OD-01 was accepted on 2026-07-28; this ADR records the selected thin custom CMDB service on the baseline PostgreSQL platform. See the addendum below.

## Addendum 2026-07-27: iTop research and updated engineer recommendation

Owner direction recorded 2026-07-27: the team is evaluating iTop; the owner
asked for research on suitable CMDB platforms and whether a custom service is
feasible. Research against official primary sources added Option 4 above and
established the comparison below.

| Dimension | iTop | NetBox | Custom PostgreSQL service |
|---|---|---|---|
| License | AGPL-3.0 | Apache-2.0 | project-owned (per ADR-0019) |
| Database | MySQL/MariaDB (not PostgreSQL) | PostgreSQL native | PostgreSQL native |
| Data model | generic CI classes, ITIL, impact analysis | fixed DCIM/IPAM model + custom fields/plugins | exact canonical fit by design |
| REST API | full CI CRUD, token auth | full CRUD, token auth, OpenAPI, GraphQL read | full control |
| Webhooks | AGPL extension, separate install | built-in event rules | build as needed |
| Official container image | none (community only) | official `netboxcommunity/netbox` + compose | project-built |
| Footprint | 2 vCPU / 4 GB + own MySQL/MariaDB | ~1–2 GB total, shares PostgreSQL baseline | lowest; reuses baseline |

Updated engineer recommendation (unchanged process, updated ranking):
**NetBox behind the canonical adapter** moves to co-leading candidate beside
the thin custom service, and is the recommended product option over iTop for
this platform: Apache-2.0, PostgreSQL-native, official images, built-in
webhooks, and a DCIM model covering most physical-infrastructure needs, with
custom fields/plugins carrying canonical alias/validity/source-attribution
semantics. The thin custom service remains the exact-fit fallback if the
spike's mapping matrix shows NetBox loses canonical semantics. iTop is not
recommended unless the owner values its ITIL impact analysis above the
license, database, and supply-chain costs.

The owner accepted that CMDB data ownership after handover stays with the
team. The bounded synthetic spike and weighted scoring defined above remain
the acceptance mechanism; iTop enters the spike only on explicit owner
request.

## Addendum 2026-07-28: owner decision

Owner confirmed 2026-07-28 (source: `docs/research/PRD.md` §7 Q1 and
`docs/research/DECISION-LOG-REVIEW.md` §2):

1. A **custom PostgreSQL CMDB service** is the implementation for Phase 1–2.
2. **iTop and NetBox are demoted to read-only discovery sources** behind the canonical adapter; neither is the CMDB of record.
3. The bounded synthetic spike defined in this ADR is **converted** from a selection mechanism into Phase 3 implementation acceptance evidence: canonical-semantics tests, security negative tests, recovery/neutral round-trip, and Development-VM headroom evidence are all still required of the custom service before milestone acceptance.
4. **ADR-0022 remains reserved and unused**; no replacement CMDB document is written.
5. The satellite-repo iTop-consumer refactor (generic CMDB adapter) is a cross-repo follow-up outside this repository (per clarification D-5 in `docs/research/PHASE0-PLAN.md`).
