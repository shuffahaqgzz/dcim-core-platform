from __future__ import annotations

import os
from pathlib import Path
import unittest

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
]


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
        migrate.apply()

    def test_apply_when_repeated_reports_zero_and_exact_inventory(self) -> None:
        # Given / When
        applied = migrate.apply()
        inventory = migrate.verify()

        # Then
        self.assertEqual(0, applied)
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
