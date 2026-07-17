# Template Private Source Authorization Register

> Simpan record terisi pada private approved system. Jangan commit copy terisi ke repository ini.

| Field | Value |
|---|---|
| source_id | `<PRIVATE-REFERENCE>` |
| source type | `<Redfish/SNMP/ISAPI/CSV/Metrics>` |
| business owner | `<PRIVATE-REFERENCE>` |
| technical owner | `<PRIVATE-REFERENCE>` |
| approval reference | `<PRIVATE-REFERENCE>` |
| environment | `<ENVIRONMENT>` |
| data classification | `<CLASSIFICATION>` |
| protocol | `<PROTOCOL>` |
| allowed operations | `<EXPLICIT-READ-ALLOWLIST>` |
| prohibited operations | `<EXPLICIT-DENYLIST>` |
| credential reference | `<SECRET-STORE-REFERENCE; NEVER SECRET>` |
| polling interval | `<VALUE>` |
| rate limit | `<VALUE>` |
| timeout | `<VALUE>` |
| maintenance window | `<VALUE>` |
| fields collected | `<MINIMUM-FIELDS>` |
| retention | `<VALUE>` |
| downstream consumers | `<APPROVED-CONSUMERS>` |
| audit location | `<PRIVATE-REFERENCE>` |
| kill-switch procedure | `<PRIVATE-RUNBOOK-REFERENCE>` |
| incident contact | `<PRIVATE-REFERENCE>` |
| expiration/review date | `<YYYY-MM-DD>` |

Approval wajib mencatat bahwa identity dedicated read-only telah diuji dan network/egress allowlist aktif.
