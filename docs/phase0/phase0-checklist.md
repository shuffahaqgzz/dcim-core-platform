# Phase 0 Checklist

## Repository dan governance

- [x] Repository inventory dan bounded history review dibuat.
- [x] Charter, scope, limitations, roadmap, dan data boundary terdokumentasi.
- [x] License tetap open decision; tidak ada `LICENSE` ditambahkan.
- [x] Owner mengaktifkan dan memverifikasi `main-development-gate` ruleset serta required checks.

## Safety dan architecture

- [x] Three-plane design, promotion, failure, dan stop conditions terdokumentasi.
- [x] Read-only policy/template/checklist/kill switch tersedia.
- [x] Demo sanitization policy, sanitizer, dan synthetic fixtures tersedia.
- [x] Threat model Phase 0 tersedia.
- [x] CI memakai GitHub-hosted runner dan synthetic data only.
- [x] Hermes tetap disabled dan tidak menerima tool/data/credential.

## Evidence dan owner boundary

- [x] Historical local gates PR #2 lulus; corrective adversarial review kemudian menemukan gap.
- [x] Remote PR #2 checks lulus untuk PR event range; hasil ini bukan full-history proof.
- [ ] Corrective local/remote gates lulus pada exact corrective PR head.
- [x] Actual full-history `workflow_dispatch` terhadap current `main` lulus pada run `29699171363`, target `11fc8c6`.
- [ ] Owner menyetujui ADR crosswalk/numbering dan read-only policy pada exact corrective PR head.
- [ ] Independent read-only re-review PASS sebelum corrective merge.

Checklist ini tidak menutup condition register; hanya owner berwenang mengubah status condition.
