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


def durable_snapshot(run_id: str) -> dict[str, db.JsonValue]:
    return db.query_json(
        f"""
SELECT json_build_object(
    'manifest_wire', (
        SELECT row_to_json(manifest)::text
        FROM phase2.run_manifests AS manifest
        WHERE run_id = '{run_id}'
    ),
    'disposition_count', (
        SELECT count(*) FROM phase2.dispositions WHERE run_id = '{run_id}'
    )
)::text;
"""
    )[0]


class ManifestDriftCliTests(unittest.TestCase):
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

    def test_exact_same_directory_extra_fixture_drift_preserves_durable_state(
        self,
    ) -> None:
        run_id = "exact-drift-main"
        with tempfile.TemporaryDirectory() as raw:
            fixtures = Path(raw)
            for source in FIXTURES.glob("*.json"):
                shutil.copy2(source, fixtures / source.name)
            first_result, first_stdout, first_stderr = invoke_main(run_id, fixtures)
            before = durable_snapshot(run_id)
            shutil.copy2(
                FIXTURES / "p1-redfish-health.json",
                fixtures / "z-extra.json",
            )
            drift_result, drift_stdout, drift_stderr = invoke_main(run_id, fixtures)
            after = durable_snapshot(run_id)

        self.assertEqual(0, first_result)
        self.assertEqual("", first_stderr)
        self.assertIn('"reconciled":true', first_stdout)
        self.assertEqual(1, drift_result)
        self.assertEqual("", drift_stdout)
        self.assertIn("ManifestDriftError", drift_stderr)
        self.assertEqual(before, after)
        self.assertEqual(6, after["disposition_count"])


if __name__ == "__main__":
    unittest.main()
