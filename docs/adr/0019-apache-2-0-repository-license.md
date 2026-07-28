# ADR-0019: Apache-2.0 as the Repository License

- Status: Accepted
- Date: 2026-07-27
- Owner: shuffahaqgzz
- Decision reference: OD-06
- Decision source: owner direction in the 2026-07-27 governance review
  ("permissive license seperti open-source platform pada umumnya")
- Supersedes: [ADR-0011](0011-public-repository-license-decision-pending.md)
- Related ADRs: ADR-0013, ADR-0016, ADR-0018

## Context

OD-06 has kept the repository without a license since Phase 0 (ADR-0011):
public visibility without reuse rights. This blocks publication and
distribution claims (including derived-image distribution) and leaves
downstream adopters without clarity. The owner directed a permissive license
in the MIT/Apache family.

## Decision drivers

- Standard choice for infrastructure platforms (Kubernetes, Kafka, NetBox,
  Temporal are Apache-2.0), easing adoption and contribution.
- Express patent grant and trademark protection, which MIT lacks.
- Compatibility with the project's permissive dependencies (MIT/BSD/Apache).
- Clear separation from non-permissive runtime dependencies (Grafana AGPL,
  Elasticsearch ELv2/SSPL/AGPLv3, n8n Sustainable Use) which remain
  independently licensed, API-integrated components.

## Decision

License the repository under **Apache-2.0**:

1. Add `LICENSE` (Apache-2.0 text) and a `NOTICE` file at the repository root.
2. Update the README license section; remove the "no reuse rights" wording.
3. Record non-permissive runtime component licenses (Grafana AGPL,
   Elasticsearch ELv2/SSPL/AGPLv3, n8n Sustainable Use, Tracecat pending
   verification) in the dependency inventory as an adopter-facing note.
4. Derived hardened images remain subject to ADR-0013 publication constraints
   until upstream redistribution obligations are reviewed; Apache-2.0 on the
   repository does not by itself authorize image publication.

## Options considered

### 1. MIT (rejected)

Simplest and fully adequate for code reuse, but lacks an express patent grant
and trademark terms. For a platform intended for multi-team handover and
possible commercial use, Apache-2.0's explicit terms reduce future ambiguity
at negligible cost.

### 2. Apache-2.0 (selected)

Selected per owner direction and the drivers above.

### 3. Source-available or no license (rejected)

Conflicts with the owner's stated permissive, open-source-platform intent.

## Security impact

None directly. Public-safety gates are unchanged; licensing the code does not
permit committing private operational data.

## License impact

The repository becomes Apache-2.0. Existing third-party notices are preserved.
Contributors retain copyright; no CLA is introduced in this milestone.

## Resource and operational impact

None.

## Migration and rollback

Documentation-only change. Rollback reverts the LICENSE/NOTICE and README
edits; prior "no license" state is restored.

## Acceptance evidence

- owner marks this ADR Accepted;
- LICENSE, NOTICE, and README updates merged;
- dependency inventory lists non-permissive runtime components.

## Revalidation triggers

- commercial or hosted-service intent changes;
- a dependency with incompatible obligations is added;
- derived-image publication is requested (upstream obligations reviewed
  first).
