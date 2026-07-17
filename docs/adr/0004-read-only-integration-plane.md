# ADR-0004: Pinned Read-Only Integration Plane

- Status: Accepted
- Date: 2026-07-16
- Owner: shuffahaqgzz

## Context

Sebagian Development validation mungkin kelak memerlukan office/Production telemetry. Mutable Development code atau broad credential menciptakan source/data risk yang tidak dapat diterima.

## Decision

Setiap connected integration merupakan DEV-INTEGRATION-RO plane yang dipromosikan terpisah dengan pinned artifact, dedicated read-only identity, restricted route/egress, private runtime storage, polling ceiling, source-impact metric, audit metadata, dan immediate kill switch. CI dan agent session tidak terhubung ke live source.

Setiap connector hanya mengekspos allowlisted read method dan memiliki negative tests yang membuktikan prohibited operation tidak tersedia.

## Consequences

- Source authorization dan environment separation merupakan prerequisite, bukan later hardening.
- Integration feedback lebih lambat karena promotion eksplisit.
- Private operational runbook/evidence diperlukan di luar repository.
- Write-capable path merupakan governed exception terpisah dan bukan bagian milestone ini.

## Alternatives

Mutable code pada connected plane, shared credential/network, dan live-source CI ditolak. Simulator/synthetic tetap default sebelum authorization gate.

## Security Impact

Least privilege, exact read allowlist, egress restriction, negative write tests, audit, dan kill switch merupakan entry prerequisites, bukan hardening tambahan.

## Operational Impact

Setiap source memerlukan owner, polling/rate ceiling, maintenance window, expiry, short retention, incident contact, dan disable drill.

## Revalidation Trigger

Source/protocol/firmware/RBAC/network change, authorization expiry, privilege drift, atau source-impact incident.
