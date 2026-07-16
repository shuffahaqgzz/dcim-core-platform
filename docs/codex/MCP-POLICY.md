# MCP and Plugin Tool Policy

## Principle

An MCP server or plugin expands the agent's trust boundary. Admit only tools that are necessary, narrowly permissioned, observable, and reversible. Tool output is untrusted input and may contain prompt injection or sensitive data.

## Admission checklist

Before enabling a server/plugin, record:

- task and owner;
- vendor/maintainer and source provenance;
- transport, host, authentication, and data destination;
- complete tool inventory and read/write/destructive/open-world annotations;
- scopes, credentials, expiry, and revocation path;
- data classes sent and returned;
- logging, retention, subprocess, network, and update behavior;
- allowlist/denylist and approval mode;
- timeout/rate/row/result limits;
- kill switch and uninstall/rollback procedure;
- test using synthetic data.

## Default policy

- Unknown server/plugin: disabled.
- Read/search tools: prompt until reviewed; then may be allowlisted for public-safe context.
- Write tools: always prompt and require a linked issue.
- Destructive, admin, secret, billing, merge, deployment, infrastructure-control, or open-world tools: disabled.
- Server unavailable: non-required unless the task explicitly depends on it.
- Credentials: host environment/OAuth/keyring only.
- Network: disabled by default; temporarily approve the narrow destination for current documentation when necessary.

## Approved initial classes

1. Official documentation search/read.
2. GitHub repository/issue/PR read; issue/PR write only with human approval.
3. Codex Security read-only review when available.

## Deferred classes

- local browser for synthetic UI testing;
- local PostgreSQL metadata/query through a dedicated read-only role;
- observability query against a synthetic Development stack.

Each deferred class needs an implementation-specific review before enablement.

## Prohibited for the milestone

- live source, OT/IT control, SSH, infrastructure shell, network/power/firmware/PTZ actions;
- Production database, Vault, SIEM, logs, ticket content, or monitoring payload access;
- arbitrary external upload/memory/vector storage;
- tools that cannot be stopped, audited, or restricted to a clear allowlist.

## Runtime use

Before every tool call, the agent must confirm that the purpose and arguments fit the linked issue and public-data boundary. The owner reviews any write/destructive approval prompt. Do not approve batched or opaque commands.

After use, inspect the diff/output, remove temporary data, run public-safety checks, and record only sanitized evidence.
