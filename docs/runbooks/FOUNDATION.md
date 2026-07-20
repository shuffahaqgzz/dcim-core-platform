# Synthetic Development Foundation

Scope: `dcim-build` only. No office or Production source, connector, Hermes,
workflow execution, or infrastructure control path exists in this foundation.

## Lifecycle

Set `DCIM_RUNTIME_ROOT` to a protected path outside this repository, then run:

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

Image qualification uses only public pinned inputs. It builds ADR-0013 derived
images twice, checks reproducibility, scans vulnerability and license data,
generates SBOMs, and writes local immutable image references beneath
`${DCIM_RUNTIME_ROOT}/dev-build`. Raw reports and local image IDs remain outside
Git. `foundation-up`, policy, supply-chain, and preflight also enforce this lock.

`foundation-bootstrap` refuses overwrite. `stop` and `down` preserve named
volumes. `foundation-reset` is interactive, unavailable in CI, and removes only
allowlisted volumes labelled for project `dcim-build`.

Grafana has no published host port. Per ADR-0012, the Linux Development host
resolves its current internal bridge address with `foundation-grafana-url`.

Raw JSON evidence, secrets, artifacts, and dumps stay under the protected
external runtime root. Git receives no raw runtime output.

## Non-claims

Passing foundation checks does not prove P1/P2 flows, HA, Kafka backup,
scalability, SLA, Staging readiness, Production readiness, or Production
hardening. C-03, C-05, and C-07 remain unchanged until owner disposition.
