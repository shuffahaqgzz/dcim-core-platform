# Phase 1 Foundation Runbook

Date: 2026-07-21
Status: Development evidence
Issue: #12
Parent: #9

## Scope

This runbook covers the synthetic `dcim-build` Runtime Plane only. It does not
authorize `dcim-integration-ro`, `dcim-demo`, or any Production path.

## Prerequisites

- Ubuntu Server 24.04, `linux/amd64`;
- Docker Engine and the Compose plugin installed;
- Python 3.12-compatible standard library;
- GNU Make;
- No network access required for synthetic lifecycle;
- No package installation required.

## Lifecycle commands

All commands use the Make interface. The external runtime root defaults to
`${XDG_STATE_HOME:-$HOME/.local/state}/dcim-core-platform/runtime`. An explicit
`DCIM_RUNTIME_ROOT` override must remain paired with the state it bootstrapped.

| Command | Purpose |
|---|---|
| `make bootstrap` | Prepare a public-safe local workspace |
| `make foundation-bootstrap` | Create protected synthetic runtime material |
| `make foundation-images-qualify` | Build, reproduce, and scan local derived images |
| `make foundation-artifacts` | Fetch external JMX exporter artifact |
| `make foundation-policy` | Validate normalized Compose model |
| `make foundation-supply-chain` | Generate SBOM, license, and vulnerability evidence |
| `make foundation-up` | Start explicit synthetic foundation capabilities |
| `make foundation-stop` | Stop containers and preserve state |
| `make foundation-down` | Remove containers and networks, preserve state |
| `make foundation-smoke` | Run bounded synthetic fast smoke (5-minute deadline) |
| `make foundation-recovery` | Run restart and PostgreSQL restore checks (15-minute deadline) |
| `make foundation-grafana-url` | Resolve current internal Grafana URL |
| `make foundation-reset` | Interactively remove only `dcim-build` volumes (CI-prohibited) |
| `make foundation-evidence-summary` | Generate public-safe evidence summary |
| `make preflight` | Run all Development gates |

## Startup sequence

1. `make foundation-bootstrap` creates the external runtime root with
   owner-only traversal (`0700`) and secret files (`0444`). It refuses to
   overwrite existing material.
2. `make foundation-images-qualify` builds each derived image twice, verifies
   matching local image IDs and labels, produces SBOM, license, and
   vulnerability evidence outside Git, then writes `images.env` and
   `derived-images-lock.json` under the runtime root.
3. `make foundation-up` validates the normalized Compose model, starts the
   three explicit profiles (`data`, `observability`, `smoke`), and waits up to
   180 seconds for all services to become healthy.
4. Plain `docker compose up` without `--profile` starts nothing.

## Recovery procedure

`make foundation-recovery` proves:

1. PostgreSQL and Kafka synthetic state persists across restart;
2. Observability recovers (Prometheus targets, exporter backends, Grafana);
3. PostgreSQL `pg_dump` and restore with logical checksum verification;
4. All within a 15-minute deadline.

If recovery fails:

- Check container health: `docker compose ps` with the appropriate env files;
- Verify named volumes exist: `docker volume ls | grep dcim-build`;
- Review container logs: `docker compose logs <service>`;
- Do not modify volumes or secrets to mask failures.

## Failure handling

### Bootstrap failure

If `make foundation-bootstrap` fails:

- Verify the runtime root is outside the repository;
- Ensure no symbolic links exist in the runtime plane path;
- Check that the runtime root parent directory has correct permissions.

### Image qualification failure

If `make foundation-images-qualify` fails:

- A Critical vulnerability finding is NO-GO;
- A High finding with a fix is NO-GO;
- An unfixable High requires owner disposition;
- Do not lower the vulnerability gate.

### Policy failure

If `make foundation-policy` fails:

- Review the specific policy violation in the output;
- Common causes: missing digest, wrong profile, published port, non-internal
  network, shared volume;
- Do not modify policy tests to hide failures.

### Smoke failure

If `make foundation-smoke` or `make foundation-recovery` fails:

- The 5-minute (fast) or 15-minute (recovery) deadline is enforced;
- Evidence is still written to the external runtime root with `fail` status;
- Review the specific assertion failure in stderr;
- Timeouts are failures; the suite does not wait or retry without bound.

## Grafana Development access

Grafana publishes no host port. Access follows accepted ADR-0012:

```bash
make foundation-grafana-url
```

This resolves the current internal bridge address at runtime. The address may
change after container recreation and must be resolved again. No fixed container
address is stored in Git or evidence.

Credentials are in the external runtime root:

```text
${DCIM_RUNTIME_ROOT}/dev-build/secrets/grafana-admin-user
${DCIM_RUNTIME_ROOT}/dev-build/secrets/grafana-admin-password
```

## Evidence

Raw evidence is stored under the protected external runtime root:

```text
${DCIM_RUNTIME_ROOT}/dev-build/evidence/
```

Each evidence file contains: commit, image digests, capability profiles, UTC
timestamp, duration, assertion result, and synthetic run ID. No runtime secrets,
host details, credentials, or environment dumps are recorded.

Generate a public-safe summary:

```bash
make foundation-evidence-summary
```

## Limitations

- Single-broker Kafka KRaft: no HA, durability, or Production claim;
- No P1 or P2 vertical slice;
- No normalize, validate, DLQ/quarantine, enrichment, Asset/CI, analytics,
  workflow, SIEM/SOAR, or NOC application behavior;
- No event-to-dashboard latency or zero silent loss under workload;
- No Kafka backup claim;
- No continuous host-level telemetry;
- No office or Production source access;
- No Staging or Production readiness.

## Explicit non-claims

This runbook does not authorize:

- HA, SLA, scalability, or durability beyond the single Development VM;
- Staging entry or Production readiness;
- Connected-source integration or Hermes access;
- Write or control operations against any infrastructure;
- Remote or network access to any service.

## Stop controls

- `make foundation-stop`: stop containers, preserve volumes (60-second timeout);
- `make foundation-down`: remove containers and networks, preserve volumes;
- `make foundation-reset`: remove only `dcim-build` named volumes after
  interactive confirmation; unavailable in CI; restricted to the exact volume
  allowlist.

Emergency stop is a bounded smoke assertion, not an unbounded retry.
