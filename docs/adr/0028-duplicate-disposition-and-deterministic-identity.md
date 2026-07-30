# ADR-0028: Duplicate Disposition and Deterministic Identity

- Status: Accepted
- Date: 2026-07-29
- Owner: shuffahaqgzz
- Decision type: Addendum to ADR-0006 and ADR-0020
- Related ADRs: ADR-0006 (canonical contract and identity), ADR-0020 (identity alias and conflict resolution)

## Context

ADR-0006 requires explicit validation dispositions and stable Asset/CI
identity, while ADR-0020 requires identity outcomes to be deterministic under
replay. The canonical event envelope currently distinguishes only accepted and
quarantined inputs. It cannot represent a valid replay that has already been
persisted, so a consumer could silently discard it or incorrectly mutate the
first event.

The Phase 2 batch pipeline also needs one canonical content representation for
deduplication, persistence, replay, and lineage, plus stable identifiers that
do not depend on arrival order or mutable aliases.

## Decision

### Contract compatibility and validation

Add `duplicate` to `enrichment.validation_status`. This is an additive,
backward-compatible enum extension. `schema_version` remains `"0.1.0"` because
all six existing fixtures already use that version and remain valid unchanged;
bumping it would force fixture churn without adding contract value.

Producers may emit the new value only after schema validation and duplicate
classification. Consumers, storage constraints, dashboard/read models, replay,
and DLQ/quarantine handling must recognize all three values before Phase 2 is
promoted. There is no default: the status remains required. Unknown status
values fail validation. The envelope continues to reject unknown fields through
its existing `additionalProperties: false` policy.

### Duplicate and conflict classification

- The deduplication key is the envelope `event_id`.
- The deduplication window is the lifetime of the persistent store.
- The first occurrence wins.
- Processing order is schema validation, then an atomic claim of `event_id`,
  then acceptance. Invalid input never claims an ID.
- Every accepted event stores the canonical envelope SHA-256.

The hash uses **project canonical JSON v1**, not RFC 8785:

```python
json.dumps(
    value,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
    allow_nan=False,
)
```

The serialized string is encoded as UTF-8 before SHA-256. The hash input
`value` is exactly the validated Pydantic model's
`model_dump(mode="json", round_trip=True)`, never the raw input dictionary.
That same project-canonical representation is persisted as `events.envelope`.

After a failed atomic claim:

- the same `event_id` with a matching stored hash is `duplicate`; it receives
  its own disposition row and lineage entry, and the accepted event is not
  mutated;
- the same `event_id` with a different hash is `quarantined` with reason
  `event_id_content_conflict`; lineage records both the stored and incoming
  hashes, and the accepted event is not mutated.

This makes replay and DLQ/quarantine behavior explicit and preserves the
zero-silent-loss ledger.

### Deterministic identity IDs

Asset and CI identifiers use UUIDv5 with:

```text
namespace = 7d4e2c10-5f3a-4b8c-9d6e-1a2b3c4d5e6f
name = <canonical identity string>
```

The canonical name is encoded as UTF-8 for UUIDv5. Canonical forms are:

```text
asset|native_uuid|<lowercased uuid>
asset|mfr_serial|<manufacturer>|<serial>
ci|<source_system>|<native_device_id>
```

Every component is first normalized with
`unicodedata.normalize("NFC", value).strip()`. Then:

- a native UUID is lowercased;
- `manufacturer` uses `.casefold()`;
- `serial` uses `.casefold().upper()`;
- `source_system` uses `.casefold()`;
- `native_device_id` is unchanged after NFC normalization and trimming.

Any component empty after normalization is invalid identity input and is
rejected; an ID is never derived from it. Hostname, FQDN, and IP remain
time-bounded aliases and are never used in these canonical names.

Golden vectors:

| Raw identity input | Canonical name | UUIDv5 |
|---|---|---|
| native UUID `550E8400-E29B-41D4-A716-446655440000` | `asset\|native_uuid\|550e8400-e29b-41d4-a716-446655440000` | `39542c91-ef59-53b8-a0c8-159b8c7eaa8a` |
| manufacturer `  Acme Systems  `, serial ` sn-0042 ` | `asset\|mfr_serial\|acme systems\|SN-0042` | `9b998410-a0e4-5e66-857f-1bad8b4afaba` |
| source system `  Monitoring Core `, native device ID `Device-007` | `ci\|monitoring core\|Device-007` | `f3a481af-08df-5be0-bf4e-35d287d3256d` |

## Consequences

- Producers and consumers gain one explicit disposition without changing any
  other envelope field or requirement.
- Storage needs an atomic unique claim on `event_id`, the accepted content
  hash, immutable accepted envelopes, and separate disposition/lineage rows.
- Dashboard/read models can count duplicates without treating them as accepted
  events or quarantine failures.
- Replay is deterministic for identical content and fails closed for an
  `event_id` content conflict.
- Identity resolution is stable across Unicode-equivalent and
  case-equivalent source values according to the pinned normalization rules.
- Contract tests cover the new value and rejection of an unknown value.
  Later persistence and identity work must cover hash matches/conflicts,
  collision scenarios, aliases, consumer contracts, and these golden vectors.

## Migration and rollback

The JSON Schema change is additive and needs no fixture or payload migration.
The Phase 2 persistence migration must add `duplicate` to its disposition
constraint before any producer can write it and must preserve existing
accepted/quarantined rows. There is no database migration in this ADR-only
change.

Rollback first stops new duplicate writes. Older consumers may be restored only
after they can safely retain and read existing duplicate disposition and
lineage rows. A full persistence-constraint downgrade is permitted only for an
empty Phase 2 store or after an operator-approved export and rebuild that
preserves the disposition ledger; accepted events are never rewritten or
deleted to make rollback succeed.

## Security impact

The decision introduces no connected source or infrastructure write path.
Hashes and identifiers are derived from validated data, but public fixtures and
evidence remain synthetic because hashes do not declassify source content.

## Revalidation triggers

- a change to project canonical JSON v1 or the Pydantic dump boundary;
- a change to the deduplication key, window, claim order, or conflict reason;
- a change to the UUID namespace, canonical forms, or normalization rules;
- a persisted disposition constraint or consumer that cannot represent
  `duplicate`.
