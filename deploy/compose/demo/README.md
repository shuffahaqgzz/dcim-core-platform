# `dcim-demo` Runtime Plane contract

Phase 1 P1-C4 adds `compose.yaml` skeleton for synthetic-only demo flow:
Redfish fixture (`fixtures/synthetic/events/p1-redfish-health.json`) -> Kafka ->
normalized -> enriched -> dashboard placeholder.

## Run on Docker host

Docker Engine and Docker Compose plugin required. Sandbox cannot run this demo;
Docker is unavailable here.

After foundation image qualification and runtime bootstrap, activate profiles:

```bash
docker compose \
  --env-file "$DCIM_RUNTIME_ROOT/demo/runtime.env" \
  --env-file "$DCIM_RUNTIME_ROOT/demo/images.env" \
  -f deploy/compose/demo/compose.yaml \
  --profile data --profile p1-demo up
```

`data` starts PostgreSQL and Kafka. `p1-demo` names placeholder stages only;
placeholder stages use the pinned Prometheus image until real synthetic stage
images are introduced.
No application implementation, live endpoint, credential, or production route is
included. C-05 remains open until Docker acceptance proves the intended flow.
