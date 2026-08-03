# ADR-0011: Public Repository License Decision Pending

- Status: Superseded by [ADR-0019](0019-apache-2-0-repository-license.md)
- Decision reference: OD-06 (accepted 2026-07-27 — Apache-2.0)
- Date: 2026-07-17
- Owner: shuffahaqgzz

## Context

> Superseded by [ADR-0019](0019-apache-2-0-repository-license.md), which
> records the accepted Apache-2.0 repository license.

Repository public belum berarti reuse/contribution rights jelas. License memengaruhi dependency compatibility, contribution, distribution, dan commercial intent.

## Decision

Tidak memilih atau menambahkan `LICENSE` sampai owner menutup OD-06 dengan explicit decision. Public visibility dipertahankan sesuai fixed decision.

## Alternatives

Permissive, copyleft, source-available, dan closed/no-license tetap kandidat. Belum ada evidence/owner intent cukup untuk memilih.

## Consequences

External reuse/contribution terms tidak terdefinisi. Dependency/license review harus mencatat compatibility conditional dan menghindari assumption tersembunyi.

## Security Impact

Tidak ada runtime control langsung; supply-chain provenance dan legal distribution risk tetap perlu review.

## Operational Impact

Release/distribution dan contributor process dapat tertunda. Tidak ada migration code sebelum keputusan.

## Revalidation Trigger

Owner business intent, external contribution, release/distribution, atau dependency license conflict.
