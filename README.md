# DCIM Core Platform

Public development repository untuk DCIM Core Platform: fondasi ingestion, Asset/CMDB context, analytics, advisory workflow, SIEM/SOAR boundary, dan NOC-oriented Dashboard/API.

## Status saat ini

- Phase: **Phase 0 COMPLETE / DEV-APPROVED — Repository Safety, Governance, dan Dev Entry Readiness**.
- Overall Development: **CONDITIONAL GO**; open conditions tetap authoritative.
- Maturity: **Prototype/Alpha**; bukan Production-ready.
- Owner: `shuffahaqgzz`.
- Operating model: Solo Development, controlled handover, multi-team Staging, governed Production.
- Current milestone: **Phase 1 compact infrastructure foundation**. Implementasi
  synthetic Development berada pada closure-candidate branch; clean-runtime dan
  preflight evidence sudah captured. Parent issue #9 masih membutuhkan remote
  checks pada final pushed head, final review, dan owner disposition sebelum
  closure.

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

No open-source license telah dipilih. Public visibility tidak memberikan reuse rights; OD-06 tetap OPEN.
