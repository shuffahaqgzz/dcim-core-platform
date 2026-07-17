---
name: public-repo-safety
description: Use before adding fixtures, logs, screenshots, configuration, prompts, evidence, connector examples, or GitHub automation to this public repository. Trigger whenever data provenance or secrecy could be relevant.
---

# Public Repository Safety

1. Treat every file, issue, PR, action log, prompt, and tool transcript as publicly discoverable.
2. Allow only generic code, schemas, templates, synthetic fixtures, reserved domains, and reviewed sanitized evidence.
3. Reject real or suspected-real endpoints, IPs, hostnames, FQDNs, serials, asset tags, topology, credentials, community strings, raw payloads, packet captures, logs, dumps, certificates, keys, videos, and unredacted screenshots.
4. Never ask the user to paste sensitive material into Codex. Request a synthetic reproduction or a separately governed private process.
5. Run `python3 scripts/check-public-safety.py` and inspect the diff manually.
6. When uncertain, stop. Describe the suspected classification issue without repeating the sensitive value.
7. For accidental exposure, rotate/revoke first, then perform governed history cleanup and a sanitized incident record.
