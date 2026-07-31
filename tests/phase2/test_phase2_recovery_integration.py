from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
from unittest.mock import patch
from typing import override

from scripts.phase2 import db, migrate, recovery


class RecoveryIntegrationTests(unittest.TestCase):
    run_id = "recovery-integration-synthetic"

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
        command = [
            sys.executable,
            "scripts/phase2/run.py",
            "--run-id",
            cls.run_id,
            "--fixtures-dir",
            "fixtures/synthetic/events",
            "--fixed-clock",
            "2026-07-29T00:00:00Z",
        ]
        result = subprocess.run(
            command,
            cwd=recovery.ROOT,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=db.COMMAND_TIMEOUT_SECONDS,
        )
        if result.returncode:
            raise RuntimeError(f"synthetic recovery seed failed with exit {result.returncode}")

    @classmethod
    @override
    def tearDownClass(cls) -> None:
        run_id = db.literal(cls.run_id)
        _ = db.psql(
            f"""
DELETE FROM phase2.noc_cards WHERE run_id = {run_id};
DELETE FROM phase2.dispositions WHERE run_id = {run_id};
DELETE FROM phase2.events WHERE run_id = {run_id};
DELETE FROM phase2.run_manifests WHERE run_id = {run_id};
DELETE FROM phase2.aliases;
DELETE FROM phase2.cis;
DELETE FROM phase2.assets;
"""
        )

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

    def test_recovery_when_one_table_data_is_missing_reports_count_mismatch_and_cleans_up(
        self,
    ) -> None:
        dump = db.pg_dump(schema="phase2")
        partial, replacements = re.subn(
            r"(?ms)(^COPY phase2\.events \([^\n]+\) FROM stdin;\n).*?^\\\.\n",
            r"\1\\.\n",
            dump,
            count=1,
        )
        self.assertEqual(1, replacements)

        with (
            patch("scripts.phase2.recovery.dump_phase2", return_value=partial),
            self.assertRaisesRegex(
                recovery.RecoveryError,
                r"events: restored checksum or row count mismatch \(expected rows=[1-9][0-9]*, actual rows=0\)",
            ),
        ):
            _ = recovery.verify_recovery()

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
