from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.phase2 import db, migrate
from scripts.phase2.db import literal
from scripts.phase2.migrations import m0001_phase2_core


class JsonExtractionTests(unittest.TestCase):
    def test_parse_json_rows_when_rows_are_objects_returns_canonical_values(self) -> None:
        # Given
        output = '{"value":1,"nested":{"ready":true}}\n{"value":2}\n'

        # When
        rows = db.parse_json_rows(output)

        # Then
        self.assertEqual(
            [
                {"value": 1, "nested": {"ready": True}},
                {"value": 2},
            ],
            rows,
        )

    def test_parse_json_rows_when_output_is_empty_returns_no_rows(self) -> None:
        # Given / When
        rows = db.parse_json_rows("")

        # Then
        self.assertEqual([], rows)

    def test_parse_json_rows_when_line_is_invalid_fails_loudly(self) -> None:
        for output, reason in (
            ('{"ok":true}\n\n{"ok":false}\n', "blank row"),
            ("not-json\n", "malformed JSON"),
            ("[1,2]\n", "expected a JSON object"),
        ):
            with self.subTest(reason=reason):
                # Given / When / Then
                with self.assertRaisesRegex(db.JsonExtractionError, reason):
                    db.parse_json_rows(output)

    def test_parse_json_rows_when_value_is_nonfinite_fails_loudly(self) -> None:
        # Given / When / Then
        with self.assertRaisesRegex(db.JsonExtractionError, "malformed JSON"):
            db.parse_json_rows('{"value":NaN}\n')

    def test_parse_json_rows_when_object_key_is_repeated_fails_loudly(self) -> None:
        # Given / When / Then
        with self.assertRaisesRegex(db.JsonExtractionError, "malformed JSON"):
            db.parse_json_rows('{"value":1,"value":2}\n')


class DatabaseCommandTests(unittest.TestCase):
    def test_compose_prefix_when_normal_project_has_override_rejects_it(self) -> None:
        # Given
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                os.environ,
                {
                    "DCIM_RUNTIME_ROOT": directory,
                    "COMPOSE_PROJECT_NAME": "dcim-build",
                    "DCIM_COMPOSE_OVERRIDE": "/synthetic/override.yaml",
                },
                clear=True,
            ),
        ):
            # When / Then
            with self.assertRaisesRegex(
                db.DatabaseCommandError,
                "override is prohibited",
            ):
                db.compose_prefix()

    def test_compose_prefix_when_acceptance_project_uses_protected_override(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            override = root / "dev-build" / db.ACCEPTANCE_OVERRIDE_NAME
            override.parent.mkdir()
            override.write_text("services: {}\n", encoding="utf-8")
            environment = {
                "DCIM_RUNTIME_ROOT": directory,
                "COMPOSE_PROJECT_NAME": "dcim-build-acceptance-abcdef123456",
                "DCIM_COMPOSE_OVERRIDE": str(override),
            }

            # When
            with patch.dict(os.environ, environment, clear=True):
                prefix = db.compose_prefix()

        # Then
        self.assertEqual(["-f", str(override)], prefix[8:10])

    def test_psql_when_called_uses_exact_protected_argv_and_stdin(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory)
            environment = {
                "DCIM_RUNTIME_ROOT": str(runtime_root),
                "COMPOSE_PROJECT_NAME": "dcim-build",
            }
            completed = subprocess.CompletedProcess([], 0, "result\n", "")

            # When
            with (
                patch.dict(os.environ, environment, clear=True),
                patch("scripts.phase2.db.subprocess.run", return_value=completed) as run,
            ):
                output = db.psql("SELECT 1;\n", "synthetic_db")

        # Then
        command = run.call_args.args[0]
        self.assertEqual(["docker", "compose"], command[:2])
        self.assertEqual(
            [
                "--env-file",
                str(runtime_root / "dev-build/runtime.env"),
                "--env-file",
                str(runtime_root / "dev-build/images.env"),
                "-f",
                str(db.COMPOSE_FILE),
                "--profile",
                "data",
                "--profile",
                "observability",
                "--profile",
                "smoke",
            ],
            command[2:14],
        )
        self.assertEqual(
            [
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "dcim_bootstrap",
                "-d",
                "synthetic_db",
                "-v",
                "ON_ERROR_STOP=1",
                "-X",
                "-A",
                "-t",
            ],
            command[14:],
        )
        self.assertEqual("result\n", output)
        self.assertEqual("SELECT 1;\n", run.call_args.kwargs["input"])
        self.assertEqual(db.ROOT, run.call_args.kwargs["cwd"])
        self.assertEqual(db.COMMAND_TIMEOUT_SECONDS, run.call_args.kwargs["timeout"])
        self.assertIs(False, run.call_args.kwargs["shell"])
        self.assertEqual(
            "dcim-build",
            run.call_args.kwargs["env"]["COMPOSE_PROJECT_NAME"],
        )

    def test_psql_when_process_fails_returns_clean_typed_error(self) -> None:
        # Given
        completed = subprocess.CompletedProcess([], 17, "", "protected detail")
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                os.environ,
                {"DCIM_RUNTIME_ROOT": directory, "COMPOSE_PROJECT_NAME": "dcim-build"},
                clear=True,
            ),
            patch("scripts.phase2.db.subprocess.run", return_value=completed),
        ):
            # When / Then
            with self.assertRaisesRegex(
                db.DatabaseCommandError,
                "PostgreSQL command failed with exit 17",
            ) as captured:
                db.psql("SELECT 1;")
        self.assertNotIn("protected detail", str(captured.exception))

    def test_psql_when_process_times_out_returns_clean_typed_error(self) -> None:
        # Given
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                os.environ,
                {"DCIM_RUNTIME_ROOT": directory, "COMPOSE_PROJECT_NAME": "dcim-build"},
                clear=True,
            ),
            patch(
                "scripts.phase2.db.subprocess.run",
                side_effect=subprocess.TimeoutExpired(["docker"], 180),
            ),
        ):
            # When / Then
            with self.assertRaisesRegex(db.DatabaseCommandError, "timed out"):
                db.psql("SELECT 1;")


class MigrationSqlTests(unittest.TestCase):
    @staticmethod
    def _verified_schema_rows() -> list[list[dict[str, object]]]:
        return [
            [{"table_name": name} for name in sorted(migrate.EXPECTED_TABLES)],
            [
                {
                    "table_name": "dispositions",
                    "column_name": "execution_sequence",
                    "data_type": "bigint",
                    "is_nullable": "NO",
                },
                {
                    "table_name": "dispositions",
                    "column_name": "input_ordinal",
                    "data_type": "integer",
                    "is_nullable": "NO",
                },
                {
                    "table_name": "run_manifests",
                    "column_name": "last_execution_sequence",
                    "data_type": "bigint",
                    "is_nullable": "NO",
                },
            ],
            [
                {
                    "table_name": "dispositions",
                    "constraint_name": "dispositions_execution_input_unique",
                    "constraint_type": "UNIQUE",
                    "columns": ["run_id", "execution_sequence", "input_ordinal"],
                },
                {
                    "table_name": "dispositions",
                    "constraint_name": "dispositions_execution_sequence_nonnegative",
                    "constraint_type": "CHECK",
                    "columns": [],
                },
                {
                    "table_name": "dispositions",
                    "constraint_name": "dispositions_input_ordinal_nonnegative",
                    "constraint_type": "CHECK",
                    "columns": [],
                },
                {
                    "table_name": "run_manifests",
                    "constraint_name": "run_manifests_execution_sequence_nonnegative",
                    "constraint_type": "CHECK",
                    "columns": [],
                },
            ],
        ]

    def test_verify_when_required_column_is_missing_names_column(self) -> None:
        rows = self._verified_schema_rows()
        rows[1] = rows[1][1:]
        with (
            patch.object(migrate, "query_json", side_effect=rows),
            self.assertRaisesRegex(migrate.MigrationError, "execution_sequence"),
        ):
            migrate.verify()

    def test_verify_when_required_column_type_is_wrong_names_column(self) -> None:
        rows = self._verified_schema_rows()
        rows[1][0]["data_type"] = "integer"
        with (
            patch.object(migrate, "query_json", side_effect=rows),
            self.assertRaisesRegex(migrate.MigrationError, "execution_sequence.*data type"),
        ):
            migrate.verify()

    def test_verify_when_required_column_is_nullable_names_column(self) -> None:
        rows = self._verified_schema_rows()
        rows[1][1]["is_nullable"] = "YES"
        with (
            patch.object(migrate, "query_json", side_effect=rows),
            self.assertRaisesRegex(migrate.MigrationError, "input_ordinal.*NOT NULL"),
        ):
            migrate.verify()

    def test_verify_when_named_constraint_is_missing_names_constraint(self) -> None:
        rows = self._verified_schema_rows()
        rows[2] = rows[2][1:]
        with (
            patch.object(migrate, "query_json", side_effect=rows) as query_json,
            self.assertRaisesRegex(
                migrate.MigrationError, "dispositions_execution_input_unique"
            ),
        ):
            migrate.verify()
        self.assertIn("ORDER BY", query_json.call_args_list[2].args[0])

    def test_migration_id_when_rendered_is_quoted_at_every_sql_boundary(self) -> None:
        # Given
        migration_id = "m0001'; DROP TABLE phase2.events; --"
        expected = literal(migration_id)

        # When
        with (
            patch.object(migrate, "_registry_exists", return_value=True),
            patch.object(migrate, "query_json", return_value=[]) as query_json,
        ):
            self.assertIs(False, migrate._is_applied(migration_id))
        with (
            patch.object(migrate, "MIGRATION_ID", migration_id),
            patch.object(migrate, "_is_applied", side_effect=[False, True]),
            patch.object(migrate, "psql") as apply_psql,
        ):
            self.assertEqual(1, migrate.apply())
        with (
            patch.object(migrate, "MIGRATION_ID", migration_id),
            patch.object(migrate, "_is_applied", return_value=True),
            patch.object(migrate, "psql") as rollback_psql,
        ):
            migrate.rollback(migration_id)

        # Then
        self.assertIn(
            f"WHERE migration_id = {expected};",
            query_json.call_args.args[0],
        )
        self.assertIn(
            f"VALUES ({expected}, CURRENT_TIMESTAMP);",
            apply_psql.call_args.args[0],
        )
        self.assertIn(
            f"WHERE migration_id = {expected};",
            rollback_psql.call_args.args[0],
        )

    def test_up_when_inspected_defines_exact_eight_table_schema(self) -> None:
        # Given / When
        sql = m0001_phase2_core.up()

        # Then
        self.assertEqual(8, sql.count("CREATE TABLE phase2."))
        self.assertIn("content_sha256 text NOT NULL", sql)
        self.assertIn(
            "status text CHECK (status IN ('accepted', 'quarantined', 'duplicate'))",
            sql,
        )
        self.assertIn(
            "owner_type text CHECK (owner_type IN ('asset', 'ci'))",
            sql,
        )
        self.assertIn("PRIMARY KEY (run_id, kind, subject_key)", sql)
        self.assertIn("event_id uuid NULL", sql)
        dispositions = sql.split("CREATE TABLE phase2.dispositions", 1)[1].split(
            "CREATE TABLE phase2.assets", 1
        )[0]
        self.assertNotIn("event_id uuid NULL REFERENCES", dispositions)
        self.assertIn(
            "run_id text NOT NULL REFERENCES phase2.run_manifests(run_id)",
            dispositions,
        )
        self.assertEqual("DROP SCHEMA phase2 CASCADE;\n", m0001_phase2_core.down())

    def test_rollback_when_id_is_unknown_rejects_before_database_access(self) -> None:
        # Given / When / Then
        with (
            patch("scripts.phase2.migrate._is_applied") as is_applied,
            self.assertRaisesRegex(migrate.MigrationError, "unknown migration ID"),
        ):
            migrate.rollback("unknown")
        is_applied.assert_not_called()

if __name__ == "__main__":
    unittest.main()
