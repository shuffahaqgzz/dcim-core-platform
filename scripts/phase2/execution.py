"""Allocate and reconcile replay-safe Phase 2 executions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from . import db
from .errors import ManifestDriftError, Phase2Error
from .identity_sql import JsonObject, literal
from .manifest import RunManifest


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Immutable values shared by every transaction in one execution."""

    run_id: str
    fixed_clock: str
    execution_sequence: int


class ReconciledCounts(TypedDict):
    received: int
    accepted: int
    quarantined: int
    duplicate: int


@dataclass(frozen=True, slots=True)
class ReconciliationError(Phase2Error):
    """Durable dispositions do not balance one manifest execution."""

    run_id: str
    execution_sequence: int

    def __str__(self) -> str:
        return (
            f"execution {self.run_id}/{self.execution_sequence} "
            "does not match its manifest"
        )


def begin_execution(manifest: RunManifest) -> ExecutionContext:
    """Verify immutable manifest data, then atomically allocate an execution."""
    sql = f"""
\\set QUIET 1
BEGIN;
INSERT INTO phase2.run_manifests
    (run_id, fixed_clock, source_count, manifest_sha256, created_at)
VALUES (
    {literal(manifest.run_id)}, {literal(manifest.fixed_clock)}::timestamptz,
    {manifest.source_count}, {literal(manifest.manifest_sha256)},
    {literal(manifest.fixed_clock)}::timestamptz
)
ON CONFLICT (run_id) DO NOTHING;
SELECT (
    source_count = {manifest.source_count}
    AND manifest_sha256 = {literal(manifest.manifest_sha256)}
) AS manifest_matches
FROM phase2.run_manifests
WHERE run_id = {literal(manifest.run_id)}
FOR UPDATE \\gset
\\if :manifest_matches
    UPDATE phase2.run_manifests
    SET last_execution_sequence = last_execution_sequence + 1
    WHERE run_id = {literal(manifest.run_id)}
    RETURNING json_build_object(
        'run_id', run_id,
        'execution_sequence', last_execution_sequence
    )::text;
    COMMIT;
\\else
    ROLLBACK;
    SELECT json_build_object('drift', true)::text;
\\endif
"""
    rows = db.parse_json_rows(db.psql(sql))
    if rows == [{"drift": True}]:
        raise ManifestDriftError("stored manifest differs from immutable run manifest")
    if len(rows) != 1:
        raise ManifestDriftError("manifest transaction returned unexpected rows")
    sequence = rows[0].get("execution_sequence")
    if rows[0].get("run_id") != manifest.run_id or type(sequence) is not int:
        raise ManifestDriftError("manifest transaction returned invalid execution")
    return ExecutionContext(
        run_id=manifest.run_id,
        fixed_clock=manifest.fixed_clock,
        execution_sequence=sequence,
    )


def reconcile_execution(context: ExecutionContext) -> ReconciledCounts:
    """Verify the exact durable disposition set for one execution."""
    rows = db.query_json(
        f"""
WITH execution AS (
    SELECT status, input_ordinal
    FROM phase2.dispositions
    WHERE run_id = {literal(context.run_id)}
      AND execution_sequence = {context.execution_sequence}
)
SELECT json_build_object(
    'source_count', manifest.source_count,
    'disposition_count', (SELECT count(*) FROM execution),
    'accepted', (SELECT count(*) FROM execution WHERE status = 'accepted'),
    'quarantined', (SELECT count(*) FROM execution WHERE status = 'quarantined'),
    'duplicate', (SELECT count(*) FROM execution WHERE status = 'duplicate'),
    'ordinals', COALESCE(
        (SELECT json_agg(input_ordinal ORDER BY input_ordinal) FROM execution),
        '[]'::json
    )
)::text
FROM phase2.run_manifests AS manifest
WHERE run_id = {literal(context.run_id)};
"""
    )
    if len(rows) != 1:
        raise ReconciliationError(context.run_id, context.execution_sequence)
    row: JsonObject = rows[0]
    source_count = row.get("source_count")
    disposition_count = row.get("disposition_count")
    accepted = row.get("accepted")
    quarantined = row.get("quarantined")
    duplicate = row.get("duplicate")
    ordinals = row.get("ordinals")
    match (
        source_count,
        disposition_count,
        accepted,
        quarantined,
        duplicate,
        ordinals,
    ):
        case (
            int() as source_count,
            int() as disposition_count,
            int() as accepted,
            int() as quarantined,
            int() as duplicate,
            list() as ordinals,
        ) if all(
            type(value) is int
            for value in (
                source_count,
                disposition_count,
                accepted,
                quarantined,
                duplicate,
            )
        ):
            pass
        case _:
            raise ReconciliationError(context.run_id, context.execution_sequence)
    terminal_count = accepted + quarantined + duplicate
    if (
        disposition_count != source_count
        or terminal_count != source_count
        or ordinals != list(range(source_count))
    ):
        raise ReconciliationError(context.run_id, context.execution_sequence)
    return {
        "received": source_count,
        "accepted": accepted,
        "quarantined": quarantined,
        "duplicate": duplicate,
    }
