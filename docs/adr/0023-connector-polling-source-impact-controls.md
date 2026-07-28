# ADR-0023: Connector Polling and Source-Impact Controls

- Status: Accepted
- Date: 2026-07-27
- Owner: shuffahaqgzz
- Decision reference: condition C-09 closure path (owner direction 2026-07-27:
  engineer-researched defaults via ADR)
- Related ADRs: ADR-0004 (read-only integration plane)
- Related conditions: C-01, C-04

## Context

C-09 requires per-source polling/source-impact controls: ceilings, timeouts,
retries, metrics, and a stop test proving collectors cannot harm sources and
can be stopped quickly. Defaults below derive from vendor documentation and
SRE practice (DMTF Redfish, Dell iDRAC session limits, SNMP RFCs 1157/3416,
Prometheus scrape defaults, Google SRE golden signals, Fowler/AWS circuit
breaker patterns). Design principles: conservative over fresh; explicit
rejection (HTTP 429, SNMP resourceUnavailable) opens the breaker immediately;
BMC session headroom reserved for human operators.

## Decision

### Per-class defaults

| Source class | Min interval | Connect timeout | Read timeout | Max retries | Max concurrent | Max req/min | Breaker threshold | Breaker cooldown |
|---|---|---|---|---|---|---|---|
| Redfish BMC — health | 30 s | 5 s | 10 s | 3 | 2 | 10 | 5 consecutive or 50%/60 s | 60 s |
| Redfish BMC — standard/inventory | 60–300 s | 5 s | 10 s | 3 | 2 | 10 | 5 consecutive or 50%/60 s | 60 s |
| SNMP — critical counters | 30 s | — (UDP) | 5 s | 2 | 1 | 10 | 5 consecutive or 50%/60 s | 60 s |
| SNMP — default/environmental | 60–300 s | — (UDP) | 5 s | 2 | 1 | 10 | 5 consecutive or 50%/60 s | 60 s |
| SNMP traps | event-driven | — | — | 1 (INFORM only) | — | — | — | — |
| REST API health | 15–120 s (60 default) | 3 s | 10 s | 3 | 4 | 30 | 5 consecutive or 50%/60 s | 60 s |
| NVR/camera — RTSP probe | 30 s | 5 s | 10 s | 2 | 1 | 5 | 3 consecutive or 50%/60 s | 120 s |
| NVR/camera — ONVIF | 60 s | 5 s | 10 s | 2 | 1 | 3 | 3 consecutive or 50%/60 s | 120 s |
| NVR/camera — ping | 15 s | — | 2 s | 2 | 1 | 10 | 5 consecutive or 50%/60 s | 60 s |

Retry backoff: decorrelated jitter, `delay = min(30 s cap, random(1 s, last × 3))`.

### Traps vs polling split

Traps/INFORMs carry event-driven state transitions; polling carries trend and
confirmation. Neither replaces the other; a lost trap never suppresses a
polling-derived state.

### Source-impact metrics (per connector, per source)

`connector_poll_duration_seconds` (histogram), `connector_poll_total`
(counter, labeled status), `connector_poll_failures_total` (counter, labeled
error type), `connector_source_response_latency_seconds` (histogram),
`connector_concurrent_requests` (gauge), `connector_requests_per_minute`
(gauge), `connector_circuit_state` (gauge), `connector_last_success_timestamp`
(gauge), `connector_backoff_seconds` (gauge).

### Kill switch (three tiers) and stop test

1. Config flag (`enabled: false`), hot-reloadable — stops within one cycle.
2. Stop file checked before each poll — works when reload is unavailable.
3. Orchestration stop (SIGTERM) — graceful drain, max 10 s in-flight
   completion.

The stop test must prove: zero requests to the source within one poll
interval after signal; in-flight drain ≤ 10 s; zero requests over 2× the max
interval (verified via connector metrics and source-side observation in the
integration plane); clean resume without burst after re-enable.

### Authorization binding

Every connector instance records its per-source ceilings in its C-01
authorization register entry; exceeding a registered ceiling is a policy
violation, not a tuning choice.

## Options considered

### 1. Aggressive freshness (5–15 s polls) (rejected)

Vendor guidance warns of BMC session saturation (iDRAC caps 8 concurrent
sessions) and SNMP control-plane CPU spikes; freshness targets in the
baseline (30 s polling feeds) are met without this risk.

### 2. Conservative defaults with breakers and kill switch (selected)

Selected; meets baseline latency targets (P1 poll feed p95 < 30 s) with wide
margin while protecting sources.

## Security impact

Breakers and ceilings bound the blast radius of a misconfigured or
compromised collector; the stop test proves C-09's "stopped quickly"
requirement. Combined with ADR-0004, write/control methods remain
unavailable regardless of polling behavior.

## License impact

None.

## Resource and operational impact

Serialized SNMP and capped concurrency keep connector CPU/memory negligible;
metrics flow into the existing Prometheus stack.

## Migration and rollback

Defaults live in versioned connector policy config; per-source overrides
require a registered authorization entry. Rollback restores previous config.

## Acceptance evidence

- owner marks this ADR Accepted;
- connector policy schema enforces ceilings; negative tests prove a connector
  cannot exceed its registered ceilings;
- stop test passes against a synthetic source;
- conditions register C-09 evidence links the runs.

## Revalidation triggers

- a new source class or vendor guidance changes;
- baseline latency targets tighten;
- a source reports impact despite the ceilings.
