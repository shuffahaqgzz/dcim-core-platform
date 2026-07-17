# Codex Operator Setup — DCIM Core Platform

This guide configures Codex as a constrained Development assistant. Repository files define project instructions, skills, and subagents; plugins, authentication, and most MCP credentials remain host/user configuration.

## 1. Prepare the Development host

Recommended baseline:

- Ubuntu Server 24.04;
- Git, Python 3.12+, GNU Make;
- Docker Engine and the Docker Compose plugin when platform implementation begins;
- no default route from DEV-BUILD to office/Production management networks;
- a non-root developer account with narrowly scoped Docker access;
- protected credential storage outside the repository.

Clone into the mutable Development workspace:

```bash
mkdir -p ~/src
cd ~/src
git clone https://github.com/shuffahaqgzz/dcim-core-platform.git
cd dcim-core-platform
./scripts/bootstrap-dev.sh
make preflight
```

The script creates only public-safe local directories outside the repository. Do not copy live environment files into the worktree.

## 2. Install and authenticate Codex

For macOS/Linux, use the current official standalone installer:

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex --version
```

Start Codex from the repository and choose the approved ChatGPT sign-in method:

```bash
cd ~/src/dcim-core-platform
codex
```

Review the project before trusting it. After trust is granted, Codex can load `.codex/config.toml`, `AGENTS.md`, project skills, and custom subagents. In the session run:

```text
/status
/permissions
/mcp
```

Expected project posture:

- approval policy: interactive/on-request;
- approval reviewer: user;
- filesystem: workspace-write;
- outbound network inside the workspace sandbox: disabled;
- `/tmp` and `$TMPDIR`: not writable roots through the workspace sandbox;
- subagent depth: one; maximum concurrent threads: four.

Do not launch this project with unrestricted/yolo permissions. Do not pin a model in Git; select an available model and reasoning level per task, because availability and naming can change.

## 3. Repository-provided agent assets

- `AGENTS.md` — global decision, safety, quality, and Git behavior.
- `.codex/config.toml` — conservative project sandbox and delegation defaults.
- `.codex/agents/` — architect, implementer, reviewer, security reviewer, documentation researcher, and evidence writer.
- `.agents/skills/` — baseline, data safety, connectors, schemas, ADRs, and PR evidence workflows.
- `docs/codex/PROMPT-CATALOG.md` — bounded copy/paste prompts.
- `docs/codex/MCP-POLICY.md` — tool admission and approval policy.

Codex discovers repository skills under `.agents/skills`; each skill includes a `SKILL.md` with trigger metadata. Project custom agents are standalone TOML files under `.codex/agents`.

## 4. Recommended plugins

Install plugins through the Codex/ChatGPT Plugins interface available to the approved account. Plugin names and IDs can vary by marketplace/workspace; inspect requested permissions before installation.

| Plugin | Use | Initial policy |
|---|---|---|
| GitHub (OpenAI curated where available) | Read issues/PRs/checks; open or update owner-approved PRs/issues | read/search allowed; write operations prompt for user approval; no merge/delete/admin actions |
| OpenAI Developers / Docs | Verify current Codex/OpenAI configuration and API behavior | read/search only; send no repository data beyond generic queries |
| Codex Security | Review code changes and threat-model findings | read-only review first; fixes require a separate issue/approval |

Do not install broad email, calendar, cloud-admin, SSH, infrastructure-control, database-write, browser-recording, or generic automation plugins for this project unless a task-specific ADR and permission review approve them.

A plugin is not trusted merely because it is installed. Restrict bundled MCP tools to the minimum allowlist and keep writes in prompt/approval mode.

## 5. MCP baseline

### 5.1 OpenAI Developer Docs MCP — recommended, read-only

Review [`USER-CONFIG.example.toml`](USER-CONFIG.example.toml), then merge only the approved block into the user-level `~/.codex/config.toml` after approving network access:

```toml
[mcp_servers.openaiDeveloperDocs]
url = "https://developers.openai.com/mcp"
enabled = true
required = false
default_tools_approval_mode = "prompt"
startup_timeout_sec = 10
tool_timeout_sec = 45
```

Use it only for current OpenAI/Codex facts. It does not need DCIM source data.

### 5.2 GitHub — recommended through the curated plugin

Prefer the approved GitHub plugin instead of placing a personal token in project configuration. Start with repository metadata, files, issues, pull requests, diffs, and CI read access. Require a user prompt for creating/updating issues or PRs. Keep merge, branch deletion, settings, secrets, Actions administration, and repository deletion unavailable to the agent.

### 5.3 Optional local Development database MCP — defer

Only add after selecting and reviewing a specific implementation. Requirements:

- local/synthetic Development PostgreSQL only;
- dedicated database role restricted to `SELECT` and safe metadata views;
- no office route and no Production connection string;
- credentials from protected environment/keyring, never Git;
- query timeout, row limit, schema allowlist, and audit log;
- tool approval mode `prompt` or stricter.

### 5.4 Browser MCP — defer until the UI decision

A browser tool may be useful for local NOC dashboard testing after OD-03 is accepted. Limit it to a local synthetic app, block arbitrary external navigation, and treat screenshots/console/network output as potentially sensitive.

### 5.5 Prohibited initially

- Docker/Kubernetes admin MCP with unrestricted lifecycle access;
- SSH, WinRM, Ansible, or shell MCP targeting infrastructure;
- direct Redfish/SNMP/ISAPI control tools;
- Production database/log/SIEM/Vault MCP;
- external memory/vector-store MCP containing project or source data;
- generic web/browser access during connected-source work.

Use `codex mcp list`, `codex mcp --help`, and `/mcp` to inspect active servers. OAuth and bearer credentials remain in host-managed storage/environment, never the repo.

## 6. First-session verification

From a clean branch, ask Codex:

```text
Read AGENTS.md, the Development baseline, conditions register, open decisions,
and all repository skills. Do not edit anything. Report the project gate,
public/private boundary, auto-NO-GO conditions, unresolved ADRs, available
subagents, active MCP servers, current sandbox/approval posture, and the exact
commands you would run for preflight. Flag any mismatch before continuing.
```

Then run:

```bash
make preflight
git status --short
```

Expected result: all checks pass and the worktree remains clean.

## 7. Per-issue execution pattern

1. Create/select a GitHub issue with testable acceptance criteria.
2. Start a new branch from current `main`.
3. Ask Codex to use `architect`; owner approves the plan.
4. Ask `implementer` to change only the approved scope.
5. Run tests and review the diff.
6. Delegate read-only review to `reviewer` and `security_reviewer`.
7. Fix findings in a bounded follow-up turn.
8. Run `make preflight` plus component gates.
9. Ask `evidence_writer` for a sanitized evidence summary.
10. Open a pull request; never let an agent merge without an explicit owner action.

## 8. Credential rules

- Prefer ChatGPT/OAuth and GitHub App/plugin authentication over long-lived personal tokens.
- Never paste a token into a prompt, shell command that enters history, issue, PR, `.env.example`, log, screenshot, or evidence file.
- When an API key is unavoidable, inject it from a protected host environment or keyring and restrict its scope/expiry.
- Revoke and rotate first when exposure is suspected.

## 9. Update cadence

At least monthly, and before a release candidate:

- update Codex from the official installer;
- inspect Codex config deprecations and feature maturity;
- review installed plugin/MCP permissions;
- remove unused servers and credentials;
- update pinned GitHub Action commit SHAs through a reviewed dependency PR;
- run a clean-machine bootstrap and document the result.
