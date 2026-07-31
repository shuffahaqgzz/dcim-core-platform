from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.phase2 import db
from scripts.phase2.db import DatabaseCommandError
from scripts.phase2.migrate import MIGRATION_ID, MigrationError, apply, rollback
from scripts.phase2.run import main


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures/synthetic/events"
CLOCK = "2026-07-29T00:00:00Z"


def invoke_main(run_id: str, fixtures: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    argv = [
        "run.py",
        "--run-id",
        run_id,
        "--fixtures-dir",
        str(fixtures),
        "--fixed-clock",
        CLOCK,
    ]
    with patch.object(sys, "argv", argv), redirect_stdout(stdout), redirect_stderr(stderr):
        result = main()
    return result, stdout.getvalue(), stderr.getvalue()


def table_counts(run_id: str) -> dict[str, db.JsonValue]:
    return db.query_json(
        f"""
SELECT json_build_object(
    'events', (SELECT count(*) FROM phase2.events WHERE run_id = '{run_id}'),
    'dispositions', (SELECT count(*) FROM phase2.dispositions
        WHERE run_id = '{run_id}'),
    'assets', (SELECT count(*) FROM phase2.assets),
    'cis', (SELECT count(*) FROM phase2.cis),
    'aliases', (SELECT count(*) FROM phase2.aliases)
)::text;
"""
    )[0]


class PostgresFailureBoundaryTests(unittest.TestCase):
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

    def test_unexpected_oserror_from_load_json_has_live_durable_disposition(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixtures = Path(raw)
            shutil.copy2(
                FIXTURES / "p1-redfish-health.json",
                fixtures / "01-input.json",
            )
            with patch(
                "scripts.phase2.runner_input._load_json",
                side_effect=OSError("synthetic read failure"),
            ):
                result, stdout, stderr = invoke_main("oserror-durable", fixtures)
        rows = db.query_json(
            """
SELECT json_build_object(
    'status', status,
    'reason', reason,
    'detail', lineage->>'validation_detail',
    'execution_sequence', execution_sequence,
    'input_ordinal', input_ordinal
)::text
FROM phase2.dispositions
WHERE run_id = 'oserror-durable';
"""
        )

        self.assertEqual(0, result)
        self.assertEqual("", stderr)
        self.assertIn('"reconciled":true', stdout)
        self.assertEqual(
            [{
                "status": "quarantined",
                "reason": "unexpected_input_error",
                "detail": "OSError",
                "execution_sequence": 1,
                "input_ordinal": 0,
            }],
            rows,
        )

    def test_deterministic_mid_run_postgres_session_loss_rolls_back_failed_input(
        self,
    ) -> None:
        original_psql = db.psql
        state: dict[str, int | dict[str, db.JsonValue]] = {"input_calls": 0}

        def terminate_third_input(sql: str, database: str = db.DEFAULT_DATABASE) -> str:
            if "INSERT INTO phase2.events" not in sql:
                return original_psql(sql, database)
            state["input_calls"] = int(state["input_calls"]) + 1
            if state["input_calls"] != 3:
                return original_psql(sql, database)
            state["before"] = table_counts("mid-run-session-loss")
            failing_sql = sql.replace(
                "\nCOMMIT;\n",
                "\nSELECT pg_terminate_backend(pg_backend_pid());\nCOMMIT;\n",
                1,
            )
            return original_psql(failing_sql, database)

        with patch("scripts.phase2.db.psql", side_effect=terminate_third_input):
            result, stdout, stderr = invoke_main("mid-run-session-loss", FIXTURES)
        after = table_counts("mid-run-session-loss")

        self.assertEqual(1, result)
        self.assertEqual("", stdout)
        self.assertIn("DatabaseCommandError", stderr)
        self.assertEqual(state["before"], after)
        self.assertNotIn("durability_guarantee", stdout)

    def test_deferred_commit_failure_rolls_back_every_input_write(self) -> None:
        run_id = "deferred-commit-failure"
        db.psql(
            f"""
CREATE FUNCTION phase2.r09_fail_commit_fn() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.run_id = '{run_id}' THEN
        RAISE EXCEPTION 'synthetic deferred commit failure';
    END IF;
    RETURN NEW;
END;
$$;
CREATE CONSTRAINT TRIGGER r09_fail_commit_trigger
AFTER INSERT ON phase2.dispositions
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION phase2.r09_fail_commit_fn();
"""
        )
        try:
            with tempfile.TemporaryDirectory() as raw:
                fixtures = Path(raw)
                shutil.copy2(
                    FIXTURES / "p1-redfish-health.json",
                    fixtures / "01-input.json",
                )
                result, stdout, stderr = invoke_main(run_id, fixtures)
            durable = table_counts(run_id)
        finally:
            db.psql(
                """
DROP TRIGGER IF EXISTS r09_fail_commit_trigger ON phase2.dispositions;
DROP FUNCTION IF EXISTS phase2.r09_fail_commit_fn();
"""
            )

        self.assertEqual(1, result)
        self.assertEqual("", stdout)
        self.assertIn("DatabaseCommandError", stderr)
        self.assertEqual(
            {"events": 0, "dispositions": 0, "assets": 0, "cis": 0, "aliases": 0},
            durable,
        )


if __name__ == "__main__":
    unittest.main()
