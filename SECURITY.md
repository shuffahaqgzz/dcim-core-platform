# Kebijakan Security

## Status dukungan

Repository berada pada maturity Prototype/Alpha. Belum ada release yang didukung untuk deployment Production dan dokumen ini bukan klaim Production readiness.

## Pelaporan vulnerability

Do **not** disclose vulnerabilities, credentials, live endpoints, or operational evidence in a public issue, pull request, discussion, or Actions log.

Kanal pilihan: GitHub private vulnerability reporting setelah owner mengaktifkannya. Sebelum tersedia, hubungi `@shuffahaqgzz` melalui kanal private yang telah disepakati dan minta jalur pelaporan aman. Jangan membuka public issue berisi secret, endpoint, identifier, atau operational evidence. Security contact final masih open decision; handle owner hanya placeholder routing aman.

Sertakan affected commit/tag, impact, reproduction memakai synthetic data, dan remediation suggestion. Jangan sertakan office/Production data.

## Batas public repository dan private runtime

Code, schema, template, dan synthetic fixture yang public-safe boleh berada di Git. Credential, source inventory, endpoint, topology, raw payload/log/capture/dump, certificate, screenshot operasional, serta authorization record asli wajib berada pada private control plane di luar repository.

## Respons data exposure

1. Hentikan publish, CI, dan distribusi artifact terkait; jangan menyalin nilai exposure ke issue atau chat.
2. Revoke atau rotate credential melalui owner sistem terkait sebelum cleanup.
3. Catat hanya tipe exposure, path, commit reference, impact, dan status rotasi pada incident record private.
4. Tentukan kebutuhan history rewrite bersama owner; jangan menjalankan destructive rewrite otomatis.
5. Validasi ulang history, clone bersih, cache/artifact, dan downstream consumer sebelum membuka kembali gate.

Credential rotation harus menghasilkan identity baru, mencabut identity lama, memperbarui private secret store, menguji read-only scope, dan merekam approval/expiry di private register. Nilai credential tidak boleh masuk evidence publik.

## Security boundaries

- Direct OT/IT control path dilarang pada Development.
- Source connector wajib read-only dan memiliki negative tests untuk prohibited methods.
- CI hanya memakai GitHub-hosted runner dan synthetic data.
- Self-hosted runner dengan office/Production route dilarang sampai separate security review.
- Critical/High security finding memblokir release kecuali diterima melalui governed process.
