# Threat Model Phase 0

Metode: STRIDE dengan qualitative likelihood/impact. Scope mencakup source code, credential boundary, Production telemetry/device identity/topology, sanitized demo data, GitHub Actions, Dev VM, dan Hermes runtime. Phase 0 tidak menghubungkan Production.

## Trust boundaries

Public GitHub, developer session/workstation, Dev VM, office Production network, source devices, future Hermes, dan future Staging diperlakukan sebagai boundary terpisah. Tidak ada trust transitive antar-plane.

## Threat register

| ID / STRIDE | Threat | Likelihood | Impact | Control | Verification | Residual risk | Owner | Revalidation trigger |
|---|---|---|---|---|---|---|---|---|
| T01 / I | Secret committed ke public Git | Medium | Critical | ignore rules, scanner, gitleaks, review | local safety + full-history CI | Regex miss/social error | owner | credential/config change |
| T02 / I | Git history leakage | Low | Critical | history scan, revoke-first response, governed rewrite | full-history gitleaks + inventory | fork/cache persistence | owner | exposure atau history import |
| T03 / T | Malicious dependency/action | Medium | High | trusted source, immutable SHA, minimal dependency | workflow SHA/dependency review | upstream compromise | owner | dependency/action update |
| T04 / E | CI token abuse | Low | High | read-only permissions, no untrusted trigger, GitHub runner | workflow invariant review | platform compromise | owner | permission/trigger change |
| T05 / E | Self-hosted runner pivot | Low | Critical | self-hosted runner prohibited | repository search + rules review | owner setting drift | owner | runner label/change |
| T06 / I | Production endpoint dipakai pada test | Medium | Critical | synthetic fixtures, documentation ranges, no office route | fixture + safety scan | disguised identifier | owner | fixture/test update |
| T07 / E | Read credential memiliki hidden write permission | Medium | Critical | dedicated identity, effective permission test, denylist | private authorization + negative tests | vendor privilege ambiguity | source owner | credential/firmware/RBAC change |
| T08 / I | SNMPv2c exposure | Medium | High | temporary exception, source-IP ACL, private handling, migration plan | private network/auth review | plaintext protocol | source owner | exception expiry/network change |
| T09 / T/E | Redfish privileged method reachable | Medium | Critical | GET allowlist, no generic dispatch | POST/PUT/PATCH/DELETE/action negative tests | new vendor action path | integration owner | API/firmware update |
| T10 / T/E | ISAPI control endpoint reachable | Medium | Critical | metadata GET only, PTZ/config/export denylist | method/path negative tests | undocumented vendor path | integration owner | API/firmware update |
| T11 / I | Log/screenshot leakage | Medium | High | synthetic logs, demo-only screenshot, redaction, no raw upload | scanner + manual review | visual/free-text inference | owner | evidence release |
| T12 / I | Demo de-anonymization | Medium | High | stable pseudonym, controlled time offset, generic location, small-population review | sanitizer tests + reviewer checklist | correlation/linkability | owner | dataset/salt/audience change |
| T13 / I | Prompt/RAG memuat Restricted evidence | Medium | Critical | Restricted data prohibited from prompt/external AI | prompt/evidence review | human copy/paste | owner | AI/RAG integration |
| T14 / I | Credential leakage ke Hermes | Low | Critical | Hermes disabled; no tool/credential/source/evidence | configuration and threat review | future integration drift | owner | C-08/Hermes enablement |
| T15 / I/T | Cross-plane volume/env reuse | Medium | Critical | separate project/network/volume/env/identity | architecture + future deployment tests | operator misconfiguration | platform owner | compose/manifest change |
| T16 / D | Uncontrolled polling mengganggu source | Medium | High | ceilings, bounded retry/concurrency, maintenance window, source metrics | simulator load/stop tests | vendor capacity unknown | source owner | polling/source capacity change |
| T17 / D | Kill switch tidak cukup cepat | Medium | High | default-disabled collector, egress revoke, tested procedure | timed disable drill | control-plane outage | integration owner | collector/network change |
| T18 / R | Bus factor satu / insufficient approval | High | Medium | auditable evidence, ADR, handover contract, future named teams | owner review + handover exercise | no independent Dev approval | owner | Staging entry/staffing change |

## Stop conditions

Active secret/private key, live payload/dump/topology, write-capable path, Production access requirement, unverified Action, self-hosted runner, failed kill switch, atau Critical gate failure adalah NO-GO. Incident details tetap private dan nilai sensitive tidak boleh masuk finding publik.
