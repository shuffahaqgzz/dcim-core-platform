from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from scripts.phase2 import db
from scripts.phase2.db import DatabaseCommandError
from scripts.phase2.migrate import MIGRATION_ID, MigrationError, apply, rollback
from scripts.phase2.reconcile import main as reconcile_main
from scripts.phase2.run import main as pipeline_main


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures/synthetic/events"
CLOCK = "2026-07-29T00:00:00Z"


def invoke_pipeline(run_id: str) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    argv = [
        "run.py",
        "--run-id",
        run_id,
        "--fixtures-dir",
        str(FIXTURES),
        "--fixed-clock",
        CLOCK,
    ]
    with patch.object(sys, "argv", argv), redirect_stdout(stdout), redirect_stderr(stderr):
        result = pipeline_main()
    return result, stdout.getvalue(), stderr.getvalue()


def invoke_reconcile(*arguments: str) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with (
        patch.object(sys, "argv", ["reconcile.py", *arguments]),
        redirect_stdout(stdout),
        redirect_stderr(stderr),
    ):
        result = reconcile_main()
    return result, stdout.getvalue(), stderr.getvalue()


class Phase2ReconciliationCliTests(unittest.TestCase):
    run_ids = (
        "reconcile-shortfall",
        "reconcile-ordinal-gap",
        "reconcile-healthy",
        "reconcile-multi-execution",
    )

    @classmethod
    def setUpClass(cls) -> None:
        try:
            db.query_json("SELECT json_build_object('reachable', true)::text;")
        except DatabaseCommandError as error:
            raise unittest.SkipTest(
                f"PostgreSQL integration unavailable: {error}"
            ) from error

    def setUp(self) -> None:
        try:
            rollback(MIGRATION_ID)
        except MigrationError as error:
            if str(error) != "migration is not applied":
                raise
        self.assertEqual(2, apply())

    def tearDown(self) -> None:
        run_ids = ", ".join(db.literal(run_id) for run_id in self.run_ids)
        db.psql(
            f"""
DELETE FROM phase2.noc_cards WHERE run_id IN ({run_ids});
DELETE FROM phase2.dispositions WHERE run_id IN ({run_ids});
DELETE FROM phase2.events WHERE run_id IN ({run_ids});
DELETE FROM phase2.run_manifests WHERE run_id IN ({run_ids});
"""
        )

    def test_shortfall_surfaces_reconciliation_error_without_success_output(self) -> None:
        run_id = "reconcile-shortfall"
        result, _, pipeline_stderr = invoke_pipeline(run_id)
        self.assertEqual(0, result)
        self.assertEqual("", pipeline_stderr)
        db.psql(
            f"""
DELETE FROM phase2.dispositions
WHERE disposition_id = (
    SELECT disposition_id
    FROM phase2.dispositions
    WHERE run_id = {db.literal(run_id)} AND execution_sequence = 1
    ORDER BY input_ordinal
    LIMIT 1
);
"""
        )

        result, stdout, stderr = invoke_reconcile("--run-id", run_id)

        self.assertNotEqual(0, result)
        self.assertEqual("", stdout)
        self.assertIn("ReconciliationError", stderr)
        self.assertIn(f"{run_id}/1", stderr)
        self.assertIn("expected", stderr)
        self.assertIn("actual", stderr)

    def test_ordinal_gap_fails_even_when_disposition_count_matches(self) -> None:
        run_id = "reconcile-ordinal-gap"
        result, _, _ = invoke_pipeline(run_id)
        self.assertEqual(0, result)
        db.psql(
            f"""
WITH removed AS (
    DELETE FROM phase2.dispositions
    WHERE disposition_id = (
        SELECT disposition_id
        FROM phase2.dispositions
        WHERE run_id = {db.literal(run_id)} AND execution_sequence = 1
        ORDER BY input_ordinal DESC
        LIMIT 1
    )
    RETURNING event_id, run_id, status, reason, lineage, decided_at,
        execution_sequence
)
INSERT INTO phase2.dispositions
    (event_id, run_id, status, reason, lineage, decided_at,
     execution_sequence, input_ordinal)
SELECT event_id, run_id, status, reason, lineage, decided_at,
    execution_sequence, 999
FROM removed;
"""
        )

        result, stdout, stderr = invoke_reconcile("--run-id", run_id)

        self.assertNotEqual(0, result)
        self.assertEqual("", stdout)
        self.assertIn(f"{run_id}/1", stderr)

    def test_healthy_execution_prints_canonical_success_json(self) -> None:
        run_id = "reconcile-healthy"
        result, _, _ = invoke_pipeline(run_id)
        self.assertEqual(0, result)

        result, stdout, stderr = invoke_reconcile("--run-id", run_id)

        self.assertEqual(0, result)
        self.assertEqual("", stderr)
        summary = json.loads(stdout)
        self.assertEqual(run_id, summary["run_id"])
        self.assertEqual([1], summary["execution_sequences"])
        self.assertTrue(summary["reconciled"])
        self.assertEqual(
            json.dumps(
                summary,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ) + "\n",
            stdout,
        )

    def test_run_id_scope_checks_all_executions_and_finds_earlier_damage(self) -> None:
        run_id = "reconcile-multi-execution"
        first_result, _, _ = invoke_pipeline(run_id)
        second_result, _, _ = invoke_pipeline(run_id)
        self.assertEqual((0, 0), (first_result, second_result))
        db.psql(
            f"""
DELETE FROM phase2.dispositions
WHERE disposition_id = (
    SELECT disposition_id
    FROM phase2.dispositions
    WHERE run_id = {db.literal(run_id)} AND execution_sequence = 1
    ORDER BY input_ordinal
    LIMIT 1
);
"""
        )

        result, stdout, stderr = invoke_reconcile("--run-id", run_id)

        self.assertNotEqual(0, result)
        self.assertEqual("", stdout)
        self.assertIn(f"{run_id}/1", stderr)

    def test_unknown_run_id_is_not_a_false_pass(self) -> None:
        result, stdout, stderr = invoke_reconcile(
            "--run-id", "reconcile-unknown"
        )

        self.assertNotEqual(0, result)
        self.assertEqual("", stdout)
        self.assertIn("no manifest", stderr)

    def test_execution_sequence_above_manifest_is_not_a_false_pass(self) -> None:
        run_id = "reconcile-healthy"
        result, _, _ = invoke_pipeline(run_id)
        self.assertEqual(0, result)

        result, stdout, stderr = invoke_reconcile(
            "--run-id", run_id, "--execution-sequence", "2"
        )

        self.assertNotEqual(0, result)
        self.assertEqual("", stdout)
        self.assertIn("exceeds last_execution_sequence 1", stderr)


if __name__ == "__main__":
    unittest.main()
