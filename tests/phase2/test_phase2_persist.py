from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.phase2 import db
from scripts.phase2.db import DatabaseCommandError
from scripts.phase2.errors import ManifestDriftError
from scripts.phase2.migrate import MIGRATION_ID, MigrationError, apply, rollback
from scripts.phase2.run import execute


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures/synthetic/events"
INVALID = ROOT / "fixtures/synthetic/invalid/invalid-event.json"
CLOCK = "2026-07-29T00:00:00Z"


def rows(sql: str) -> list[db.JsonObject]:
    return db.query_json(sql)


def counts() -> dict[str, int]:
    result = rows(
        """
SELECT json_build_object(
    'events', (SELECT count(*) FROM phase2.events),
    'assets', (SELECT count(*) FROM phase2.assets),
    'cis', (SELECT count(*) FROM phase2.cis),
    'aliases', (SELECT count(*) FROM phase2.aliases),
    'run_manifests', (SELECT count(*) FROM phase2.run_manifests),
    'dispositions', (SELECT count(*) FROM phase2.dispositions)
)::text;
"""
    )
    if len(result) != 1:
        raise AssertionError("count query returned unexpected rows")
    return {key: int(value) for key, value in result[0].items()}


class PostgresPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            probe = rows("SELECT json_build_object('reachable', true)::text;")
        except DatabaseCommandError as error:
            raise unittest.SkipTest(
                f"PostgreSQL integration unavailable: {error}"
            ) from error
        if probe != [{"reachable": True}]:
            raise unittest.SkipTest("PostgreSQL integration probe returned invalid data")

    def setUp(self) -> None:
        try:
            rollback(MIGRATION_ID)
        except MigrationError as error:
            if str(error) != "migration is not applied":
                raise
        self.assertEqual(2, apply())

    def test_full_replay_is_duplicate_and_authoritative_rows_are_stable(self) -> None:
        first = execute("synthetic-run-001", FIXTURES, CLOCK)
        first_counts = counts()
        second = execute("synthetic-run-001", FIXTURES, CLOCK)
        second_counts = counts()

        self.assertEqual(6, first["counts"]["accepted"])
        self.assertEqual(6, second["counts"]["duplicate"])
        for table in ("events", "assets", "cis", "aliases", "run_manifests"):
            self.assertEqual(first_counts[table], second_counts[table], table)
        self.assertEqual(
            first_counts["dispositions"] + second["counts"]["received"],
            second_counts["dispositions"],
        )
        executions = rows(
            """
SELECT json_build_object(
    'execution_sequence', execution_sequence,
    'ordinals', json_agg(input_ordinal ORDER BY input_ordinal)
)::text
FROM phase2.dispositions
WHERE run_id = 'synthetic-run-001'
GROUP BY execution_sequence
ORDER BY execution_sequence;
"""
        )
        self.assertEqual(
            [
                {"execution_sequence": 1, "ordinals": [0, 1, 2, 3, 4, 5]},
                {"execution_sequence": 2, "ordinals": [0, 1, 2, 3, 4, 5]},
            ],
            executions,
        )

    def test_content_conflict_quarantines_without_mutating_event(self) -> None:
        with tempfile.TemporaryDirectory() as first_raw, tempfile.TemporaryDirectory() as changed_raw:
            first_dir = Path(first_raw)
            changed_dir = Path(changed_raw)
            source = FIXTURES / "p1-redfish-health.json"
            shutil.copy2(source, first_dir / source.name)
            candidate = json.loads(source.read_text(encoding="utf-8"))
            candidate["payload"]["health"] = "Critical"
            (changed_dir / source.name).write_text(
                json.dumps(candidate), encoding="utf-8"
            )

            execute("original-run", first_dir, CLOCK)
            before = rows(
                """
SELECT json_build_object('envelope', envelope::text)::text
FROM phase2.events;
"""
            )
            summary = execute("changed-run", changed_dir, CLOCK)
            after = rows(
                """
SELECT json_build_object('envelope', envelope::text)::text
FROM phase2.events;
"""
            )
            disposition = rows(
                """
SELECT json_build_object('status', status, 'reason', reason)::text
FROM phase2.dispositions
WHERE run_id = 'changed-run';
"""
            )

        self.assertEqual(before, after)
        self.assertEqual(1, summary["counts"]["quarantined"])
        self.assertEqual(
            [
                {
                    "status": "quarantined",
                    "reason": "event_id_content_conflict",
                }
            ],
            disposition,
        )

    def test_invalid_first_is_durable_after_manifest_commit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture_dir = Path(raw)
            shutil.copy2(INVALID, fixture_dir / "000-invalid.json")
            summary = execute("invalid-first", fixture_dir, CLOCK)
            durable = rows(
                """
SELECT json_build_object(
    'event_id_is_null', event_id IS NULL,
    'status', status,
    'reason', reason,
    'raw_id', lineage->>'raw_rejected_identifier',
    'has_detail', length(lineage->>'validation_detail') > 0
)::text
FROM phase2.dispositions
WHERE run_id = 'invalid-first';
"""
            )
            durable_counts = counts()

        self.assertEqual(
            {"received": 1, "accepted": 0, "quarantined": 1, "duplicate": 0},
            summary["counts"],
        )
        self.assertEqual(1, durable_counts["run_manifests"])
        self.assertEqual(0, durable_counts["events"])
        self.assertEqual(1, durable_counts["dispositions"])
        self.assertEqual(
            [
                {
                    "event_id_is_null": True,
                    "status": "quarantined",
                    "reason": "schema_invalid",
                    "raw_id": "SYNTHETIC-INVALID-ID",
                    "has_detail": True,
                }
            ],
            durable,
        )

    def test_manifest_drift_fails_closed_and_rollback_reingests_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            changed = Path(raw)
            shutil.copy2(FIXTURES / "p1-redfish-health.json", changed / "only.json")
            execute("stable-run", FIXTURES, CLOCK)
            before = rows(
                """
SELECT json_build_object(
    'run_id', run_id,
    'source_count', source_count,
    'manifest_sha256', manifest_sha256
)::text
FROM phase2.run_manifests
WHERE run_id = 'stable-run';
"""
            )
            with self.assertRaises(ManifestDriftError):
                execute("stable-run", changed, CLOCK)
            after = rows(
                """
SELECT json_build_object(
    'run_id', run_id,
    'source_count', source_count,
    'manifest_sha256', manifest_sha256
)::text
FROM phase2.run_manifests
WHERE run_id = 'stable-run';
"""
            )
        self.assertEqual(before, after)
        self.assertEqual(6, counts()["events"])

        rollback(MIGRATION_ID)
        self.assertEqual(2, apply())
        summary = execute("clean-reingest", FIXTURES, CLOCK)
        self.assertEqual(6, summary["counts"]["accepted"])
        self.assertEqual(6, counts()["events"])


if __name__ == "__main__":
    unittest.main()
