# Production Source Safety Checklist

Checklist ini future gate, bukan authorization Phase 0.

- [ ] Private written authorization dan classification masih berlaku.
- [ ] Dedicated read-only identity diuji; effective permission tidak memiliki write/control.
- [ ] Exact endpoint, method/OID/field allowlist dan prohibited operations disetujui.
- [ ] Separate network/egress, source-IP ACL, DNS/TLS verification, dan no source bind mount.
- [ ] Pinned image digest dipromosikan manual; tidak ada mutable source.
- [ ] Timeout, bounded retry/jitter/concurrency, polling/rate ceiling, dan maintenance window ditetapkan.
- [ ] Short retention, private storage, redaction, audit, dan downstream consumers ditetapkan.
- [ ] Negative write/control tests serta source-impact tests lulus memakai simulator.
- [ ] Kill switch diuji dan owner/incident contact tersedia.
- [ ] Tidak ada data menuju public CI, public artifact, external AI, atau Hermes.
- [ ] Expiry/review date dan rollback/disable procedure direkam.

Kegagalan satu item: NO-GO untuk source tersebut.
