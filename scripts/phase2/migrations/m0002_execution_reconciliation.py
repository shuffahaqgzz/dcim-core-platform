"""Add replay-safe execution identity to manifests and dispositions."""

from __future__ import annotations


MIGRATION_ID = "m0002_execution_reconciliation"


def up() -> str:
    """Return SQL that adds execution-scoped reconciliation fields."""
    return """
ALTER TABLE phase2.run_manifests
    ADD COLUMN last_execution_sequence bigint NOT NULL DEFAULT 0,
    ADD CONSTRAINT run_manifests_execution_sequence_nonnegative
        CHECK (last_execution_sequence >= 0);

ALTER TABLE phase2.dispositions
    ADD COLUMN execution_sequence bigint,
    ADD COLUMN input_ordinal int;

WITH ranked AS (
    SELECT disposition_id,
        row_number() OVER (
            PARTITION BY run_id ORDER BY disposition_id
        ) - 1 AS legacy_ordinal
    FROM phase2.dispositions
)
UPDATE phase2.dispositions AS disposition
SET execution_sequence = 0,
    input_ordinal = ranked.legacy_ordinal
FROM ranked
WHERE ranked.disposition_id = disposition.disposition_id;

ALTER TABLE phase2.dispositions
    ALTER COLUMN execution_sequence SET NOT NULL,
    ALTER COLUMN input_ordinal SET NOT NULL,
    ADD CONSTRAINT dispositions_execution_sequence_nonnegative
        CHECK (execution_sequence >= 0),
    ADD CONSTRAINT dispositions_input_ordinal_nonnegative
        CHECK (input_ordinal >= 0),
    ADD CONSTRAINT dispositions_execution_input_unique
        UNIQUE (run_id, execution_sequence, input_ordinal);
"""


def down() -> str:
    """Return SQL that removes execution-scoped reconciliation fields."""
    return """
ALTER TABLE phase2.dispositions
    DROP CONSTRAINT dispositions_execution_input_unique,
    DROP CONSTRAINT dispositions_input_ordinal_nonnegative,
    DROP CONSTRAINT dispositions_execution_sequence_nonnegative,
    DROP COLUMN input_ordinal,
    DROP COLUMN execution_sequence;

ALTER TABLE phase2.run_manifests
    DROP CONSTRAINT run_manifests_execution_sequence_nonnegative,
    DROP COLUMN last_execution_sequence;
"""
