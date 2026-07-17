# Template Source Inventory

> Template public-safe. Record terisi wajib private. Gunakan opaque reference; jangan masukkan IP, hostname, serial, lokasi, username, atau credential.

| source_id | type | owner ref | authorization ref | classification | protocol | read allowlist | polling/rate ceiling | credential ref | retention | review date | status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `<OPAQUE-ID>` | `<TYPE>` | `<PRIVATE-REF>` | `<PRIVATE-REF>` | `<CLASS>` | `<PROTOCOL>` | `<READS>` | `<LIMIT>` | `<SECRET-STORE-REF>` | `<VALUE>` | `<DATE>` | `<DISABLED/PENDING/APPROVED>` |

Status default `DISABLED`. `APPROVED` hanya boleh diberikan oleh authority yang tercatat dan tidak mengaktifkan connector secara otomatis.
