# ADR-0009: Hermes Read-Only Shadow After Gate

- Status: Accepted
- Date: 2026-07-17
- Owner: shuffahaqgzz

## Context

Hermes Runtime tersedia, tetapi prompt/tool/memory/egress dapat membocorkan Restricted evidence atau menciptakan execution path.

## Decision

Hermes tetap disabled pada Phase 0. Future enablement hanya read-only, non-blocking, advisory shadow setelah pipeline gate, dengan approved allowlist, private-safe context policy, no credential/source endpoint/database/tool access, audit, resource/egress/memory limits, evaluation, dan kill switch. Workflow/SOAR tetap execution boundary.

## Alternatives

Production-connected Hermes, autonomous action, dan ingestion raw operational evidence ditolak.

## Consequences

AI value ditunda sampai C-08 dan pipeline evidence selesai. Recommendation tidak boleh mengubah state atau menjadi blocking dependency.

## Security Impact

Mencegah credential/data exfiltration dan prompt-to-action path; future model/tool supply chain tetap perlu threat model.

## Operational Impact

Future owner wajib mengelola egress, memory deletion, audit, resource ceiling, eval, disable procedure, dan incident response.

## Revalidation Trigger

Hermes/model/tool/context/egress/memory integration proposal atau pipeline gate change.
