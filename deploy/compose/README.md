# Development Compose Foundation

Phase 1 design is owner-approved. Development implementation and qualification
live in `dev-build/`; milestone completion still depends on issue review and
merge. The complete design and acceptance contract are in
[`docs/plan/PHASE1-COMPACT-INFRASTRUCTURE-FOUNDATION.md`](../../docs/plan/PHASE1-COMPACT-INFRASTRUCTURE-FOUNDATION.md).

## Runtime Plane layout

- `dev-build/`: executable `dcim-build` Compose project, synthetic only;
- `integration-ro/`: contract and README only during Phase 1; no runnable
  manifest, credential, connector, or route;
- `demo/`: contract and README only during Phase 1; no runnable manifest.

Runtime Planes require separate project names, networks, volumes, runtime
configuration, credentials, and promotion lifecycles. Compose profiles are
Capability Profiles within a plane and are not security boundaries.
The Make lifecycle and workspace bootstrap resolve the same checkout-independent
default root at `${XDG_STATE_HOME:-$HOME/.local/state}/dcim-core-platform/runtime`.
An explicit `DCIM_RUNTIME_ROOT` override must remain paired with the state it
bootstrapped; a new root is not a reason to reset persistent volumes.
Issue #9 clean-runtime acceptance is the exception: use
`make foundation-clean-acceptance DCIM_RUNTIME_ROOT=<new-protected-root>`, which
requires a brand-new protected root under an owner/root-controlled path and an
isolated `dcim-build-acceptance-*` Compose namespace. Normal Make lifecycle
targets pin `COMPOSE_PROJECT_NAME=dcim-build`, and the checked-in Compose file
uses fixed `dcim-build-*` network and volume names. Clean acceptance writes a
validated acceptance-only override under the protected external runtime root.

## Phase 1 Capability Profiles

- `data`: PostgreSQL and single-broker Kafka KRaft;
- `observability`: Prometheus, Grafana, and metrics exporters;
- `smoke`: one-shot synthetic smoke clients where required.

Every service must have an explicit profile. Plain `docker compose up` must start
nothing. Redis, API/application services, connectors, workflow, Hermes, and all
write/control paths are excluded.

Future profile names remain reserved: `core`, `dashboard`, `workflow`,
`connectors-synthetic`, `connectors-integration-ro`, and `hermes`.

## Non-negotiable implementation constraints

- official upstream images pinned as `exact-version@sha256:digest`, or the five
  ADR-0013/ADR-0015 Development-only derived images selected through an external
  local immutable image-ID lock;
- external runtime secrets and state; no runtime material in Git;
- isolated internal networks and service-specific named volumes;
- only the two metrics exporters may be long-running dual-homed services, with
  IP forwarding disabled;
- zero published host ports; Grafana access follows accepted ADR-0012 internal
  bridge resolution;
- explicit health checks, resource limits, retention, and log rotation;
- no host network/PID/IPC, privileged mode, device, Docker socket, broad host
  mount, or live source route;
- normalized Compose policy checks plus synthetic fast/recovery smoke tests;
- no HA, SLA, Staging, Production, or vertical-slice claim.

Plain Compose with the protected runtime and image environment files but no
profile selects zero services. Policy binds the exact `dcim-build` project, or
the isolated `dcim-build-acceptance-*` project used only by clean acceptance, to
network membership, service-owned stateful volumes, functional health checks,
reviewed exporter commands, Kafka runtime settings, and Prometheus retention.

## Derived image qualification

`derived-images/recipes.json` records immutable public inputs, checksums,
allowlisted security patches, and non-publication policy. Run
`make foundation-images-qualify` before Compose startup. Qualification builds
each image twice, requires matching local image IDs and labels, produces SBOM,
license, and vulnerability evidence outside Git, then writes `images.env` and
`derived-images-lock.json` under `${DCIM_RUNTIME_ROOT}/dev-build`.

`derived-images/license-dispositions.json` records issue #10 owner review for
the exact review-required inventories in the qualified six-image set. Each
`restricted`, `reciprocal`, and `unknown` record binds both count and a canonical
identity fingerprint; a changed inventory cannot pass by preserving aggregate
counts. Recipe, publication/distribution, OD-06, or deployment-scope changes
require fresh owner review. Qualification upgrades a valid external lock from
schema v1 to v2 only after revalidating existing reports; rollback to v1 restores
the Governance HOLD and cannot pass current policy or supply-chain gates.

These images are local Development artifacts. They are never pushed. Clean
official upstream images remain preferred replacements.

Fast and recovery evidence remains external, binds the effective image digests,
and uses five- and fifteen-minute fail-closed deadlines respectively. Fast smoke
proves the Kafka oversize-message rejection. Recovery verifies pre-restart
PostgreSQL and Kafka state without rewriting it after restart.
