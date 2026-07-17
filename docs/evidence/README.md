# Public-safe Development Evidence

Evidence files should be concise Markdown records, not raw logs.

Required fields:

- UTC date/time;
- commit/tag and issue/PR;
- scope and acceptance criterion;
- exact command or test name;
- result and duration/measurement method;
- synthetic fixture/provenance reference;
- limitation or failure disposition;
- owner/reviewer status.

Never include environment dumps, live endpoint/identity data, raw payloads, credentials, topology, unredacted screenshots, or large command output. Store private operational evidence in the governed private system and reference only its approved identifier.
