# ADR-0010: Solo Development to Multi-Team Handover

- Status: Accepted
- Date: 2026-07-17
- Owner: shuffahaqgzz

## Context

Development owner tunggal mempercepat prototype tetapi menciptakan bus-factor dan approval separation risk. Staging/Production akan dimiliki banyak tim.

## Decision

Gunakan model Solo Development, evidence-backed `DEV-APPROVED`, controlled handover, named multi-team Staging, lalu separately governed Production. Development approval tidak memberi Staging entry atau Production authorization.

## Alternatives

Solo owner sampai Production dan automatic environment promotion ditolak. Full multi-team process pada Phase 0 tidak tersedia.

## Consequences

Evidence, runbook, reproducible artifact, schema/migration/recovery, security review, limitations, dan explicit ownership wajib menjadi handover contract.

## Security Impact

Future separation of duties dan environment approval mengurangi unilateral privilege; Phase 0 tetap memiliki residual bus-factor-one risk.

## Operational Impact

Staging membutuhkan Product/Architecture, Platform/SRE, Data/Integration, Security, QA/UAT, dan domain owners bernama.

## Revalidation Trigger

Staging entry, staffing/ownership change, Production planning, atau handover failure.
