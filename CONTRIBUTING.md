# Kontribusi

Project berada pada Prototype/Alpha Development yang dipimpin owner. Ketentuan kontribusi eksternal tetap terbatas sampai license dipilih.

Branch memakai `feat/<scope>`, `fix/<scope>`, `docs/<scope>`, `chore/<scope>`, atau `adr/<decision>`. Commit memakai Conventional Commits dengan imperative subject. Jangan force-push atau merge langsung ke `main` tanpa approval owner.

## Sebelum mulai

1. Baca `AGENTS.md`, `DATA-HANDLING.md`, Development baseline, dan ADR terkait.
2. Buat atau tautkan GitHub issue dengan acceptance criteria eksplisit.
3. Pastikan task tidak memerlukan live office/Production data.
4. Untuk unresolved architecture choice, ajukan ADR sebelum implementasi.

## Verifikasi lokal

```bash
./scripts/bootstrap-dev.sh
make preflight
```

Perintah test component-specific wajib didokumentasikan pada README terdekat dan pull request.

## Pull request

Pertahankan satu concern koheren per pull request. Sertakan scope/out-of-scope, linked issue/ADR, command/result, data-handling declaration, migration/recovery impact, dan known limitations.

Fixture wajib sepenuhnya synthetic. Setiap perubahan behavior atau decision memperbarui dokumentasi. Jalankan unit/contract/integration test yang relevan, secret/public-safety scan, dependency/license review, serta `make preflight`. Pertimbangkan compatibility, migration, dan rollback.

Owner hanya boleh memberi `DEV-APPROVED` setelah required evidence tersedia. Status tersebut bukan Staging atau Production approval.
