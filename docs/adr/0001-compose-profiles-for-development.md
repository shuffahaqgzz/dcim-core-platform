# ADR-0001: Docker Compose Profiles untuk Development

- Status: Accepted
- Date: 2026-07-16
- Owner: shuffahaqgzz

## Context

Milestone Prototype/Alpha berjalan pada satu Ubuntu 24.04 VM dengan resource terbatas. Target langsung adalah compact deployability dan integrated evidence, bukan Kubernetes parity atau Production orchestration.

## Decision

Gunakan Docker Compose dengan explicit Development profiles. Pisahkan DEV-BUILD, DEV-INTEGRATION-RO, dan DEV-DEMO melalui project name, network, volume, environment file, serta credential berbeda. Pin image dan dokumentasikan resource limit, health check, retention, dan disk watermark.

Kubernetes ditunda sampai Staging planning atau owner menetapkan Development parity criterion khusus.

## Consequences

- Bootstrap lebih cepat dan troubleshooting lebih sederhana untuk solo developer.
- Compose behavior dan recovery wajib reproducible serta tested.
- Production scalability/HA tidak boleh disimpulkan dari environment ini.
- Future Kubernetes design memerlukan ADR dan migration/parity plan terpisah.

## Alternatives

Single shared plane ditolak karena cross-plane credential/network/volume risk. Kubernetes ditunda karena bukan Phase 0 atau current Development parity criterion.

## Security Impact

Separation wajib deny route Production pada build/demo dan mencegah volume/env reuse. Phase 0 hanya design; tidak membuat network aktif.

## Operational Impact

Promotion menjadi manual dan artifact-based. Setiap plane memiliki health, audit, retention, rollback, serta stop control terpisah.

## Revalidation Trigger

Perubahan orchestrator, manifest/network/volume, Staging mapping, atau kebutuhan Kubernetes parity.
