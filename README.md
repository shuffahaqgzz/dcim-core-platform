# DCIM Core Platform

Public development repository for the **DCIM Core Platform**. The current milestone is **Dev Platform Bootstrap v0.1**: prove compact deployability for the major platform components and one integrated P1/P2 vertical slice. This repository does **not** claim Production readiness, high availability, SLA compliance, or safe control of OT/IT equipment.

## Current decision

- Gate: **CONDITIONAL GO**; maturity: **prototype/alpha**.
- Operator model: solo Development, controlled handover, multi-team Staging, governed Production.
- Development target: Ubuntu Server 24.04 VM, 32 vCPU, 64 GB RAM, 500 GB SSD, 24 GB VRAM, 1 Gbps.
- Orchestration: Docker Compose profiles for Development; Kubernetes is deferred.
- State and messaging: PostgreSQL, Redis, single-broker Kafka KRaft in Development.
- Observability and UX: Prometheus/Grafana plus a NOC-oriented Web Dashboard/API.
- Automation: notification, ticket draft, approval simulation, dry-run, or mock action only.
- Hermes: read-only, non-blocking shadow mode after the data-pipeline gate.

The sanitized authoritative development summary is in [`docs/baseline/DEVELOPMENT-BASELINE.md`](docs/baseline/DEVELOPMENT-BASELINE.md). Open conditions are tracked in [`docs/governance/CONDITIONS-REGISTER.md`](docs/governance/CONDITIONS-REGISTER.md).
The executable 10-day plan is in [`docs/plan/DEV-BOOTSTRAP-V0.1.md`](docs/plan/DEV-BOOTSTRAP-V0.1.md), and owner-only GitHub settings are in [`docs/runbooks/GITHUB-REPOSITORY-SETUP.md`](docs/runbooks/GITHUB-REPOSITORY-SETUP.md).

## Public-code / private-runtime boundary

Allowed here: generic source code, generic schemas, synthetic fixtures, sanitized examples and public-safe evidence.

Never commit: live endpoints, IP addresses, hostnames, serial numbers, rack/site topology, credentials, SNMP community strings, raw payloads, packet captures, logs, database dumps, certificates, keys, tokens, camera/NVR details, unredacted screenshots, or prompts containing operational evidence. See [`DATA-HANDLING.md`](DATA-HANDLING.md).

## Quick start

```bash
git clone https://github.com/shuffahaqgzz/dcim-core-platform.git
cd dcim-core-platform
./scripts/bootstrap-dev.sh
make preflight
```

`bootstrap-dev.sh` prepares only a local, public-safe workspace. It does not connect to office/Production systems and does not install platform services.

## Repository map

```text
.agents/skills/       repository-scoped Codex skills
.codex/               Codex project config and subagents
.github/              pull-request templates and CI guardrails
connectors/           read-only connector implementations
contracts/            API and event contract notes
schemas/              JSON Schemas
fixtures/synthetic/   public-safe fixtures only
services/             platform service boundaries
platform/             infrastructure and Compose implementation
web/                  NOC-oriented UI
scripts/              local/CI verification tools
tests/                safety and contract tests
docs/                 baseline, ADRs, task plan, evidence and runbooks
```

## Contribution and license status

Development is currently owner-led. Every change goes through a focused branch, evidence-producing checks, and a pull request. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`AGENTS.md`](AGENTS.md).

No open-source license has been selected yet. The repository is publicly visible, but reuse and external contribution terms remain undefined until the owner closes the license decision. See [`docs/governance/LICENSE-DECISION.md`](docs/governance/LICENSE-DECISION.md).
