# ADR-0012: Internal Grafana Access for Development

- Status: Accepted
- Date: 2026-07-20
- Owner: shuffahaqgzz
- Decision source: owner approval during issue #9 implementation

## Context

Issue #9 originally required Grafana to publish `127.0.0.1:3000` while every
Compose network remained `internal: true`. Runtime verification on Docker Engine
29 showed that an internal bridge does not create the requested host port
mapping. Grafana remained healthy and reachable directly from the Development
host through its internal bridge address.

Making loopback publication work would require a non-internal network, host
networking, or a dual-homed proxy. Each option would widen reachability or add a
general-purpose bridge prohibited by the approved Phase 1 security boundary.

## Decision

Keep Grafana solely on the internal `observability` network and publish no host
port. The Development host resolves the current container bridge address at
runtime through the Make lifecycle interface. No fixed container address is
stored in Git or evidence.

This decision changes only local Development access. It does not authorize a
non-internal network, remote access, Staging exposure, or Production exposure.

## Consequences

- All Phase 1 services have zero published host ports.
- Grafana access remains available from the Linux Development host.
- The address may change after container recreation and must be resolved again.
- Docker Desktop and remote-daemon behavior are not claimed; those environments
  require separate verification.
- A future reverse proxy, identity provider, external bind, or Staging ingress
  requires a new governed design.

## Security and operational impact

No service gains another network, Linux capability, host namespace, device,
mount, or external route. Smoke tests resolve the address in memory and do not
persist it in evidence.

## Revalidation trigger

Revalidate when Docker internal-network publishing behavior changes, the target
host stops supporting direct bridge access, remote access is requested, or the
work advances to Staging.
