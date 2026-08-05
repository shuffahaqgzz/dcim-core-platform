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

import argparse
from dataclasses import dataclass
import inspect
from pathlib import Path
import sys
from typing import Callable, Mapping, assert_never, Final, override


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
    m0003_ci_relationships,
)
from scripts.foundation_bootstrap import SECRET_NAMES  # noqa: E402


EXPECTED_TABLES: Final = (
    "schema_migrations",
    "run_manifests",
    "events",
    "dispositions",
    "assets",
    "cis",
    "aliases",
    "noc_cards",
    "ci_relationships",
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
LATEST_MIGRATION_ID: Final = m0003_ci_relationships.MIGRATION_ID
PREVIOUS_MIGRATION_ID: Final = m0002_execution_reconciliation.MIGRATION_ID
ROLE_PASSWORD_FILES: Final = {
    "dcim_assets_rw": "assets-db-password",
    "dcim_cmdb_rw": "cmdb-db-password",
    "dcim_api_ro": "api-db-password",
    "dcim_analytics_ro": "analytics-db-password",
    "dcim_workflow_rw": "workflow-db-password",
}


@dataclass(frozen=True, slots=True)
class MigrationError(RuntimeError):
    """A migration command violated the fixed migration contract."""

    reason: str

    @override
    def __str__(self) -> str:
        return self.reason

def redact(text: str, secrets: tuple[str, ...]) -> str:
    """Remove credential values from text that can reach the terminal."""
    for secret in secrets:
        text = text.replace(secret, "***")
    return text


def role_password_context(directory: Path) -> dict[str, dict[str, str]]:
    """Read the bootstrap role passwords after validating its complete inventory."""
    try:
        entries = tuple(directory.iterdir())
    except OSError as error:
        raise MigrationError("role-password directory is unavailable") from error
    for entry in entries:
        if entry.name not in SECRET_NAMES or entry.is_symlink() or not entry.is_file():
            raise MigrationError("role-password directory contains an invalid entry")
    try:
        values = {
            role: (directory / filename).read_text(encoding="utf-8").strip()
            for role, filename in ROLE_PASSWORD_FILES.items()
        }
    except FileNotFoundError as error:
        raise MigrationError("required role password file is missing") from error
    except OSError as error:
        raise MigrationError("required role password file is unavailable") from error
    if not all(values.values()):
        raise MigrationError("required role password file is empty")
    return {"role_passwords": values}


MigrationUp = Callable[..., str]


def _migration_sql(migration: MigrationUp, context: dict[str, dict[str, str]] | None) -> str:
    if not inspect.signature(migration).parameters:
        return migration()
    if context is None:
        raise MigrationError("--role-password-dir is required for credential-aware migrations")
    return migration(context)


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


def apply(role_password_dir: Path | None = None) -> int:
    """Apply every unrecorded migration transactionally."""
    applied = 0
    context = role_password_context(role_password_dir) if role_password_dir else None
    migrations = (
        (MIGRATION_ID, m0001_phase2_core.up),
        (PREVIOUS_MIGRATION_ID, m0002_execution_reconciliation.up),
    )
    for migration_id, migration_up in migrations:
        if _is_applied(migration_id):
            continue
        migration = literal(migration_id)
        sql = (
            f"BEGIN;\n{_migration_sql(migration_up, context)}"
            "INSERT INTO phase2.schema_migrations (migration_id, applied_at)\n"
            f"VALUES ({migration}, CURRENT_TIMESTAMP);\nCOMMIT;\n"
        )
        _ = psql(sql)
        applied += 1
    if role_password_dir is not None and not _is_applied(LATEST_MIGRATION_ID):
        migration = literal(LATEST_MIGRATION_ID)
        sql = (
            f"BEGIN;\n{_migration_sql(m0003_ci_relationships.up, context)}"
            "INSERT INTO phase2.schema_migrations (migration_id, applied_at)\n"
            f"VALUES ({migration}, CURRENT_TIMESTAMP);\nCOMMIT;\n"
        )
        _ = psql(sql)
        applied += 1
    return applied


def rollback(migration_id: str) -> None:
    """Delete one known record and run its down migration atomically."""
    down_migrations = {
        MIGRATION_ID: m0001_phase2_core.down,
        PREVIOUS_MIGRATION_ID: m0002_execution_reconciliation.down,
        LATEST_MIGRATION_ID: m0003_ci_relationships.down,
    }
    if migration_id not in down_migrations:
        raise MigrationError("unknown migration ID")
    if not _is_applied(migration_id):
        raise MigrationError("migration is not applied")
    migration_down = down_migrations[migration_id]
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
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?")
    parser.add_argument("migration_id", nargs="?")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--role-password-dir", type=Path)
    arguments = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if arguments.verify:
        for table_name in verify():
            print(table_name)
        return 0
    if arguments.command == "apply" and arguments.migration_id is None:
        print(f"{apply(arguments.role_password_dir)} applied")
        return 0
    if arguments.command == "rollback" and arguments.migration_id is not None:
        migration_id = arguments.migration_id
        rollback(migration_id)
        print(f"rolled back {migration_id}")
        return 0
    raise MigrationError("expected apply [--role-password-dir PATH], rollback <migration_id>, or --verify")


def main() -> int:
    """Translate expected migration failures into a clean nonzero result."""
    secrets: tuple[str, ...] = ()
    try:
        arguments = sys.argv[1:]
        if "--role-password-dir" in arguments:
            index = arguments.index("--role-password-dir")
            if index + 1 < len(arguments):
                secrets = tuple(
                    role_password_context(Path(arguments[index + 1]))["role_passwords"].values()
                )
        return run()
    except (DatabaseCommandError, JsonExtractionError, MigrationError) as error:
        print(f"phase2 migration failed: {redact(str(error), secrets)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
