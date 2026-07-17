# ADR-0002: Public Code, Private Runtime

- Status: Accepted
- Date: 2026-07-16
- Owner: shuffahaqgzz

## Context

Repository bersifat public, sementara DCIM source dan operational context dapat mengungkap credential, identity, topology, security posture, serta sensitive telemetry.

## Decision

Simpan generic code, schema, synthetic fixture, template, dan sanitized evidence di Git. Live endpoint, identity, topology, credential, raw payload/log/capture/dump, certificate, screenshot, operational prompt, source authorization, serta runtime state wajib di luar Git dan public automation.

CI hanya memakai synthetic data dan GitHub-hosted runner. Runtime environment file dan volume dibuat di luar repository.

## Consequences

- Public-safety scan dan manual review wajib.
- Live defect wajib direproduksi dengan synthetic/sanitized case sebelum public discussion.
- Connected integration dan evidence-nya memerlukan private governed store.
- Accidental publication merupakan incident yang memerlukan credential rotation dan history cleanup.

## Alternatives

Private repository penuh ditolak oleh fixed owner decision. Menaruh sanitized-looking runtime material di public Git tanpa provenance juga ditolak.

## Security Impact

Mengurangi blast radius public disclosure, tetapi tetap bergantung pada automated scan, review, dan private governance yang benar.

## Operational Impact

Runtime/evidence memerlukan private storage, retention, access control, dan incident process terpisah.

## Revalidation Trigger

Perubahan repository visibility, artifact/evidence channel, data classification, atau accidental exposure.
