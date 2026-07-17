# Phase 0 Checklist

## Repository dan governance

- [x] Repository inventory dan bounded history review dibuat.
- [x] Charter, scope, limitations, roadmap, dan data boundary terdokumentasi.
- [x] License tetap open decision; tidak ada `LICENSE` ditambahkan.
- [ ] Owner memverifikasi branch protection/required checks.

## Safety dan architecture

- [x] Three-plane design, promotion, failure, dan stop conditions terdokumentasi.
- [x] Read-only policy/template/checklist/kill switch tersedia.
- [x] Demo sanitization policy, sanitizer, dan synthetic fixtures tersedia.
- [x] Threat model Phase 0 tersedia.
- [x] CI memakai GitHub-hosted runner dan synthetic data only.
- [x] Hermes tetap disabled dan tidak menerima tool/data/credential.

## Evidence dan owner boundary

- [x] Semua local gates final lulus dan evidence index terisi.
- [x] Remote CI dan full-history gitleaks lulus pada draft PR #2.
- [ ] Owner menyetujui proposed ADR crosswalk/numbering melalui PR review.
- [ ] Owner review dan approval sebelum merge.

Checklist ini tidak menutup condition register; hanya owner berwenang mengubah status condition.
