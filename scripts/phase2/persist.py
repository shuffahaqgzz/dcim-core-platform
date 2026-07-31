"""Transactional PostgreSQL persistence for the synthetic Phase 2 batch."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import assert_never
import uuid

from contracts.python.dcim_contracts.disposition import ClaimResult, JsonValue
from contracts.python.dcim_contracts.envelope import Envelope

from . import db
from .errors import Phase2Error
from .execution import ExecutionContext
from .identity_sql import (
    IdentityOmitted,
    IdentityRejected,
    JsonObject,
    json_literal,
    literal,
    PreparedIdentity,
    prepare_identity,
    render_identity_dml,
)


@dataclass(frozen=True, slots=True)
class QuarantineInput:
    """Rejected boundary data retained for a durable disposition."""

    candidate: Mapping[str, JsonValue]
    reason: str
    detail: str


class PersistenceError(Phase2Error):
    """A database result violated the Phase 2 persistence contract."""


@dataclass(frozen=True, slots=True)
class IdentityQuarantined(Phase2Error):
    """Signal that an identity-invalid disposition committed."""

    event_id: str

    def __str__(self) -> str:
        return f"event {self.event_id} has invalid identity"


class PostgresClaimStore:
    """Atomically claim and durably classify one validated canonical event."""

    def __init__(
        self,
        context: ExecutionContext,
        candidate: Mapping[str, JsonValue],
        input_ordinal: int,
    ) -> None:
        self._context = context
        self._input_ordinal = input_ordinal
        self._canonical = Envelope.model_validate(
            candidate, strict=True
        ).model_dump(mode="json", round_trip=True)

    def try_claim(self, event_id: str, content_sha256: str) -> ClaimResult:
        """Commit one event, disposition, and identity unit or classify replay."""
        preparation = prepare_identity(
            self._canonical, self._context.fixed_clock
        )
        match preparation:
            case PreparedIdentity() as prepared:
                identity_sql = render_identity_dml(prepared)
            case IdentityOmitted():
                identity_sql = ""
            case IdentityRejected():
                identity_sql = None
            case unreachable:
                assert_never(unreachable)
        identity_is_valid = identity_sql is not None
        envelope = json_literal(self._canonical if identity_is_valid else {})
        context = self._context
        sql = f"""
\\set QUIET 1
BEGIN;
SELECT pg_advisory_xact_lock(hashtextextended({literal(event_id)}, 0)) \\gset
WITH inserted AS (
    INSERT INTO phase2.events
        (event_id, run_id, envelope, content_sha256, ingested_at)
    SELECT
        {literal(event_id)}::uuid, {literal(context.run_id)}, {envelope},
        {literal(content_sha256)}, {literal(context.fixed_clock)}::timestamptz
    WHERE {literal(str(identity_is_valid).lower())}::boolean
    ON CONFLICT (event_id) DO NOTHING
    RETURNING event_id, content_sha256
),
decision AS (
    SELECT 'new' AS claim, content_sha256 AS stored_sha256 FROM inserted
    UNION ALL
    SELECT CASE WHEN content_sha256 = {literal(content_sha256)}
        THEN 'duplicate' ELSE 'conflict' END,
        content_sha256
    FROM phase2.events
    WHERE event_id = {literal(event_id)}::uuid
      AND NOT EXISTS (SELECT 1 FROM inserted)
    UNION ALL
    SELECT 'identity_invalid', {literal(content_sha256)}
    WHERE NOT {literal(str(identity_is_valid).lower())}::boolean
      AND NOT EXISTS (
          SELECT 1 FROM phase2.events
          WHERE event_id = {literal(event_id)}::uuid
      )
),
disposed AS (
    INSERT INTO phase2.dispositions
        (event_id, run_id, execution_sequence, input_ordinal,
         status, reason, lineage, decided_at)
    SELECT {literal(event_id)}::uuid, {literal(context.run_id)},
        {context.execution_sequence}, {self._input_ordinal},
        CASE claim
            WHEN 'new' THEN 'accepted'
            WHEN 'duplicate' THEN 'duplicate'
            ELSE 'quarantined'
        END,
        CASE claim
            WHEN 'conflict' THEN 'event_id_content_conflict'
            WHEN 'identity_invalid' THEN 'identity_conflict'
            ELSE NULL
        END,
        jsonb_build_object('incoming_sha256', {literal(content_sha256)},
            'stored_sha256', stored_sha256),
        {literal(context.fixed_clock)}::timestamptz
    FROM decision
    RETURNING disposition_id
)
SELECT json_build_object('claim', claim)::text AS result,
    claim = 'new' AS claim_is_new
FROM decision \\gset
\\echo :result
\\if :claim_is_new
{identity_sql or ""}
\\endif
COMMIT;
"""
        rows = db.parse_json_rows(db.psql(sql))
        if len(rows) != 1:
            raise PersistenceError("claim transaction returned unexpected rows")
        match rows[0].get("claim"):
            case "new" | "duplicate" | "conflict" as claim:
                return claim
            case "identity_invalid":
                raise IdentityQuarantined(event_id=event_id)
            case str() | int() | float() | bool() | None | list() | dict():
                raise PersistenceError("claim transaction returned invalid status")
            case unreachable:
                assert_never(unreachable)

def persist_quarantine(
    context: ExecutionContext,
    rejected: QuarantineInput,
    input_ordinal: int,
) -> None:
    """Commit exactly one pre-claim quarantine disposition."""
    raw_identifier = rejected.candidate.get("event_id")
    raw_text = raw_identifier if isinstance(raw_identifier, str) else None
    try:
        event_id = None if raw_text is None else str(uuid.UUID(raw_text))
    except ValueError:
        event_id = None
    lineage: JsonObject = {
        "raw_rejected_identifier": raw_text, "validation_detail": rejected.detail
    }
    event_sql = "NULL" if event_id is None else f"{literal(event_id)}::uuid"
    sql = f"""
\\set QUIET 1
BEGIN;
INSERT INTO phase2.dispositions
    (event_id, run_id, execution_sequence, input_ordinal,
     status, reason, lineage, decided_at)
VALUES (
    {event_sql}, {literal(context.run_id)}, {context.execution_sequence},
    {input_ordinal}, 'quarantined',
    {literal(rejected.reason)}, {json_literal(lineage)},
    {literal(context.fixed_clock)}::timestamptz
);
COMMIT;
"""
    output = db.psql(sql)
    if output:
        raise PersistenceError("quarantine transaction returned unexpected output")
