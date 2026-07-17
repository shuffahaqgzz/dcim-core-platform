# Emergency Collector Kill Switch

## Trigger

Aktifkan saat authorization expired/missing, write permission terlihat, source health terdampak, polling tidak terkendali, data egress salah, credential exposure, cross-plane reuse, audit hilang, atau operator tidak dapat memastikan read-only behavior.

## Urutan aman

1. Disable collector melalui control yang tidak mengirim request baru; default state harus disabled.
2. Putus egress route/allowlist pada `dcim-integration-ro` melalui authorized private operator process.
3. Revoke dedicated credential bila exposure atau privilege mismatch terjadi.
4. Preserve minimum private audit metadata tanpa menyalin payload/secret ke Git.
5. Verifikasi request berhenti dan source pulih melalui owner sumber.
6. Quarantine private runtime output; jangan publish log/screenshot.
7. Buka kembali hanya setelah root cause, negative tests, authorization, dan owner approval lengkap.

Phase 0 hanya mendokumentasikan proses. Tidak ada executable network/firewall control di repository ini.
