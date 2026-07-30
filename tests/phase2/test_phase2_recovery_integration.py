from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from typing import override

from scripts.phase2 import db, migrate, recovery


class RecoveryIntegrationTests(unittest.TestCase):
    @classmethod
    @override
    def setUpClass(cls) -> None:
        state_home = os.environ.get("XDG_STATE_HOME")
        default_root = (
            Path(state_home) if state_home else Path.home() / ".local/state"
        ) / "dcim-core-platform/runtime"
        _ = os.environ.setdefault("DCIM_RUNTIME_ROOT", str(default_root))
        _ = os.environ.setdefault("COMPOSE_PROJECT_NAME", "dcim-build")
        try:
            _ = db.query_json("SELECT json_build_object('ready', true)::text;")
        except db.DatabaseCommandError as error:
            raise unittest.SkipTest(
                f"Compose PostgreSQL unavailable: {error}"
            ) from error
        _ = migrate.apply()

    def _live_counts(self) -> list[db.JsonObject]:
        return db.query_json(
            """
SELECT json_build_object('table_name', table_name, 'row_count', row_count)::text
FROM (
    SELECT 'events' AS table_name, count(*) AS row_count FROM phase2.events
    UNION ALL
    SELECT 'run_manifests', count(*) FROM phase2.run_manifests
) counts
ORDER BY table_name;
"""
        )

    def _temporary_database_exists(self) -> bool:
        rows = db.query_json(
            f"""
SELECT json_build_object(
    'exists',
    EXISTS (SELECT 1 FROM pg_database
            WHERE datname = '{recovery.RECOVERY_DATABASE}')
)::text;
""",
            "postgres",
        )
        return rows == [{"exists": True}]

    def test_recovery_when_real_restore_succeeds_leaves_live_rows_unchanged(self) -> None:
        # Given
        before = self._live_counts()

        # When
        tables = recovery.verify_recovery()

        # Then
        self.assertEqual(tuple(sorted(migrate.EXPECTED_TABLES)), tables)
        self.assertEqual(before, self._live_counts())
        self.assertFalse(self._temporary_database_exists())

    def test_recovery_when_real_restore_is_truncated_leaves_no_temp_database(
        self,
    ) -> None:
        # Given
        truncated = "CREATE SCHEMA phase2;\nCREATE TABLE phase2.incomplete (\n"

        # When
        with (
            patch("scripts.phase2.recovery.dump_phase2", return_value=truncated),
            self.assertRaises(db.DatabaseCommandError),
        ):
            _ = recovery.verify_recovery()

        # Then
        self.assertFalse(self._temporary_database_exists())

    def test_recovery_when_two_independent_processes_run_each_completes_and_cleans_up(
        self,
    ) -> None:
        # Given
        environment = os.environ.copy()
        command = [sys.executable, str(recovery.ROOT / "scripts/phase2/recovery.py")]
        processes = [
            subprocess.Popen(
                command,
                cwd=recovery.ROOT,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for _ in range(2)
        ]
        outputs: list[str] = []

        # When
        try:
            for process in processes:
                output, _ = process.communicate(timeout=45)
                outputs.append(output)
        except subprocess.TimeoutExpired:
            for process in processes:
                process.terminate()
            for process in processes:
                _ = process.communicate()
            self.fail("concurrent recovery process exceeded the 45-second bound")

        # Then
        self.assertEqual([0, 0], [process.returncode for process in processes])
        self.assertTrue(all("phase2-recovery: PASS" in output for output in outputs))
        self.assertFalse(self._temporary_database_exists())


if __name__ == "__main__":
    _ = unittest.main()
