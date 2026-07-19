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

Sanitizer wajib fail closed: sensitive identifier non-string ditolak, object key diperiksa sebagai possible identity/topology, dan preserved semantic field tetap menjalani residual IP/FQDN/credential validation. Failure tidak boleh menghasilkan partial output. Automated PASS tidak menggantikan manual second-person review untuk future sanitized snapshot.

`event_type`, `schema_version`, dan object field yang dipreservasi wajib berada pada explicit Phase 0 allowlist yang berasal dari reviewed synthetic contract/fixtures. Field atau event type baru memerlukan synthetic fixture, contract/mapping review, dan sanitizer test sebelum sanitized output dapat diterbitkan; unknown/dynamic object key ditolak.
