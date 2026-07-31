from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from typing import Final

from scripts.phase2 import capacity, db, recovery


class CapacityTests(unittest.TestCase):
    def test_admission_when_measured_usage_is_below_threshold_passes(self) -> None:
        # Given
        output = io.StringIO()

        # When
        with (
            patch(
                "scripts.phase2.capacity.measured_usage_percent",
                return_value=89.999,
            ),
            redirect_stdout(output),
        ):
            result = capacity.run([])

        # Then
        self.assertEqual(0, result)
        self.assertIn("PASS", output.getvalue())

    def test_admission_when_forced_usage_is_below_threshold_is_rejected(self) -> None:
        # Given
        output = io.StringIO()

        # When
        with (
            patch.object(
                sys,
                "argv",
                ["capacity.py", "--force-threshold-for-test", "0"],
            ),
            redirect_stdout(output),
            redirect_stderr(output),
        ):
            result = capacity.main()

        # Then
        self.assertEqual(1, result)
        self.assertIn("can only force a refusal", output.getvalue())
        self.assertNotIn("PASS", output.getvalue())

    def test_admission_when_forced_usage_is_below_threshold_never_measures(self) -> None:
        # Given
        measurement = patch(
            "scripts.phase2.capacity.measured_usage_percent",
            side_effect=AssertionError("measurement must not run"),
        )

        # When
        with (
            measurement,
            patch.object(
                sys,
                "argv",
                ["capacity.py", "--force-threshold-for-test", "89.999"],
            ),
            redirect_stderr(io.StringIO()),
        ):
            result = capacity.main()

        # Then
        self.assertEqual(1, result)

    def test_admission_when_forced_usage_equals_threshold_refuses(self) -> None:
        # Given
        output = io.StringIO()

        # When
        with redirect_stderr(output):
            result = capacity.run(["--force-threshold-for-test", "90"])

        # Then
        self.assertEqual(1, result)
        self.assertIn("REFUSED", output.getvalue())

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
        with patch(
            "scripts.phase2.recovery.db.pg_dump",
            return_value="synthetic dump\n",
        ) as pg_dump:
            dump = recovery.dump_phase2()

        self.assertEqual("synthetic dump\n", dump)
        pg_dump.assert_called_once_with(schema="phase2", database=db.DEFAULT_DATABASE)

    def test_recovery_when_all_live_tables_are_empty_is_unverifiable(self) -> None:
        empty = {table: recovery.TableDigest(0, "d41d8cd98f00b204e9800998ecf8427e") for table in self.TABLES}
        with tempfile.TemporaryDirectory() as raw:
            with (
                patch.dict(os.environ, {"DCIM_RUNTIME_ROOT": raw}, clear=True),
                patch("scripts.phase2.recovery._table_inventory", return_value=self.TABLES),
                patch("scripts.phase2.recovery._snapshot", return_value=empty),
                patch("scripts.phase2.recovery.db.psql", return_value=""),
                patch("scripts.phase2.recovery._temporary_database_exists", return_value=False),
                self.assertRaisesRegex(recovery.RecoveryError, "unverifiable.*total live row count is zero"),
            ):
                recovery.verify_recovery()

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
                patch("scripts.phase2.recovery._temporary_database_exists", return_value=False),
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
                patch("scripts.phase2.recovery._temporary_database_exists", return_value=False),
                self.assertRaisesRegex(db.DatabaseCommandError, "corrupt restore"),
            ):
                _ = recovery.verify_recovery()

        # Then
        drop = f'DROP DATABASE IF EXISTS "{recovery.RECOVERY_DATABASE}";'
        self.assertEqual((drop, "postgres"), calls[-1])
        self.assertEqual(2, sum(sql == drop for sql, _ in calls))

    def test_recovery_when_restore_and_cleanup_fail_reports_both_errors(self) -> None:
        calls = 0

        def fake_psql(sql: str, database: str = db.DEFAULT_DATABASE) -> str:
            nonlocal calls
            calls += 1
            if calls >= 3:
                raise db.DatabaseCommandError("forced cleanup failure")
            return ""

        with tempfile.TemporaryDirectory() as raw:
            with (
                patch.dict(os.environ, {"DCIM_RUNTIME_ROOT": raw}, clear=True),
                patch("scripts.phase2.recovery._table_inventory", return_value=self.TABLES),
                patch("scripts.phase2.recovery._snapshot", return_value=self.DIGESTS),
                patch("scripts.phase2.recovery.dump_phase2", return_value="BROKEN"),
                patch("scripts.phase2.recovery.db.psql", side_effect=fake_psql),
                self.assertRaisesRegex(
                    recovery.RecoveryError,
                    "recovery failed: forced cleanup failure; temporary database cleanup failed: forced cleanup failure",
                ),
            ):
                recovery.verify_recovery()


if __name__ == "__main__":
    _ = unittest.main()
