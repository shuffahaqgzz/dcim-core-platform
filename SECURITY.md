# Security Policy

## Supported status

The repository is prototype/alpha Development. No release is currently supported for Production deployment.

## Reporting a vulnerability

Do **not** disclose vulnerabilities, credentials, live endpoints, or operational evidence in a public issue, pull request, discussion, or Actions log.

Preferred reporting channel: GitHub private vulnerability reporting after the repository owner enables it. Until then, contact `@shuffahaqgzz` through a private pre-agreed channel and request a secure reporting path. Provide only the minimum information needed to establish contact in public.

Include affected commit/tag, impact, reproduction using synthetic data, and a remediation suggestion. Never include office/Production data.

## Security boundaries

- No direct OT/IT control path is permitted in Development.
- Source connectors are read-only and require negative tests for prohibited methods.
- CI uses GitHub-hosted runners and synthetic data only.
- A self-hosted runner connected to an office/Production network is prohibited until a separate security review.
- Security findings rated Critical or High block release unless formally accepted through the governed process.
