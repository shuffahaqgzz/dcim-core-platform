# Evidence todo 19

Todo 19 was verified on the synthetic Docker host. The evidence is limited to
the local Development runtime and makes no Staging, Production, HA, or SLA
claim.

## Happy path

Commands were run exactly as follows:

```text
rtk .venv/bin/python -m unittest discover -s tests/phase3 -p 'test_*.py' -v
```

Exit code: `0`. Result: 61 Phase 3 tests passed, including stage ordering,
evidence shape, cleanup ordering, gateway dashboard assertions, and Compose
profile/safety contracts.

```text
rtk make phase2-check
```

Exit code: `0`. Result: the 11-stage Phase 2 gate passed, including topic
verification, stream round-trip, zero-loss/idempotency checks, and Kafka
latency assertion. The gate derives the current Kafka container address after
startup; it does not publish a host port.

```text
rtk make service-check
```

Exit code: `0`. Result: Phase 3 tests, service smoke, and E2E all passed. The
service smoke evidence at
`$DCIM_RUNTIME_ROOT/dev-build/evidence/service-smoke/evidence.json` records all
5 services with health `200`, readiness `200`, non-empty metrics, and 403 for
the unauthenticated `/api/*` probe on every service: `5/5` auth-denial proofs.
The token value was read only from the protected runtime and was not logged or
written to this evidence.

The E2E evidence at
`$DCIM_RUNTIME_ROOT/dev-build/evidence/e2e/evidence-e2e.json` records the
required stage order:

```text
topic-verify -> produce -> drain -> zero-loss -> dashboard -> latency
```

Sanitized assertions from the evidence:

- producer ledger: received `6`, published `6`, DLQ `0`;
- consumer ledger: received `6`, accepted `6`, quarantined `0`, duplicate `0`;
- durable counts: events `6`, dispositions `6`, accepted `6`, quarantined `0`, duplicate `0`;
- `zero_silent_loss=true` and `producer_consumer_counts_match=true`;
- dashboard visibility: P1 visible `2`, expected `2`, summary P1 `2`; assertions used the gateway;
- Kafka latency: count `50`, seed `42`, p95 `1581.272993 ms`, below `5000 ms`;
- `latency_cleanup=true`.

```text
rtk make foundation-policy
```

Exit code: `0`. Result: `foundation-policy: PASS`, including the aggregate
20-CPU/40-GiB resource policy.

```text
rtk make phase0-check
```

Exit code: `0`. Result: compile, public-safety, JSON, fixture, Markdown-link,
and 272 standard-library unittest checks passed.

## Failure mutation and restore

The Kafka failure mutation was run against the same synthetic Compose stack.
The stack start command exited successfully before mutation:

```text
rtk env -u DCIM_COMPOSE_OVERRIDE COMPOSE_PROJECT_NAME='dcim-build' docker compose --env-file "$DCIM_RUNTIME_ROOT/dev-build/runtime.env" --env-file "$DCIM_RUNTIME_ROOT/dev-build/images.env" -f 'deploy/compose/dev-build/compose.yaml' --profile data --profile observability --profile core --profile dashboard --profile workflow up -d --wait --wait-timeout 240
```

Exit code: `0`.

```text
rtk env -u DCIM_COMPOSE_OVERRIDE COMPOSE_PROJECT_NAME='dcim-build' docker compose --env-file "$DCIM_RUNTIME_ROOT/dev-build/runtime.env" --env-file "$DCIM_RUNTIME_ROOT/dev-build/images.env" -f 'deploy/compose/dev-build/compose.yaml' --profile data --profile observability --profile core --profile dashboard --profile workflow stop --timeout 60 kafka
```

Exit code: `0`. Mutation result: Kafka was stopped and no other service was
removed.

```text
rtk env DCIM_KAFKA_BOOTSTRAP="$(docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' dcim-build-kafka-1):9092" .venv/bin/python scripts/phase3/e2e.py --output "$DCIM_RUNTIME_ROOT/dev-build/evidence/e2e/evidence-e2e-kafka-stopped.json"
```

Exit code: `1`. Expected failure was observed without secret output:
`e2e: stage 1 topic-verify: FAIL: Kafka topic verification failed`.

Restore commands:

```text
rtk env -u DCIM_COMPOSE_OVERRIDE COMPOSE_PROJECT_NAME='dcim-build' docker compose --env-file "$DCIM_RUNTIME_ROOT/dev-build/runtime.env" --env-file "$DCIM_RUNTIME_ROOT/dev-build/images.env" -f 'deploy/compose/dev-build/compose.yaml' --profile data --profile observability --profile core --profile dashboard --profile workflow start kafka
```

Exit code: `0`.

```text
rtk env -u DCIM_COMPOSE_OVERRIDE COMPOSE_PROJECT_NAME='dcim-build' docker compose --env-file "$DCIM_RUNTIME_ROOT/dev-build/runtime.env" --env-file "$DCIM_RUNTIME_ROOT/dev-build/images.env" -f 'deploy/compose/dev-build/compose.yaml' --profile data --profile observability --profile core --profile dashboard --profile workflow up -d --wait --wait-timeout 240
```

Exit code: `0`.

```text
rtk env DCIM_KAFKA_BOOTSTRAP="$(docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' dcim-build-kafka-1):9092" .venv/bin/python scripts/phase3/e2e.py --output "$DCIM_RUNTIME_ROOT/dev-build/evidence/e2e/evidence-e2e-restored.json"
```

Exit code: `0`. Restored result: E2E passed with zero silent loss, dashboard
visibility true, and p95 `1571.214231 ms` below `5000 ms`.

Final cleanup was run:

```text
rtk env -u DCIM_COMPOSE_OVERRIDE COMPOSE_PROJECT_NAME='dcim-build' docker compose --env-file "$DCIM_RUNTIME_ROOT/dev-build/runtime.env" --env-file "$DCIM_RUNTIME_ROOT/dev-build/images.env" -f 'deploy/compose/dev-build/compose.yaml' --profile data --profile observability --profile core --profile dashboard --profile workflow stop --timeout 60
```

Exit code: `0`. The E2E runner removes its run-scoped rows in foreign-key
order, and the latency harness removes its four run-scoped rows in `finally`;
the recorded `latency_cleanup` assertion is true. No governance status file
was changed.

## Current fix binding

This evidence applies to the current Makefile contract: Kafka bootstrap is
inspected at command execution time in both `phase2-check` and `e2e`, so each
invocation uses the running Kafka container address. `service-check`
prerequisites are serialized by a runtime lock before they run.

Protected raw receipt names remain under
`$DCIM_RUNTIME_ROOT/evidence-transcripts` and are not committed.

Static verification of this binding:

```text
rtk git diff --check
```

Exit code: `0`.

```text
rtk .venv/bin/python -m unittest discover -s tests/phase2 -p 'test_stage12_gate_contracts.py' -v
```

Exit code: `0` (6 tests passed).

```text
rtk .venv/bin/python -m unittest discover -s tests/phase3 -p 'test_e2e.py' -v
```

Exit code: `0` (7 tests passed).
