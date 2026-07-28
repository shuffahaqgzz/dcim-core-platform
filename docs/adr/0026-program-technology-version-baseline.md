# ADR-0026: Program Technology Version Baseline

- Status: Accepted
- Date: 2026-07-28
- Owner: shuffahaqgzz
- Decision source: owner confirmation 2026-07-28 (`docs/research/PRD.md` §7 Q8) and D-1 clarification
- Related ADRs:
  - [ADR-0018](0018-elasticsearch-search-platform.md) — Elasticsearch as the Development Search Platform
  - [ADR-0003](0003-single-broker-kraft-development.md) — Single-Broker Kafka KRaft pada Development
  - [ADR-0013](0013-derived-hardened-foundation-images.md) — Derived Hardened Foundation Images for Development
  - [ADR-0014](0014-official-release-binary-source-provenance.md) — Official Release Binary and Source Provenance Contract

## Context

`docs/research/PRD.md` §7 Q8 asked whether the program aligns to Elasticsearch 8.x (wiki reference design) or 9.x (ingestion repo). The owner confirmed **9.x**. At the same time, the owner decision logged PostgreSQL 16 in `docs/research/DECISION-LOG-REVIEW.md` §4 conflicted with the core `deploy/compose/images.json` pin of `postgres:17.10-bookworm`. Owner clarification D-1 resolved the conflict: PostgreSQL 17.x is the program target, the pinned 17.10 image remains authoritative for the foundation plane, and PostgreSQL 16 is the minimum floor for satellite components that cannot upgrade immediately.

This ADR records the unified program technology version baseline so wiki, core repo, and satellite repos do not drift again.

## Decision drivers

- Eliminate version drift between the wiki reference designs, the core foundation plane, and satellite repos.
- Prefer current stable releases that carry the latest security fixes.
- Preserve the already-qualified foundation-plane image pin and its build provenance.
- Allow satellite components to move on independent schedules without blocking the foundation plane.
- Keep the license obligations of Elasticsearch unchanged (ADR-0018).
- Maintain image-provenance and pinning discipline per ADR-0013 and ADR-0014.

## Decision

1. **Elasticsearch 9.x** is the program-wide target. This supersedes the wiki's Elasticsearch 8.x target. The license constraints in [ADR-0018](0018-elasticsearch-search-platform.md) remain unchanged.
2. **PostgreSQL 17.x** is the program target. The core development foundation plane's pinned image `postgres:17.10-bookworm` in `deploy/compose/images.json` remains authoritative for that plane.
3. **PostgreSQL 16** is the minimum floor for satellite components that cannot upgrade to PostgreSQL 17.x immediately.
4. **Redis 7** is the program target.
5. **Apache Kafka** versioning follows [ADR-0003](0003-single-broker-kraft-development.md) and the concrete image pin in `deploy/compose/images.json`.
6. **Concrete image digests live only in `deploy/compose/images.json`.** They are not duplicated in this ADR. A version bump is a pinned-image change governed by [ADR-0014](0014-official-release-binary-source-provenance.md), not a documentation edit.

## Options considered

### 1. Align everything to PostgreSQL 16 (rejected)

Would have matched the first pass of the owner decision log, but it would surrender the current-stable security fixes and would conflict with the foundation plane already pinned to `postgres:17.10-bookworm`. Rejected.

### 2. Upgrade every satellite component to PostgreSQL 17.x immediately (rejected)

Some satellite components cannot move to PostgreSQL 17.x in Phase 0. Forcing an immediate upgrade would block the decision lock and delay the foundation plane. Rejected.

### 3. Target-plus-floor (selected)

Set PostgreSQL 17.x as the program target and the foundation-plane pin, while allowing PostgreSQL 16 as a safe minimum floor for lagging satellites. This keeps the foundation plane current, protects the satellite path, and resolves the D-1 conflict.

## Security impact

- Running the current stable lines (Elasticsearch 9.x, PostgreSQL 17.x) provides the latest vendor security fixes, e.g., PostgreSQL CVE-2025-8713.
- PostgreSQL 16 as a floor still receives support fixes but may lag behind 17.x; satellites on the floor must be tracked and upgraded.
- All runtime credentials, digests, and provenance records remain in the private credential and runtime stores, not in Git.
- No public network exposure is introduced by this version baseline.

## License impact

- Elasticsearch 9.x remains subject to the same Elastic License 2.0 / SSPL / AGPLv3 obligations recorded in [ADR-0018](0018-elasticsearch-search-platform.md). The version change does not alter distribution or hosted-service obligations.
- PostgreSQL remains under the PostgreSQL License.
- Kafka, Redis, and other runtime component licenses remain independent and are recorded in the dependency inventory.

## Resource and operational impact

- The foundation plane continues to use the qualified `postgres:17.10-bookworm` image; CPU, memory, disk, and network constraints remain unchanged.
- Satellite components on the PostgreSQL 16 floor may require separate upgrade planning, compatibility testing, and maintenance windows.
- No HA, SLA, or Production claim is implied by this baseline.

## Migration and rollback

- Satellites on the PostgreSQL 16 floor must plan migration to PostgreSQL 17.x. Rollback to 16 remains available if a 17.x upgrade fails.
- Elasticsearch 8.x to 9.x migration follows the upstream documented upgrade/reindex path and must be exercised before the search scope is used beyond Development.
- Any change to the foundation-plane image pin or satellite floor triggers revalidation under [ADR-0014](0014-official-release-binary-source-provenance.md).

## Acceptance evidence

- This ADR is marked `Accepted`.
- `deploy/compose/images.json` records the pinned `postgres:17.10-bookworm` foundation-plane image.
- [ADR-0018](0018-elasticsearch-search-platform.md) is accepted and its Elasticsearch license obligations are recorded.
- Satellite inventory records any PostgreSQL 16 floor instances and their planned upgrade path.

## Revalidation triggers

- New major or minor release of Elasticsearch, Kafka, Redis, or PostgreSQL that changes security or compatibility posture.
- A satellite component moves off the PostgreSQL 16 floor.
- The foundation-plane image pin in `deploy/compose/images.json` changes.
- A wiki or satellite repo reintroduces version drift.
- Material change to Elasticsearch or other runtime license terms.
