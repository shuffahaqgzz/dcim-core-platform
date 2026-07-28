# ADR-0018: Elasticsearch as the Development Search Platform

- Status: Accepted
- Date: 2026-07-27
- Owner: shuffahaqgzz
- Decision reference: OD-04
- Decision source: owner direction in the 2026-07-27 governance review (team
  already runs R&D on Elasticsearch)
- Related conditions: C-07

## Context

OD-04 compares Elasticsearch and OpenSearch for event/log search. The owner's
team already conducts R&D with Elasticsearch and asked to focus on it. Search
is not required for `dev-v0.1.0`; it enters with analytics/search-scope work
after the vertical slice.

## Decision drivers

- Existing team R&D investment and operational familiarity.
- Query/API fit for event and log search over the canonical event envelope.
- Single-node Development footprint within C-07 caps.
- License obligations recorded explicitly (Elasticsearch is not
  OSI-permissive in its default distribution).
- Backup/restore and lifecycle fitting the foundation recovery patterns.

## Decision

Adopt **Elasticsearch** as the Development search platform, single-node, with
these constraints:

1. **License recorded, not ignored.** The default Elasticsearch distribution
   ships under the Elastic License 2.0 / SSPL; Elastic additionally offers the
   free distribution under AGPLv3 since 2024. The project integrates via API
   only, makes no distribution claim, and records the chosen license in the
   dependency inventory. A distribution or hosted-service proposal triggers
   re-review.
2. **Single node, capped heap.** Development runs one node with a heap cap
   (proposed 2–4 GB, finalized in the C-07 capacity update) and a 30-day
   default index retention aligned with Kafka retention.
3. **API-only integration.** The platform talks to Elasticsearch over its REST
   API with a least-privilege user; no plugin development in this milestone.
4. **Backup via snapshot** to the protected runtime volume, exercised in the
   recovery evidence when the search scope activates.

## Options considered

### 1. OpenSearch (rejected for this milestone)

Apache-2.0 and license-clean, but the team's R&D is on Elasticsearch, feature
parity is sufficient for the Development scope, and switching now would
discard working knowledge without a functional requirement forcing it. License
pressure is mitigated by API-only, no-distribution use. Reconsidered at
Staging qualification or if distribution is ever proposed.

### 2. Elasticsearch (selected)

Selected per owner direction and team R&D alignment.

## Security impact

Single-node, internal-only, no anonymous access, credentials in the private
credential-control store, no public exposure. Snapshots stay in the protected
runtime root outside Git.

## License impact

ELv2/SSPL/AGPLv3 obligations recorded in the dependency inventory; no
distribution, no hosted offering. Independent of OD-06 (the repository's own
license) but listed beside it for adopters.

## Resource and operational impact

JVM service; heap capped (proposed 2–4 GB) plus off-heap filesystem cache.
Included in the ADR-0021 capacity follow-up when the search scope activates;
must not starve the foundation services.

## Migration and rollback

Index definitions and ingest mappings are versioned in Git. Reindexing from
the canonical event store (PostgreSQL) is the rollback path; Elasticsearch is
a derived view, never a system of record.

## Acceptance evidence

- owner marks this ADR Accepted;
- license entry recorded in the dependency inventory;
- single-node deployment with heap cap and snapshot restore demonstrated when
  the search scope activates.

## Revalidation triggers

- distribution, SaaS, or Staging/Production use is proposed;
- Elastic license terms change materially;
- OpenSearch feature or license advantage becomes decisive.
