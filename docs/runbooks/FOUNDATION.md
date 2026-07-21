# Synthetic Development Foundation

Scope: `dcim-build` only. No office or Production source, connector, Hermes,
workflow execution, or infrastructure control path exists in this foundation.

## Lifecycle

The default protected root is
`${XDG_STATE_HOME:-$HOME/.local/state}/dcim-core-platform/runtime`, independent
of the checkout or worktree location. Set `DCIM_RUNTIME_ROOT` only to select a
different protected root explicitly, then run:

```text
make foundation-bootstrap
make foundation-images-qualify
make foundation-up
make foundation-grafana-url
make foundation-smoke
make foundation-recovery
make foundation-stop
make foundation-down
```

Issue #9 clean-runtime acceptance uses a separate target and a brand-new
protected root under an owner/root-controlled path with no group- or
world-writable existing component. Ordinary `make preflight` can reuse the
selected protected state and must not be represented as clean-machine proof:

```text
make foundation-clean-acceptance DCIM_RUNTIME_ROOT=<new-protected-root>
```

The acceptance target uses an isolated `dcim-build-acceptance-*` Compose
namespace, refuses any existing normal `dcim-build` container, network, volume,
or project/named image, refuses any pre-existing labeled or acceptance-named
container, network, volume, or image in the acceptance namespace, writes a
validated acceptance-only Compose resource override under the protected runtime
root, and stops services without removing state or raw evidence. A clean root
can require outbound access to immutable public inputs, scanner databases, and
artifacts unless those inputs are already cached locally.

Image qualification uses only public pinned inputs. It builds ADR-0013 derived
images twice, checks reproducibility, scans vulnerability and license data,
generates SBOMs, and writes local immutable image references beneath
`${DCIM_RUNTIME_ROOT}/dev-build`. Raw reports and local image IDs remain outside
Git. `foundation-up`, policy, supply-chain, and preflight also enforce this lock.

`foundation-bootstrap` refuses overwrite. `stop` and `down` preserve named
volumes. `foundation-reset` is interactive, unavailable in CI, and removes only
allowlisted volumes labelled for project `dcim-build`.

Bootstrap stores the resolved external runtime root in protected `runtime.env`.
Keep using that same root with the persistent `dcim-build` volumes; selecting a
fresh bootstrap root does not authorize resetting or re-identifying existing
state. Legacy issue #10 material may not contain that non-secret root entry;
the Make lifecycle supplies `DCIM_RUNTIME_ROOT` explicitly and remains
compatible without overwriting bootstrap material. The workspace bootstrap and
Make lifecycle share the same XDG default.
With that file and `images.env`, plain Compose without a profile resolves
successfully and selects zero services. Every executable service still requires
the explicit `data`, `observability`, or `smoke` Capability Profile.

Runtime writers reject symbolic-link path components. Image locks bind the exact
qualification recipe and license disposition. Normalized policy also enforces
the exact Runtime Plane/project name, network membership, stateful volume owner,
health command, exporter process, Kafka KRaft/retention/message settings, and
Prometheus retention command.

Grafana has no published host port. Per ADR-0012, the Linux Development host
resolves its current internal bridge address with `foundation-grafana-url`.

Raw JSON evidence, secrets, artifacts, and dumps stay under the protected
external runtime root. Fast evidence cannot claim PASS after five minutes;
recovery evidence cannot claim PASS after fifteen minutes. Each evidence record
uses schema version 2 and contains only its schema version, commit, effective
image digests, Capability Profiles, UTC timestamp, duration, assertion result,
synthetic run ID, and mode. Schema version 1 evidence remains historical and is
not migrated; it lacks required image binding. Git receives no raw runtime
output.

Fast smoke requires rejection of a message above the 1 MiB Kafka ceiling and
reports broker-managed internal topics separately from the single allowlisted
non-internal topic. Recovery records the exact Kafka offset and synthetic
PostgreSQL row before restart, then performs read-only post-restart checks before
dump/restore. Lost state cannot be recreated and mistaken for persistence.

## Non-claims

Passing foundation checks does not prove P1/P2 flows, HA, Kafka backup,
scalability, SLA, Staging readiness, Production readiness, or Production
hardening. C-03, C-05, and C-07 remain unchanged until owner disposition.
