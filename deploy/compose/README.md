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

- official upstream images pinned as `exact-version@sha256:digest`, or the four
  ADR-0013 Development-only derived images selected through an external local
  immutable image-ID lock;
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

## Derived image qualification

`derived-images/recipes.json` records immutable public inputs, checksums,
allowlisted security patches, and non-publication policy. Run
`make foundation-images-qualify` before Compose startup. Qualification builds
each image twice, requires matching local image IDs and labels, produces SBOM,
license, and vulnerability evidence outside Git, then writes `images.env` and
`derived-images-lock.json` under `${DCIM_RUNTIME_ROOT}/dev-build`.

These images are local Development artifacts. They are never pushed. Clean
official upstream images remain preferred replacements.
