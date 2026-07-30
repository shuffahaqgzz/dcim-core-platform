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
    psql,
    query_json,
)
from scripts.phase2.migrations import m0001_phase2_core  # noqa: E402


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
MIGRATION_ID: Final = m0001_phase2_core.MIGRATION_ID


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


def _is_applied() -> bool:
    if not _registry_exists():
        return False
    rows = query_json(
        """
SELECT json_build_object('migration_id', migration_id)::text
FROM phase2.schema_migrations
WHERE migration_id = 'm0001_phase2_core';
"""
    )
    if not rows:
        return False
    if len(rows) != 1 or rows[0].get("migration_id") != MIGRATION_ID:
        raise MigrationError("migration registry returned an invalid row")
    return True


def apply() -> int:
    """Apply every unrecorded migration transactionally."""
    if _is_applied():
        return 0
    sql = (
        f"BEGIN;\n{m0001_phase2_core.up()}"
        "INSERT INTO phase2.schema_migrations (migration_id, applied_at)\n"
        f"VALUES ('{MIGRATION_ID}', CURRENT_TIMESTAMP);\nCOMMIT;\n"
    )
    _ = psql(sql)
    return 1


def rollback(migration_id: str) -> None:
    """Delete one known record and run its down migration atomically."""
    if migration_id != MIGRATION_ID:
        raise MigrationError("unknown migration ID")
    if not _is_applied():
        raise MigrationError("migration is not applied")
    sql = (
        "BEGIN;\nDELETE FROM phase2.schema_migrations\n"
        f"WHERE migration_id = '{MIGRATION_ID}';\n"
        f"{m0001_phase2_core.down()}COMMIT;\n"
    )
    _ = psql(sql)


def verify() -> tuple[str, ...]:
    """Assert and return the exact Phase 2 table inventory."""
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
