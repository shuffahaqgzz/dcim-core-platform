from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from typing import Final

from scripts.phase2 import capacity, db, recovery


class CapacityTests(unittest.TestCase):
    def test_admission_when_usage_is_below_threshold_passes(self) -> None:
        # Given
        output = io.StringIO()

        # When
        with redirect_stdout(output):
            result = capacity.run(["--force-threshold-for-test", "89.999"])

        # Then
        self.assertEqual(0, result)
        self.assertIn("PASS", output.getvalue())

    def test_admission_when_forced_usage_is_100_refuses_with_reason(self) -> None:
        # Given
        output = io.StringIO()

        # When
        with redirect_stderr(output):
            result = capacity.run(["--force-threshold-for-test", "100"])

        # Then
        self.assertEqual(1, result)
        self.assertIn("REFUSED", output.getvalue())
        self.assertIn("at or above the 90% admission threshold", output.getvalue())

    def test_admission_when_usage_equals_90_refuses(self) -> None:
        # Given / When / Then
        self.assertFalse(capacity.admit(90.0))

    def test_admission_when_forced_usage_is_nonfinite_rejects_explicitly(
        self,
    ) -> None:
        # Given
        for value in ("nan", "inf", "-inf"):
            with self.subTest(value=value):
                output = io.StringIO()

                # When
                with (
                    patch.object(
                        sys,
                        "argv",
                        [
                            "capacity.py",
                            f"--force-threshold-for-test={value}",
                        ],
                    ),
                    redirect_stderr(output),
                ):
                    result = capacity.main()

                # Then
                self.assertEqual(1, result)
                self.assertIn(
                    "capacity percentage must be finite", output.getvalue()
                )

    def test_measurement_when_postgres_reports_usage_returns_percentage(self) -> None:
        # Given
        rows = [{"usage_percent": 12.5}]

        # When
        with patch("scripts.phase2.capacity.db.query_json", return_value=rows):
            result = capacity.measured_usage_percent()

        # Then
        self.assertEqual(12.5, result)


class RecoveryUnitTests(unittest.TestCase):
    TABLES: Final = ("events", "run_manifests")
    DIGESTS: Final = {
        "events": recovery.TableDigest(6, "a" * 32),
        "run_manifests": recovery.TableDigest(1, "b" * 32),
    }

    def test_dump_when_invoked_uses_only_synthetic_phase2_schema(self) -> None:
        # Given
        completed = subprocess.CompletedProcess([], 0, "synthetic dump\n", "")
        environment = {
            "DCIM_RUNTIME_ROOT": "/synthetic/runtime",
            "COMPOSE_PROJECT_NAME": "dcim-build",
        }
        commands: list[list[str]] = []

        def fake_run(
            command: list[str],
            *,
            cwd: Path,
            capture_output: bool,
            text: bool,
            timeout: int,
            check: bool,
            shell: bool,
            env: dict[str, str],
        ) -> subprocess.CompletedProcess[str]:
            commands.append(command)
            self.assertEqual(recovery.ROOT, cwd)
            self.assertTrue(capture_output)
            self.assertTrue(text)
            self.assertEqual(db.COMMAND_TIMEOUT_SECONDS, timeout)
            self.assertFalse(check)
            self.assertFalse(shell)
            self.assertEqual("dcim-build", env["COMPOSE_PROJECT_NAME"])
            return completed

        # When
        with (
            patch.dict(os.environ, environment, clear=True),
            patch(
                "scripts.phase2.recovery.db.compose_prefix",
                return_value=["docker", "compose", "protected"],
            ),
            patch(
                "scripts.phase2.recovery.subprocess.run", side_effect=fake_run
            ),
        ):
            dump = recovery.dump_phase2()

        # Then
        self.assertEqual("synthetic dump\n", dump)
        self.assertEqual(1, len(commands))
        command = commands[0]
        self.assertEqual(
            [
                "docker",
                "compose",
                "protected",
                "exec",
                "-T",
                "postgres",
                "pg_dump",
                "-U",
                "dcim_bootstrap",
                "-d",
                "dcim_foundation",
                "--schema=phase2",
                "--no-owner",
            ],
            command,
        )
        self.assertNotIn("--schema=foundation", command)

    def test_recovery_when_checksums_match_reports_pass_and_preserves_live(self) -> None:
        # Given
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as raw:
            calls: list[tuple[str, str]] = []

            def fake_psql(sql: str, database: str = db.DEFAULT_DATABASE) -> str:
                calls.append((sql, database))
                return ""

            # When
            with (
                patch.dict(
                    os.environ,
                    {
                        "DCIM_RUNTIME_ROOT": raw,
                        "COMPOSE_PROJECT_NAME": "dcim-build",
                    },
                    clear=True,
                ),
                patch(
                    "scripts.phase2.recovery._table_inventory",
                    side_effect=(self.TABLES, self.TABLES),
                ),
                patch(
                    "scripts.phase2.recovery._snapshot",
                    side_effect=(self.DIGESTS, self.DIGESTS, self.DIGESTS),
                ),
                patch(
                    "scripts.phase2.recovery.dump_phase2",
                    return_value="synthetic dump\n",
                ),
                patch("scripts.phase2.recovery.db.psql", side_effect=fake_psql),
                redirect_stdout(output),
            ):
                tables = recovery.verify_recovery()

            # Then
            dump = Path(raw, *recovery.DUMP_PARTS)
            self.assertEqual("synthetic dump\n", dump.read_text(encoding="utf-8"))
        self.assertEqual(self.TABLES, tables)
        self.assertIn("live-schema-unchanged PASS", output.getvalue())
        self.assertIn("temporary-database-dropped PASS", output.getvalue())
        self.assertEqual(
            [
                (
                    f'DROP DATABASE IF EXISTS "{recovery.RECOVERY_DATABASE}";',
                    "postgres",
                ),
                (
                    f'CREATE DATABASE "{recovery.RECOVERY_DATABASE}";',
                    "postgres",
                ),
                ("synthetic dump\n", recovery.RECOVERY_DATABASE),
                (
                    f'DROP DATABASE IF EXISTS "{recovery.RECOVERY_DATABASE}";',
                    "postgres",
                ),
            ],
            calls,
        )
        self.assertTrue(all("DROP SCHEMA" not in sql for sql, _ in calls))

    def test_recovery_when_restore_is_corrupt_still_drops_temp_database(self) -> None:
        # Given
        calls: list[tuple[str, str]] = []
        corrupt = "CREATE SCHEMA phase2;\nBROKEN"

        def fake_psql(sql: str, database: str = db.DEFAULT_DATABASE) -> str:
            calls.append((sql, database))
            if database == recovery.RECOVERY_DATABASE:
                raise db.DatabaseCommandError("forced corrupt restore")
            return ""

        # When
        with tempfile.TemporaryDirectory() as raw:
            with (
                patch.dict(os.environ, {"DCIM_RUNTIME_ROOT": raw}, clear=True),
                patch(
                    "scripts.phase2.recovery._table_inventory",
                    return_value=self.TABLES,
                ),
                patch(
                    "scripts.phase2.recovery._snapshot", return_value=self.DIGESTS
                ),
                patch("scripts.phase2.recovery.dump_phase2", return_value=corrupt),
                patch("scripts.phase2.recovery.db.psql", side_effect=fake_psql),
                self.assertRaisesRegex(db.DatabaseCommandError, "corrupt restore"),
            ):
                _ = recovery.verify_recovery()

        # Then
        drop = f'DROP DATABASE IF EXISTS "{recovery.RECOVERY_DATABASE}";'
        self.assertEqual((drop, "postgres"), calls[-1])
        self.assertEqual(2, sum(sql == drop for sql, _ in calls))


if __name__ == "__main__":
    _ = unittest.main()
