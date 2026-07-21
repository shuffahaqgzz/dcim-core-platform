# Issue #11 Synthetic Foundation Lifecycle Regression — PASS

Date: 2026-07-21  
Issue: #11; parent: #9  
Scope: local synthetic `dcim-build` Development foundation only

Verification subject: implementation commit
`853145f8ea5b9ed3500582d86063ad67a1846d9d`. This record is not the empty-runtime
milestone evidence required by the parent Phase 1 plan.

## Result

The foundation lifecycle passed against the protected runtime state established
by issue #10. No named volume was reset or deleted. The checkout-independent
XDG state root is now the shared default for workspace bootstrap and Make, so a
temporary worktree cannot silently select different bootstrap material.

All raw JSON, SBOM, license, vulnerability, dump, runtime identity, and local
image evidence remained under the protected external runtime root. This record
contains only public-safe aggregate outcomes.

## Acceptance evidence

| Contract | Public-safe result |
| --- | --- |
| Immutable image qualification | PASS — four derived images were rebuilt twice from exact public pinned inputs; clean second builds matched; the lock binds the recipe and accepted license disposition |
| Supply chain | PASS — PostgreSQL, Kafka, Prometheus, Grafana OSS, PostgreSQL exporter, and JMX exporter Java runtime each reported zero critical, zero fixable-high, and zero undispositioned unfixable-high findings |
| Capability Profiles | PASS — normalized policy requires exact `data`, `observability`, and `smoke` membership; plain Compose selects zero services |
| Runtime safety | PASS — exact project, networks, mounts, service owners, process commands, health checks, resource limits, retention, Kafka settings, and privilege denials are enforced fail-closed |
| Protected bootstrap | PASS — checkout-independent XDG default, owner-only directories, non-symlink path components, no overwrite, and approved read-only secret mounts |
| Fast smoke | PASS in 79.4 seconds — the controlled 90% contract guard refused before the PostgreSQL/Kafka write functions were reached; normal-capacity PostgreSQL/Kafka round trips, offset-based rejection above the 1 MiB Kafka ceiling, exporters, Prometheus targets/rules, active controller, Grafana datasource query, and a controlled alert transition also passed |
| Recovery | PASS in 48.4 seconds — pre-restart PostgreSQL row and exact Kafka offset survived; observability converged; PostgreSQL dump/restore checksum matched |
| Stop/down preservation | PASS — `foundation-stop` and `foundation-down` retained exactly the three allowlisted named data volumes; startup and recovery then passed using the same state |
| Reset control | PASS by contract tests — unavailable in CI, requires an interactive terminal, and rejects any unexpected labelled volume before confirmation |
| Evidence boundary | PASS — evidence schema version 2 binds effective image digests and permits only the documented metadata allowlist |

Representative commands used the protected default runtime root:

```text
make foundation-images-qualify
make foundation-supply-chain
make foundation-smoke
make foundation-recovery
make foundation-stop
make foundation-down
make preflight
```

## Condition impact

This evidence advances synthetic Development proof for C-03 and C-07, but does
not close either condition. C-05 is unchanged. Owner disposition remains
required through the condition register and parent issue; no open decision is
silently resolved.

## Non-claims

This is not evidence for a connected source, Staging entry, Production
readiness, HA, SLA, Kafka backup, scalability, security accreditation, or an
infrastructure write/control path. OD-06 remains open. Publication or
distribution of the Development-only derived images remains prohibited. A
clean-machine or empty-runtime milestone run remains required by the parent plan.
The 90% contract test injects the boundary value; it does not physically fill a
filesystem or Kafka volume.
