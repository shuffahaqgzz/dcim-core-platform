# DCIM Core Platform

Public development repository untuk DCIM Core Platform: fondasi ingestion, Asset/CMDB context, analytics, advisory workflow, SIEM/SOAR boundary, dan NOC-oriented Dashboard/API.

## Status saat ini

- Phase: **Phase 0 COMPLETE / DEV-APPROVED — Repository Safety, Governance, dan Dev Entry Readiness**.
- Phase 1: **DEV-APPROVED (bersyarat)** — Compact Infrastructure Foundation sintetis `dcim-build` (2026-08-03); issue #9 closure gates terpisah.
- Phase 2: **DEV-APPROVED (bounded)** — 2026-08-07; synthetic P1/P2 vertical slice, Kafka stream, p95 latency, live NOC; lihat [owner disposition](docs/evidence/2026-08-07-phase2-owner-disposition.md).
- Phase 3: **in progress** — first component slice delivered (bukan Phase 3 complete).
- Conditions: **C-02, C-06, C-07, C-09 CLOSED**; C-01, C-03, C-04, C-05 OPEN; C-08, C-10 DEFERRED — [CONDITIONS-REGISTER](docs/governance/CONDITIONS-REGISTER.md) tetap otoritatif.
- Overall Development: **CONDITIONAL GO**; open conditions yang tersisa tetap authoritative.
- Maturity: **Prototype/Alpha**; belum siap untuk rilis Production.
- Owner: `shuffahaqgzz`.
- Operating model: Solo Development, controlled handover, multi-team Staging, governed Production.
- Current milestone: Phase 2 is DEV-APPROVED (bounded); Phase 3 first slice is
  in progress. Issue #21 is authorized for close per the 2026-08-07 disposition
  (GitHub close is a separate mutation). Remaining open conditions and any
  remote/merge checks stay authoritative for their own scopes.

## Public code, private runtime

Repository hanya menerima generic code/schema/template, synthetic fixture, dan reviewed public-safe documentation/evidence. Credential, endpoint, source identity, topology, raw payload/log/capture/dump, certificate, screenshot Production, authorization record, serta runtime data wajib private dan di luar Git.

**Security warning:** jangan membuka issue/PR atau mengirim prompt yang memuat secret atau operational evidence. Phase 0 dilarang mengakses source Production. Connector aktif, deployment application stack, self-hosted runner, Hermes integration, dan direct device/OT action tidak tersedia.

## Local Phase 0 validation

Requires Python 3.12-compatible standard library dan GNU Make; tidak ada package install atau network call.

```bash
make phase0-check
```

Gate individual: `make compile`, `make test`, `make validate-json`, `make validate-fixtures`, `make public-safety`, dan `make markdown-links`.

## Repository layout

```text
.github/              PR/issue templates dan synthetic-only CI
connectors/           future read-only connector boundaries
contracts/, schemas/  versioned data contracts
fixtures/synthetic/   public-safe fictional fixtures
scripts/, tests/      Phase 0 automation dan verification
platform/, deploy/    future compact Development foundation
services/, web/       component boundaries
docs/adr/             architecture decisions
docs/architecture/    runtime/data-flow design
docs/security/        policy, threat model, dan stop controls
docs/phase0/          preflight, gate, evidence, dan handover
```

## Governance dan security index

- [Project Charter](PROJECT-CHARTER.md)
- [Development Scope](SCOPE-DEV.md)
- [Known Limitations](KNOWN-LIMITATIONS.md)
- [Roadmap](ROADMAP.md)
- [Development Baseline](docs/baseline/DEVELOPMENT-BASELINE.md)
- [Data Handling](DATA-HANDLING.md) dan [Security Policy](SECURITY.md)
- [ADR directory](docs/adr/) dan [Open Decisions](docs/governance/OPEN-DECISIONS.md)
- [Runtime Plane Separation](docs/architecture/runtime-plane-separation.md)
- [Read-Only Connector Policy](docs/security/read-only-connector-policy.md)
- [Phase 0 Threat Model](docs/security/threat-model-phase0.md)
- [Phase 0 Checklist](docs/phase0/phase0-checklist.md), [Dev Entry Gate](docs/phase0/dev-entry-gate.md), dan [Evidence Index](docs/phase0/evidence-index.md)
- [Staging Handover Contract](docs/phase0/staging-handover-contract.md)

Repository ini dilisensikan di bawah [Apache-2.0](LICENSE); lihat juga
[NOTICE](NOTICE). Komponen runtime tetap memiliki lisensi dan kewajiban
independen yang harus ditinjau sebelum deployment atau distribution.
