# ADR-0020: Identity Alias and Conflict Resolution Rules

- Status: Accepted
- Date: 2026-07-27
- Owner: shuffahaqgzz
- Decision reference: condition C-06 closure path (owner direction 2026-07-27)
- Related ADRs: ADR-0006 (canonical contract and identity)

## Context

C-06 requires identity aliases, validity, confidence, and collision tests.
ADR-0006 fixes identity classes (Asset: native UUID, fallback
manufacturer+serial; CI: source system + native device ID; hostname/FQDN/IP
are aliases; IP is never a primary key) but leaves conflict-resolution rules
to be finalized. The owner directed a final ADR for these rules, followed by
deterministic collision tests.

## Decision drivers

- Deterministic, replayable resolution: the same inputs always produce the
  same identity outcome.
- Zero silent merges and zero silent drops (baseline §8).
- Source confidence is explicit, never implied by order of arrival.
- Aliases are time-bounded; stale aliases must not steer resolution.

## Decision

### Identity precedence

1. **Asset**: native UUID; fallback manufacturer + serial number pair.
2. **CI**: source system + native device ID/UUID.
3. Strong identifiers always outrank aliases. An alias match never overrides
   a strong-identifier mismatch.

### Alias rules

- Aliases (hostname, FQDN, IP) carry `valid_from`, `valid_to`, and
  `source_confidence` (0–100, recorded per source in its authorization/
  connector config; default 50).
- An expired alias (`valid_to` in the past) is ineligible for resolution but
  retained for history and lineage.
- IP aliases additionally require a non-expired validity window; reuse of an
  IP across devices is expected and must not merge identities.

### Conflict resolution (deterministic)

When alias evidence points at two different strong identities, or two sources
claim the same strong identity with conflicting attributes:

1. **Highest source_confidence wins.**
2. Tie → the alias with the latest `valid_from` wins.
3. Still tied, or any strong-identifier conflict → the event is **quarantined**
   with reason `identity_conflict` and a structured detail record; no merge,
   no drop. An operator resolves the conflict; the resolution is recorded for
   replay determinism.

### Merge and split

- Merges require two matching strong identifiers or an approved operator
  decision; merges append lineage to both identities.
- Splits are operator-only and recorded with full lineage.

### Test obligations (C-06 closure evidence)

Deterministic fixture tests must cover: duplicate serial across sources,
hostname reuse after validity expiry, IP moving between devices,
confidence-tie quarantine, and merge lineage. All outcomes replay-stable.

## Options considered

### 1. Last-writer-wins (rejected)

Simple but non-deterministic under replay and can silently corrupt identity.

### 2. Deterministic confidence + validity rules with quarantine (selected)

Matches the baseline zero-silent-drop rule and keeps resolution replay-safe.

## Security impact

Prevents identity spoofing by low-confidence sources: a low-confidence source
cannot redirect enrichment by claiming an alias of a high-confidence asset.

## License impact

None.

## Resource and operational impact

Resolution is a deterministic lookup over indexed strong identifiers plus an
alias table with validity predicates; negligible cost at Development scale.

## Migration and rollback

Rules live in versioned schema/code. A rule change is a new ADR or an
amendment with replay evidence showing intended outcome changes only.

## Acceptance evidence

- owner marks this ADR Accepted;
- the C-06 fixture test list above passes deterministically;
- conditions register C-06 evidence links the test run.

## Revalidation triggers

- a new source class introduces identifiers outside the current classes;
- an operator workflow change alters merge/split authority.
