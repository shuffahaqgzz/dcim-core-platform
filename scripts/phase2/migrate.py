#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly:
#      uv run scripts/phase2/migrate.py apply
# 3. Or use the repository Python:
#      python3 scripts/phase2/migrate.py apply
# ──────────────────
"""Apply, roll back, and verify Python-owned Phase 2 migrations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import assert_never, Final, override


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase2.db import (  # noqa: E402
    DatabaseCommandError,
    JsonExtractionError,
    literal,
    psql,
    query_json,
)
from scripts.phase2.migrations import (  # noqa: E402
    m0001_phase2_core,
    m0002_execution_reconciliation,
)


EXPECTED_TABLES: Final = (
    "schema_migrations",
    "run_manifests",
    "events",
    "dispositions",
    "assets",
    "cis",
    "aliases",
    "noc_cards",
)
EXPECTED_M0002_COLUMNS: Final = (
    ("dispositions", "execution_sequence", "bigint", "NO"),
    ("dispositions", "input_ordinal", "integer", "NO"),
    ("run_manifests", "last_execution_sequence", "bigint", "NO"),
)
EXPECTED_M0002_CONSTRAINTS: Final = (
    (
        "dispositions",
        "dispositions_execution_input_unique",
        "UNIQUE",
        ("run_id", "execution_sequence", "input_ordinal"),
    ),
    (
        "dispositions",
        "dispositions_execution_sequence_nonnegative",
        "CHECK",
        (),
    ),
    ("dispositions", "dispositions_input_ordinal_nonnegative", "CHECK", ()),
    (
        "run_manifests",
        "run_manifests_execution_sequence_nonnegative",
        "CHECK",
        (),
    ),
)
MIGRATION_ID: Final = m0001_phase2_core.MIGRATION_ID
LATEST_MIGRATION_ID: Final = m0002_execution_reconciliation.MIGRATION_ID


@dataclass(frozen=True, slots=True)
class MigrationError(RuntimeError):
    """A migration command violated the fixed migration contract."""

    reason: str

    @override
    def __str__(self) -> str:
        return self.reason


def _registry_exists() -> bool:
    rows = query_json(
        """
SELECT json_build_object(
    'exists', to_regclass('phase2.schema_migrations') IS NOT NULL
)::text;
"""
    )
    if len(rows) != 1:
        raise MigrationError("migration registry probe returned unexpected rows")
    match rows[0].get("exists"):
        case bool() as exists:
            return exists
        case str() | int() | float() | None | list() | dict():
            raise MigrationError("migration registry probe returned an invalid row")
        case unreachable:
            assert_never(unreachable)


def _is_applied(migration_id: str) -> bool:
    if not _registry_exists():
        return False
    migration = literal(migration_id)
    rows = query_json(
        f"""
SELECT json_build_object('migration_id', migration_id)::text
FROM phase2.schema_migrations
WHERE migration_id = {migration};
"""
    )
    if not rows:
        return False
    if len(rows) != 1 or rows[0].get("migration_id") != migration_id:
        raise MigrationError("migration registry returned an invalid row")
    return True


def apply() -> int:
    """Apply every unrecorded migration transactionally."""
    applied = 0
    migrations = (
        (MIGRATION_ID, m0001_phase2_core.up),
        (LATEST_MIGRATION_ID, m0002_execution_reconciliation.up),
    )
    for migration_id, migration_up in migrations:
        if _is_applied(migration_id):
            continue
        migration = literal(migration_id)
        sql = (
            f"BEGIN;\n{migration_up()}"
            "INSERT INTO phase2.schema_migrations (migration_id, applied_at)\n"
            f"VALUES ({migration}, CURRENT_TIMESTAMP);\nCOMMIT;\n"
        )
        _ = psql(sql)
        applied += 1
    return applied


def rollback(migration_id: str) -> None:
    """Delete one known record and run its down migration atomically."""
    if migration_id not in (MIGRATION_ID, LATEST_MIGRATION_ID):
        raise MigrationError("unknown migration ID")
    if not _is_applied(migration_id):
        raise MigrationError("migration is not applied")
    migration_down = (
        m0001_phase2_core.down
        if migration_id == MIGRATION_ID
        else m0002_execution_reconciliation.down
    )
    migration = literal(migration_id)
    sql = (
        "BEGIN;\nDELETE FROM phase2.schema_migrations\n"
        f"WHERE migration_id = {migration};\n"
        f"{migration_down()}COMMIT;\n"
    )
    _ = psql(sql)


def verify() -> tuple[str, ...]:
    """Assert the Phase 2 schema contract and return its table inventory."""
    rows = query_json(
        """
SELECT json_build_object('table_name', table_name)::text
FROM information_schema.tables
WHERE table_schema = 'phase2'
ORDER BY table_name;
"""
    )
    names: list[str] = []
    for row in rows:
        match row.get("table_name"):
            case str() as name:
                names.append(name)
            case int() | float() | None | list() | dict():
                raise MigrationError("table inventory returned an invalid row")
            case unreachable:
                assert_never(unreachable)
    actual = tuple(sorted(names))
    expected = tuple(sorted(EXPECTED_TABLES))
    if actual != expected:
        raise MigrationError("Phase 2 table inventory mismatch")

    column_names = ", ".join(
        literal(column_name) for _, column_name, _, _ in EXPECTED_M0002_COLUMNS
    )
    column_rows = query_json(
        f"""
SELECT json_build_object(
    'table_name', table_name,
    'column_name', column_name,
    'data_type', data_type,
    'is_nullable', is_nullable
)::text
FROM information_schema.columns
WHERE table_schema = 'phase2'
  AND column_name IN ({column_names})
ORDER BY table_name, column_name;
"""
    )
    columns_by_name = {
        (row.get("table_name"), row.get("column_name")): row for row in column_rows
    }
    for table_name, column_name, data_type, is_nullable in EXPECTED_M0002_COLUMNS:
        row = columns_by_name.get((table_name, column_name))
        qualified_name = f"phase2.{table_name}.{column_name}"
        if row is None:
            raise MigrationError(f"required column {qualified_name} is missing")
        if row.get("data_type") != data_type:
            raise MigrationError(
                f"required column {qualified_name} has wrong data type; "
                f"expected {data_type}"
            )
        if row.get("is_nullable") != is_nullable:
            raise MigrationError(f"required column {qualified_name} must be NOT NULL")

    constraint_names = ", ".join(
        literal(constraint_name)
        for _, constraint_name, _, _ in EXPECTED_M0002_CONSTRAINTS
    )
    constraint_rows = query_json(
        f"""
SELECT json_build_object(
    'table_name', constraint_item.table_name,
    'constraint_name', constraint_item.constraint_name,
    'constraint_type', constraint_item.constraint_type,
    'columns', COALESCE(
        json_agg(column_item.column_name ORDER BY column_item.ordinal_position)
            FILTER (WHERE column_item.column_name IS NOT NULL),
        '[]'::json
    )
)::text
FROM information_schema.table_constraints AS constraint_item
LEFT JOIN information_schema.key_column_usage AS column_item
  ON column_item.constraint_schema = constraint_item.constraint_schema
 AND column_item.constraint_name = constraint_item.constraint_name
 AND column_item.table_schema = constraint_item.table_schema
 AND column_item.table_name = constraint_item.table_name
WHERE constraint_item.table_schema = 'phase2'
  AND constraint_item.constraint_name IN ({constraint_names})
GROUP BY constraint_item.table_name, constraint_item.constraint_name,
    constraint_item.constraint_type
ORDER BY constraint_item.table_name, constraint_item.constraint_name;
"""
    )
    constraints_by_name = {
        (row.get("table_name"), row.get("constraint_name")): row
        for row in constraint_rows
    }
    for table_name, constraint_name, constraint_type, columns in (
        EXPECTED_M0002_CONSTRAINTS
    ):
        row = constraints_by_name.get((table_name, constraint_name))
        if row is None:
            raise MigrationError(f"required constraint {constraint_name} is missing")
        if row.get("constraint_type") != constraint_type:
            raise MigrationError(
                f"required constraint {constraint_name} has wrong type; "
                f"expected {constraint_type}"
            )
        if row.get("columns") != list(columns):
            raise MigrationError(
                f"required constraint {constraint_name} covers wrong columns; "
                f"expected {', '.join(columns)}"
            )
    return EXPECTED_TABLES


def run(argv: list[str] | None = None) -> int:
    """Run one migration CLI command."""
    arguments = sys.argv[1:] if argv is None else argv
    if arguments == ["--verify"]:
        for table_name in verify():
            print(table_name)
        return 0
    if arguments == ["apply"]:
        print(f"{apply()} applied")
        return 0
    if len(arguments) == 2 and arguments[0] == "rollback":
        migration_id = arguments[1]
        rollback(migration_id)
        print(f"rolled back {migration_id}")
        return 0
    raise MigrationError("expected apply, rollback <migration_id>, or --verify")


def main() -> int:
    """Translate expected migration failures into a clean nonzero result."""
    try:
        return run()
    except (DatabaseCommandError, JsonExtractionError, MigrationError) as error:
        print(f"phase2 migration failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
