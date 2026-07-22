# Issue #9 Acceptance Matrix — Phase 1 Compact Infrastructure Foundation

Date: 2026-07-21
Scope: synthetic `dcim-build` Runtime Plane only
Parent issue: #9
Status: clean-runtime completion captured on external runtime; pending final
pushed-head remote checks and owner disposition.

This matrix treats the 50 numbered user stories in issue #9 as the parent
acceptance rows. The issue's implementation, testing, and out-of-scope sections
remain governing constraints.

## Current closure classification counts

| Classification | Count |
|---|---:|
| Verified by current evidence | 20 |
| Verified by isolated clean-runtime run | 25 |
| Superseded by accepted ADR | 2 |
| Out of scope according to issue #9 | 1 |
| Owner disposition required | 1 |
| Pending remote-hosted runner evidence | 1 |
| Remaining issue #9 closure blockers | 2 |
| Unresolved implementation defects in this candidate | 0 |

Rows classified as "Verified by isolated clean-runtime run" are proven by passing
`make foundation-clean-acceptance` with
`DCIM_RUNTIME_ROOT=<new-protected-root>` on the implementation-candidate head
identified by the recorded public-safe external summary. Ordinary `make
preflight` is the normal Development gate and may reuse selected protected state;
it is not clean-runtime proof. This matrix lists the remaining remote-hosted proof
and owner-action gaps above the local pass-clean proof.

PR #16 remote checks passed on pre-reconciliation head
`872df38a4ede87d129533965b28ca335672916bc`, but any local documentation
reconciliation commit creates a later final pushed head. Row 42 therefore remains
pending until remote-hosted runner evidence passes on that final pushed head.

## Matrix

| # | Requirement summary | Classification | Evidence or governing source |
|---:|---|---|---|
| 1 | Explicit bootstrap command | Verified by isolated clean-runtime run | `make foundation-clean-acceptance`; `scripts/foundation_acceptance.py`; `scripts/foundation_bootstrap.py` |
| 2 | Plain Compose without profiles starts nothing | Verified by current evidence | `tests/test_foundation_lifecycle.py::test_plain_compose_without_profiles_selects_no_services`; `scripts/foundation_policy.py` |
| 3 | Explicit `data`, `observability`, and `smoke` profiles | Verified by current evidence | `deploy/compose/dev-build/compose.yaml`; `scripts/foundation_policy.py` profile checks |
| 4 | Runtime Planes are distinct from Capability Profiles | Verified by current evidence | `deploy/compose/README.md`; `docs/plan/PHASE1-COMPACT-INFRASTRUCTURE-FOUNDATION.md` |
| 5 | Only synthetic build-plane lifecycle is runnable; integration and demo planes are not runnable | Verified by current evidence | Normal Make lifecycle pins `COMPOSE_PROJECT_NAME=dcim-build`; clean acceptance may use only the guarded `dcim-build-acceptance-*` namespace; `deploy/compose/integration-ro/README.md`; `deploy/compose/demo/README.md` |
| 6 | Integration and demo planes are contract-only | Verified by current evidence | `deploy/compose/integration-ro/README.md`; `deploy/compose/demo/README.md` |
| 7 | PostgreSQL persistent state | Verified by isolated clean-runtime run | clean acceptance fast/recovery evidence; `scripts/foundation_smoke.py` PostgreSQL persistence checks |
| 8 | Single-broker Kafka KRaft | Verified by isolated clean-runtime run | clean acceptance policy/recovery evidence; Kafka environment contract in `scripts/foundation_policy.py` |
| 9 | Redis omitted until justified | Verified by current evidence | Compose service allowlist in `scripts/foundation_policy.py` excludes Redis |
| 10 | Application services omitted | Out of scope according to issue #9 | Issue #9 out-of-scope section; `scripts/foundation_policy.py` service allowlist |
| 11 | Grafana host-loopback publication | Superseded by accepted ADR | ADR-0012 accepts zero published ports and runtime-resolved internal bridge access |
| 12 | PostgreSQL, Kafka, and Prometheus internal-only | Verified by current evidence | Network and port checks in `scripts/foundation_policy.py` |
| 13 | Only approved metrics exporters are dual-homed | Verified by current evidence | `DUAL_HOMED` allowlist and network checks in `scripts/foundation_policy.py` |
| 14 | Exporters disable IP forwarding | Verified by current evidence | exporter `sysctls` checks in `scripts/foundation_policy.py` |
| 15 | Persistent volumes isolated by service and plane | Verified by isolated clean-runtime run | acceptance namespace inventory in `scripts/foundation_acceptance.py`; policy volume checks |
| 16 | Grafana declarative provisioning with disposable state | Verified by isolated clean-runtime run | clean acceptance Grafana smoke; Grafana tmpfs/provisioning policy checks |
| 17 | Runtime secrets generated outside Git | Verified by isolated clean-runtime run | clean acceptance bootstrap; `scripts/protected_runtime.py`; public-safety scan |
| 18 | Secret-file or `_FILE` delivery | Verified by current evidence | secret allowlist and environment checks in `scripts/foundation_policy.py`; PostgreSQL argv guard tests |
| 19 | Official upstream image set only | Superseded by accepted ADR | ADR-0013/0014/0015 permit five local Development-only derived hardened images; only the JMX runtime remains qualified upstream |
| 20 | Provenance, architecture, license, SBOM, scanner, vulnerability evidence | Verified by isolated clean-runtime run | `foundation-images-qualify`; `foundation-supply-chain`; derived-image lock and external evidence |
| 21 | Critical/fixable High block; unfixable High owner disposition | Owner disposition required | policy in issue #9 and ADR-0013; `scripts/foundation_supply_chain.py`; issue #10 license/vulnerability disposition remains owner-authority-bound |
| 22 | CPU and memory limits within 10 vCPU/18 GiB | Verified by current evidence | aggregate resource checks in `scripts/foundation_policy.py` |
| 23 | 100 GiB disk budget and bounded retention | Verified by current evidence | Kafka/Prometheus retention checks in `scripts/foundation_policy.py`; Phase 1 plan |
| 24 | Logical storage alerts at 70/85/90 percent | Verified by current evidence | Prometheus rule checks in `scripts/foundation_smoke.py`; `deploy/compose/dev-build/config/prometheus/rules.yml` |
| 25 | Smoke writes refused at 90 percent usage | Verified by isolated clean-runtime run | clean acceptance fast smoke; `capacity_disposition` and regression tests |
| 26 | Health checks for every long-running service | Verified by isolated clean-runtime run | clean acceptance `foundation-up --wait`; health contracts in `scripts/foundation_policy.py` |
| 27 | Functional smoke separate from health status | Verified by isolated clean-runtime run | clean acceptance fast/recovery smoke commands |
| 28 | Prometheus exposes health, scrape, Kafka, PostgreSQL, and retention signals | Verified by isolated clean-runtime run | clean acceptance observability smoke; Prometheus config/rules |
| 29 | Grafana shows foundation health and capacity | Verified by isolated clean-runtime run | clean acceptance Grafana health/datasource smoke; dashboard provisioning files |
| 30 | Observability avoids privileged host collectors and external telemetry | Verified by current evidence | privilege, namespace, mount, and service allowlists in `scripts/foundation_policy.py` |
| 31 | PostgreSQL write/read smoke | Verified by isolated clean-runtime run | clean acceptance fast/recovery smoke evidence |
| 32 | Kafka produce/consume smoke with exact run ID | Verified by isolated clean-runtime run | clean acceptance fast/recovery smoke evidence |
| 33 | Single allowlisted Kafka topic and 1 MiB ceiling | Verified by isolated clean-runtime run | clean acceptance fast smoke; Kafka topic/message checks |
| 34 | Kafka-managed internal topics reported separately | Verified by isolated clean-runtime run | clean acceptance smoke output/evidence; `kafka_topic_inventory` |
| 35 | Prometheus target, rule, and controlled-alert smoke | Verified by isolated clean-runtime run | clean acceptance fast smoke; `controlled_alert_transition` |
| 36 | Exporter-to-backend health verified separately | Verified by isolated clean-runtime run | clean acceptance observability smoke; `pg_up` and JMX metric checks |
| 37 | Grafana health and datasource provisioning tested | Verified by isolated clean-runtime run | clean acceptance Grafana smoke |
| 38 | Restart recovery for PostgreSQL, Kafka, and observability | Verified by isolated clean-runtime run | clean acceptance recovery smoke |
| 39 | PostgreSQL dump/restore with logical checksum | Verified by isolated clean-runtime run | clean acceptance recovery smoke |
| 40 | Machine-readable smoke evidence outside Git | Verified by isolated clean-runtime run | external `dev-build/evidence/*.json`; `scripts/foundation_evidence_summary.py` strict mode |
| 41 | Only reviewed public-safe summaries are promoted | Verified by current evidence | `scripts/check_public_repo_safety.py`; evidence allowlist tests |
| 42 | Fast smoke on GitHub-hosted Ubuntu 24.04 runners | Pending remote-hosted runner evidence | PR #16 checks passed on pre-reconciliation head `872df38a4ede87d129533965b28ca335672916bc`; final pushed head remote-hosted runner evidence remains required |
| 43 | GitHub Actions and scanner containers pinned | Verified by current evidence | `.github/workflows/`; scanner digest in `scripts/foundation_supply_chain.py` and recipes |
| 44 | Bounded startup, smoke, recovery, and stop timeouts | Verified by isolated clean-runtime run | clean acceptance step durations and exit codes; Make/Compose timeout settings |
| 45 | Bounded restart attempts | Verified by current evidence | `restart: "on-failure:3"` policy checks |
| 46 | Stop/down preserve data | Verified by isolated clean-runtime run | clean acceptance bounded stop; existing stop/down lifecycle tests |
| 47 | Reset targets only `dcim-build` volumes after confirmation | Verified by current evidence | `scripts/foundation_reset.py`; reset guard tests |
| 48 | Normalized Compose policy checks fail closed | Verified by isolated clean-runtime run | clean acceptance policy step; `tests/test_foundation_policy.py` |
| 49 | Every service checked for profiles, pins, health, limits, networks, volumes, logging, privileges | Verified by current evidence | `scripts/foundation_policy.py`; `tests/test_foundation_policy.py` |
| 50 | Acceptance evidence states explicit non-claims | Verified by current evidence | `docs/phase1/DEVELOPMENT-HANDOVER.md`; `docs/phase1/FOUNDATION-RUNBOOK.md`; issue #9 closure text must preserve non-claims |

## Condition and open-decision handling

- C-03: evidence advances runtime-plane separation, but status remains `OPEN`.
- C-05: unchanged because `dcim-demo` remains non-executable.
- C-07: evidence advances resource/retention visibility, but status remains
  `OPEN`.
- OD-06: unchanged; public visibility and local Development image use do not
  grant publication, distribution, or repository-license approval.

Only the owner may change these statuses or approve issue #9 closure.
