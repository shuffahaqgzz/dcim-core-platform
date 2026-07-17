# Read-Only Connector Policy

Phase 0 tidak membuat connector atau koneksi aktif. Future connector wajib memiliki written authorization private, dedicated least-privilege identity, TLS verification bila tersedia, endpoint allowlist, bounded timeout/retry/jitter/concurrency, polling ceiling, short retention, audit, source-impact metrics, dan kill switch yang default-safe.

## Protocol allowlist dan denylist

- **Redfish:** hanya `GET` pada resource health/inventory yang disetujui. Tolak `POST`, `PATCH`, `PUT`, `DELETE`, action, power/reset, firmware, account, BIOS, dan virtual media.
- **SNMP:** hanya `GET`, `GETNEXT`, `GETBULK`, dan bounded `WALK`; `SET` selalu ditolak. Utamakan SNMPv3 authPriv. SNMPv2c hanya temporary Development exception dengan source-IP ACL, private community handling, expiry, dan migration plan.
- **ISAPI:** hanya `GET` health/alarm metadata. Tolak `PUT`, `POST`, `DELETE`, PTZ, reboot, configuration, user management, recording export, dan video download.
- **CSV:** baca sanitized working copy; quarantine malformed record dengan reason. Office export asli tidak boleh masuk repository atau demo.
- **Metrics:** read-only scrape/query pada endpoint terotorisasi dengan rate limit. Admin, mutation, remote-write, dan generic query passthrough dilarang.

## Enforcement dan verification

Tidak boleh ada generic method dispatch, raw shell, privileged SQL, arbitrary Kubernetes command, atau pass-through device action. Negative tests wajib membuktikan semua write/control class tidak reachable, termasuk authentication failure, timeout, malformed payload, rate limit, duplicate, dan kill-switch behavior. Operational metric tidak boleh memuat endpoint atau credential.
