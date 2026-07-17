# Demo Sanitization Policy

Synthetic data adalah pilihan utama. Sanitized snapshot hanya future exception dengan private provenance, owner approval, dan public-safety review.

| Input class | Public-safe transformation |
|---|---|
| hostname/FQDN | stable pseudonym pada `example.com` |
| IP | deterministic address pada RFC 5737 documentation range |
| serial number | stable `SYNTHETIC-SERIAL-*` |
| site/building/room/rack | generic location |
| NVR/camera name | generic stable identifier |
| account/user | synthetic stable account |
| timestamp | controlled deterministic offset |
| raw message | redacted atau regenerated tanpa free text asli |
| URL | documentation domain/IP tanpa query secret |
| vendor credential reference | removed |

Salt diberikan saat eksekusi, tidak di-hardcode, tidak di-log, dan tidak dipakai ulang antar release bila linkability tidak dibutuhkan. Correlation harus konsisten dalam satu dataset. Output mendapat automated scan dan manual review; hasil yang masih memuat direct/quasi identifier, small-population topology, atau unique operational pattern wajib ditolak.
