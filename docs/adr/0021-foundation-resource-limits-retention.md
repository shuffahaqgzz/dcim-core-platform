# ADR-0021: Foundation Resource Limits, Retention, and Disk Watermarks

- Status: Accepted
- Date: 2026-07-27
- Owner: shuffahaqgzz (caps engineer-recommended; retention and watermark
  values owner-set)
- Decision reference: condition C-07 closure path
- Related ADRs: ADR-0003 (single-broker KRaft), ADR-0018 (Elasticsearch heap)

## Context

C-07 requires Compose resource limits, retention, disk watermarks, and
headroom evidence for the Development VM (32 vCPU, 64 GB RAM, 500 GB SSD).
The owner set retention and watermark values directly and delegated
per-service caps to engineer recommendation.

## Owner-set values (accepted as given)

- **Kafka retention: 30 days** (log.retention.hours=720), with conservative
  segment and disk-watermark monitoring per ADR-0003.
- **Platform disk watermarks** on the runtime volume: **low 85%, high 90%,
  flood-stage 95%**. Alert at low; automatic retention enforcement and
  non-essential service pause at high; stop ingestion and page the operator
  at flood-stage.

## Decision (engineer-recommended caps)

Compose `deploy.resources.limits` per foundation service, sized to leave
~33 GB and ~18 vCPU headroom for OS, page cache, Phase 2+ application
services, and future components (workflow engines, search, CMDB):

| Service | Memory limit | CPU limit | Notes |
|---|---:|---:|---|
| PostgreSQL | 8 GB | 4 | shared_buffers ~2 GB; system of record |
| Kafka (KRaft, JVM) | 8 GB | 4 | heap 4 GB; 30-day retention monitored |
| Prometheus | 12 GB | 4 | 30-day local retention; largest consumer |
| Grafana OSS | 2 GB | 1 | dashboards only |
| postgres-exporter | 256 MB | 0.25 | lightweight |
| JMX exporter Java runtime | 512 MB | 0.5 | metrics sidecar |
| **Foundation subtotal** | **~30.75 GB** | **~13.75** | leaves ~33 GB / ~18 vCPU |

Additional rules:

1. Prometheus local retention **30 days**, aligned with Kafka.
2. Kafka log dirs on the runtime volume with the watermarks above; disk usage
   of Kafka, Prometheus, and PostgreSQL each emit metrics and alerts at the
   low watermark.
3. Non-foundation services (application, workflow, search, CMDB) must declare
   caps before activation and fit the remaining headroom; Elasticsearch heap
   per ADR-0018 counts against this headroom.
4. **Evidence obligation**: record actual usage (idle and smoke-load) in the
   foundation evidence summary; caps are revisited if measured p95 usage
   exceeds 70% of any limit.

## Options considered

### 1. No caps, rely on the kernel (rejected)

A single leaking service could starve the foundation; C-07 explicitly
requires limits and headroom evidence.

### 2. Tight caps per service (rejected)

Under-provisioning PostgreSQL/Prometheus causes OOM-driven instability that
looks like application failure; the headroom exists, use it predictably.

### 3. Recommended caps with measurement loop (selected)

Balances stability and headroom; measurement obligation keeps caps honest.

## Security impact

Limits bound denial-of-service blast radius from a misbehaving container.

## License impact

None.

## Resource and operational impact

This ADR is the resource contract for the foundation plane. Operators get
watermark alerts via the existing Prometheus/Grafana stack.

## Migration and rollback

Cap changes are Compose config edits followed by a foundation smoke and
recovery rerun; rollback restores the previous values.

## Acceptance evidence

- owner marks this ADR Accepted;
- Compose profiles carry the caps; smoke + recovery pass with caps active;
- idle/load usage recorded in the evidence summary;
- conditions register C-07 evidence links the run.

## Revalidation triggers

- measured p95 usage exceeds 70% of a limit;
- a new service class activates (search, workflow, CMDB);
- VM size or retention policy changes.
