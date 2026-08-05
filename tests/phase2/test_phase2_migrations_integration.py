from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import patch

from scripts.phase2 import db, migrate


EXPECTED_COLUMNS = [
    {
        "table_name": "aliases",
        "columns": [
            "alias_id",
            "owner_type",
            "owner_id",
            "type",
            "value",
            "valid_from",
            "valid_to",
            "source",
            "confidence",
        ],
    },
    {
        "table_name": "assets",
        "columns": [
            "asset_id",
            "identity",
            "asset_type",
            "created_at",
            "updated_at",
        ],
    },
    {
        "table_name": "ci_relationships",
        "columns": [
            "relationship_id",
            "from_ci",
            "to_ci",
            "relationship_type",
            "valid_from",
            "valid_to",
            "source",
            "created_at",
        ],
    },
    {
        "table_name": "cis",
        "columns": [
            "ci_id",
            "asset_id",
            "source_system",
            "native_device_id",
            "ci_type",
            "created_at",
            "updated_at",
        ],
    },
    {
        "table_name": "dispositions",
        "columns": [
            "disposition_id",
            "event_id",
            "run_id",
            "status",
            "reason",
            "lineage",
            "decided_at",
            "execution_sequence",
            "input_ordinal",
        ],
    },
    {
        "table_name": "events",
        "columns": [
            "event_id",
            "run_id",
            "envelope",
            "content_sha256",
            "ingested_at",
        ],
    },
    {
        "table_name": "noc_cards",
        "columns": [
            "run_id",
            "kind",
            "subject_key",
            "payload",
            "generated_at",
        ],
    },
    {
        "table_name": "run_manifests",
        "columns": [
            "run_id",
            "fixed_clock",
            "source_count",
            "manifest_sha256",
            "created_at",
            "last_execution_sequence",
        ],
    },
    {
        "table_name": "schema_migrations",
        "columns": ["migration_id", "applied_at"],
    },
    {
        "table_name": "workflow_drafts",
        "columns": ["draft_id", "created_at", "event_id", "draft_type", "payload", "status", "audit"],
    },
]

EMPTY_BUSINESS_ROWS = {
    "run_manifests": 0,
    "events": 0,
    "dispositions": 0,
    "assets": 0,
    "cis": 0,
    "aliases": 0,
    "noc_cards": 0,
}


def business_row_counts() -> list[dict[str, object]]:
    return db.query_json(
        """
SELECT json_build_object(
    'run_manifests', (SELECT count(*) FROM phase2.run_manifests),
    'events', (SELECT count(*) FROM phase2.events),
    'dispositions', (SELECT count(*) FROM phase2.dispositions),
    'assets', (SELECT count(*) FROM phase2.assets),
    'cis', (SELECT count(*) FROM phase2.cis),
    'aliases', (SELECT count(*) FROM phase2.aliases),
    'noc_cards', (SELECT count(*) FROM phase2.noc_cards)
)::text;
"""
    )


def migration_registry() -> list[dict[str, object]]:
    exists = db.query_json(
        """
SELECT json_build_object(
    'exists', to_regclass('phase2.schema_migrations') IS NOT NULL
)::text;
"""
    )
    if exists == [{"exists": False}]:
        return []
    return db.query_json(
        """
SELECT json_build_object(
    'migration_id', migration_id,
    'applied_at', applied_at
)::text
FROM phase2.schema_migrations
ORDER BY migration_id;
"""
    )


class PostgreSqlMigrationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        state_home = os.environ.get("XDG_STATE_HOME")
        default_root = (
            Path(state_home) if state_home else Path.home() / ".local/state"
        ) / "dcim-core-platform/runtime"
        os.environ.setdefault("DCIM_RUNTIME_ROOT", str(default_root))
        os.environ.setdefault("COMPOSE_PROJECT_NAME", "dcim-build")
        try:
            db.query_json("SELECT json_build_object('ready', true)::text;")
        except db.DatabaseCommandError as error:
            raise unittest.SkipTest(f"Compose PostgreSQL unavailable: {error}") from error
        migrate.apply(default_root / "dev-build/secrets")

    def test_apply_when_repeated_reports_zero_and_exact_inventory(self) -> None:
        # Given / When
        applied = migrate.apply(Path(os.environ["DCIM_RUNTIME_ROOT"]) / "dev-build/secrets")
        inventory = migrate.verify()

        # Then
        self.assertEqual(0, applied)
        self.assertEqual(migrate.EXPECTED_TABLES, inventory)

    def test_fresh_apply_when_schema_is_empty_applies_four_then_none(self) -> None:
        # Given
        if business_row_counts() != [EMPTY_BUSINESS_ROWS]:
            self.skipTest("shared Phase 2 data exists; destructive fresh apply not safe")
        migrate.rollback(migrate.MIGRATION_ID)

        # When
        secrets = Path(os.environ["DCIM_RUNTIME_ROOT"]) / "dev-build/secrets"
        first_applied = migrate.apply(secrets)
        second_applied = migrate.apply(secrets)

        # Then
        self.assertEqual(4, first_applied)
        self.assertEqual(0, second_applied)
        self.assertEqual(migrate.EXPECTED_TABLES, migrate.verify())

    def test_apply_cli_when_database_command_fails_preserves_registry(self) -> None:
        # Given
        before = migration_registry()
        stderr = StringIO()
        dropped_connection = db.DatabaseCommandError(
            "PostgreSQL command failed with exit 1"
        )

        # When
        with (
            patch.object(sys, "argv", ["migrate.py", "apply"]),
            patch.object(migrate, "query_json", side_effect=dropped_connection),
            redirect_stderr(stderr),
        ):
            exit_code = migrate.main()

        # Then
        self.assertEqual(1, exit_code)
        self.assertIn("phase2 migration failed:", stderr.getvalue())
        self.assertEqual(before, migration_registry())

    def test_apply_cli_when_transaction_fails_records_no_migration(self) -> None:
        # Given
        if business_row_counts() != [EMPTY_BUSINESS_ROWS]:
            self.skipTest("shared Phase 2 data exists; destructive fresh apply not safe")
        migrate.rollback(migrate.MIGRATION_ID)
        before = migration_registry()
        stderr = StringIO()
        dropped_connection = db.DatabaseCommandError(
            "PostgreSQL command failed with exit 1"
        )

        try:
            # When
            with (
                patch.object(sys, "argv", ["migrate.py", "apply"]),
                patch.object(migrate, "psql", side_effect=dropped_connection),
                redirect_stderr(stderr),
            ):
                exit_code = migrate.main()

            # Then
            self.assertEqual(1, exit_code)
            self.assertIn("phase2 migration failed:", stderr.getvalue())
            self.assertEqual(before, migration_registry())
        finally:
            self.assertEqual(4, migrate.apply(Path(os.environ["DCIM_RUNTIME_ROOT"]) / "dev-build/secrets"))
            self.assertEqual(migrate.EXPECTED_TABLES, migrate.verify())

    def test_verify_when_schema_is_fully_migrated_passes(self) -> None:
        # Given / When
        inventory = migrate.verify()

        # Then
        self.assertEqual(migrate.EXPECTED_TABLES, inventory)

    def test_schema_when_introspected_has_exact_columns(self) -> None:
        # Given / When
        rows = db.query_json(
            """
SELECT json_build_object(
    'table_name', table_name,
    'columns', json_agg(column_name ORDER BY ordinal_position)
)::text
FROM information_schema.columns
WHERE table_schema = 'phase2'
GROUP BY table_name
ORDER BY table_name;
"""
        )

        # Then
        self.assertEqual(EXPECTED_COLUMNS, rows)

    def test_schema_when_introspected_has_only_expected_foreign_keys(self) -> None:
        # Given / When
        rows = db.query_json(
            """
SELECT json_build_object(
    'table_name', source.table_name,
    'column_name', source.column_name,
    'foreign_table', target.table_name,
    'foreign_column', target.column_name
)::text
FROM information_schema.referential_constraints reference
JOIN information_schema.key_column_usage source
  ON source.constraint_schema = reference.constraint_schema
 AND source.constraint_name = reference.constraint_name
JOIN information_schema.constraint_column_usage target
  ON target.constraint_schema = reference.unique_constraint_schema
 AND target.constraint_name = reference.unique_constraint_name
WHERE source.table_schema = 'phase2'
ORDER BY source.table_name, source.column_name;
"""
        )

        # Then
        self.assertEqual(
            [
                {
                    "table_name": "ci_relationships",
                    "column_name": "from_ci",
                    "foreign_table": "cis",
                    "foreign_column": "ci_id",
                },
                {
                    "table_name": "ci_relationships",
                    "column_name": "to_ci",
                    "foreign_table": "cis",
                    "foreign_column": "ci_id",
                },
                {
                    "table_name": "cis",
                    "column_name": "asset_id",
                    "foreign_table": "assets",
                    "foreign_column": "asset_id",
                },
                {
                    "table_name": "dispositions",
                    "column_name": "run_id",
                    "foreign_table": "run_manifests",
                    "foreign_column": "run_id",
                },
                {
                    "table_name": "events",
                    "column_name": "run_id",
                    "foreign_table": "run_manifests",
                    "foreign_column": "run_id",
                },
                {
                    "table_name": "noc_cards",
                    "column_name": "run_id",
                    "foreign_table": "run_manifests",
                    "foreign_column": "run_id",
                },
                {
                    "table_name": "workflow_drafts",
                    "column_name": "event_id",
                    "foreign_table": "events",
                    "foreign_column": "event_id",
                },
            ],
            rows,
        )

    def test_schema_when_introspected_has_nullable_disposition_event_id(self) -> None:
        # Given / When
        rows = db.query_json(
            """
SELECT json_build_object('nullable', is_nullable)::text
FROM information_schema.columns
WHERE table_schema = 'phase2'
  AND table_name = 'dispositions'
  AND column_name = 'event_id';
"""
        )

        # Then
        self.assertEqual([{"nullable": "YES"}], rows)

    def test_schema_when_introspected_has_exact_check_constraints(self) -> None:
        # Given / When
        rows = db.query_json(
            """
SELECT json_build_object(
    'table_name', relation.relname,
    'definition', replace(pg_get_constraintdef(item.oid), '::text', '')
)::text
FROM pg_constraint item
JOIN pg_class relation ON relation.oid = item.conrelid
JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace
WHERE namespace.nspname = 'phase2'
  AND item.contype = 'c'
ORDER BY relation.relname, item.conname;
"""
        )

        # Then
        self.assertEqual(
            [
                {
                    "table_name": "aliases",
                    "definition": (
                        "CHECK ((owner_type = ANY "
                        "(ARRAY['asset', 'ci'])))"
                    ),
                },
                {
                    "table_name": "ci_relationships",
                    "definition": "CHECK ((relationship_type = ANY (ARRAY['depends_on', 'runs_on', 'connected_to', 'contains', 'hosted_on', 'part_of', 'monitors'])))",
                },
                {
                    "table_name": "dispositions",
                    "definition": "CHECK ((execution_sequence >= 0))",
                },
                {
                    "table_name": "dispositions",
                    "definition": "CHECK ((input_ordinal >= 0))",
                },
                {
                    "table_name": "dispositions",
                    "definition": (
                        "CHECK ((status = ANY (ARRAY['accepted', "
                        "'quarantined', 'duplicate'])))"
                    ),
                },
                {
                    "table_name": "run_manifests",
                    "definition": "CHECK ((last_execution_sequence >= 0))",
                },
                {
                    "table_name": "workflow_drafts",
                    "definition": "CHECK ((draft_type = ANY (ARRAY['notification', 'ticket_draft', 'approval_request'])))",
                },
                {
                    "table_name": "workflow_drafts",
                    "definition": "CHECK ((status = ANY (ARRAY['draft', 'simulated_approved', 'simulated_rejected'])))",
                },
            ],
            rows,
        )

    def test_transaction_when_statement_fails_leaves_no_partial_table(self) -> None:
        # Given / When
        with self.assertRaises(db.DatabaseCommandError):
            db.psql(
                """
BEGIN;
CREATE TABLE phase2.transaction_probe (value int);
SELECT missing_column FROM phase2.transaction_probe;
COMMIT;
"""
            )
        rows = db.query_json(
            """
SELECT json_build_object(
    'exists', to_regclass('phase2.transaction_probe') IS NOT NULL
)::text;
"""
        )

        # Then
        self.assertEqual([{"exists": False}], rows)
