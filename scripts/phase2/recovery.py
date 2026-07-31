#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

# ─── How to run ───
# 1. Set DCIM_RUNTIME_ROOT to the protected synthetic Compose runtime.
# 2. Start the synthetic foundation PostgreSQL service.
# 3. Run: python3 scripts/phase2/recovery.py
# ──────────────────
"""Verify a non-destructive Phase 2 PostgreSQL dump and temporary restore."""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import re
import stat
import sys
import time
from types import TracebackType
from typing import Final, Literal, override


ROOT: Final = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase2 import db  # noqa: E402
from scripts.protected_runtime import (  # noqa: E402
    ensure_protected_directory,
    external_runtime_root,
    write_protected_text,
)


RECOVERY_DATABASE: Final = "dcim_phase2_recovery_check"
DUMP_PARTS: Final = ("dev-build", "phase2-recovery", "phase2.sql")
LOCK_NAME: Final = "recovery.lock"
LOCK_TIMEOUT_SECONDS: Final = 30.0
LOCK_RETRY_SECONDS: Final = 0.05
TABLE_NAME: Final = re.compile(r"[a-z_][a-z0-9_]*\Z")


@dataclass(frozen=True, slots=True)
class RecoveryError(RuntimeError):
    """The dump/restore result violated the recovery contract."""

    reason: str

    @override
    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class TableDigest:
    """One table's ordered logical checksum and row count."""

    row_count: int
    checksum: str


@dataclass(frozen=True, slots=True)
class _RecoveryLock:
    descriptor: int

    def __enter__(self) -> None:
        return None

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        fcntl.flock(self.descriptor, fcntl.LOCK_UN)
        os.close(self.descriptor)
        return False


def _recovery_lock(runtime_root: Path) -> _RecoveryLock:
    directory = ensure_protected_directory(runtime_root, *DUMP_PARTS[:-1])
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(directory / LOCK_NAME, flags, 0o600)
    except OSError as error:
        raise RecoveryError("Phase 2 recovery lock could not be opened") from error
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
        ):
            raise RecoveryError("Phase 2 recovery lock is not owner-controlled")
        os.fchmod(descriptor, 0o600)
    except OSError as error:
        os.close(descriptor)
        raise RecoveryError("Phase 2 recovery lock could not be initialized") from error
    except RecoveryError:
        os.close(descriptor)
        raise
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    while True:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return _RecoveryLock(descriptor)
        except BlockingIOError:
            if time.monotonic() >= deadline:
                os.close(descriptor)
                raise RecoveryError("Phase 2 recovery lock timed out") from None
            time.sleep(LOCK_RETRY_SECONDS)
        except OSError as error:
            os.close(descriptor)
            raise RecoveryError("Phase 2 recovery lock could not be acquired") from error


def _runtime_root() -> Path:
    raw = os.environ.get("DCIM_RUNTIME_ROOT")
    if not raw:
        raise RecoveryError("DCIM_RUNTIME_ROOT is required")
    try:
        return external_runtime_root(Path(raw))
    except ValueError as error:
        raise RecoveryError(str(error)) from error


def dump_phase2() -> str:
    dump = db.pg_dump(schema="phase2", database=db.DEFAULT_DATABASE)
    if not dump:
        raise RecoveryError("Phase 2 pg_dump returned an empty dump")
    return dump


def _table_inventory(database: str) -> tuple[str, ...]:
    rows = db.query_json(
        """
SELECT json_build_object('table_name', table_name)::text
FROM information_schema.tables
WHERE table_schema = 'phase2'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
""",
        database,
    )
    names: list[str] = []
    for row in rows:
        name = row.get("table_name")
        if not isinstance(name, str) or not TABLE_NAME.fullmatch(name):
            raise RecoveryError("Phase 2 table inventory returned an invalid name")
        names.append(name)
    if not names:
        raise RecoveryError("Phase 2 table inventory is empty")
    return tuple(names)


def _table_digest(database: str, table_name: str) -> TableDigest:
    if not TABLE_NAME.fullmatch(table_name):
        raise RecoveryError("Phase 2 checksum received an invalid table name")
    rows = db.query_json(
        f"""
SELECT json_build_object(
    'row_count', count(*),
    'checksum', md5(coalesce(string_agg(
        row_to_json(item)::text, E'\\n' ORDER BY row_to_json(item)::text
    ), ''))
)::text
FROM phase2."{table_name}" AS item;
""",
        database,
    )
    if len(rows) != 1:
        raise RecoveryError(f"{table_name}: checksum returned unexpected rows")
    row_count = rows[0].get("row_count")
    checksum = rows[0].get("checksum")
    if (
        isinstance(row_count, bool)
        or not isinstance(row_count, int)
        or not isinstance(checksum, str)
        or not re.fullmatch(r"[0-9a-f]{32}", checksum)
    ):
        raise RecoveryError(f"{table_name}: checksum returned invalid values")
    return TableDigest(row_count=row_count, checksum=checksum)


def _snapshot(database: str, tables: tuple[str, ...]) -> dict[str, TableDigest]:
    return {table: _table_digest(database, table) for table in tables}


def _temporary_database_exists() -> bool:
    rows = db.query_json(
        f"""
SELECT json_build_object(
    'exists', EXISTS (
        SELECT 1 FROM pg_database WHERE datname = '{RECOVERY_DATABASE}'
    )
)::text;
""",
        "postgres",
    )
    if rows == [{"exists": False}]:
        return False
    if rows == [{"exists": True}]:
        return True
    raise RecoveryError("temporary database absence check returned invalid values")


def _raise_with_cleanup(original: Exception | None, cleanup: Exception) -> None:
    if original is None:
        raise RecoveryError(f"temporary database cleanup failed: {cleanup}") from cleanup
    raise RecoveryError(
        f"recovery failed: {original}; temporary database cleanup failed: {cleanup}"
    ) from cleanup


def verify_recovery() -> tuple[str, ...]:
    """Restore Phase 2 into one fixed temporary database and compare every table."""
    drop_sql = f'DROP DATABASE IF EXISTS "{RECOVERY_DATABASE}";'
    root = _runtime_root()
    with _recovery_lock(root):
        original_error: Exception | None = None
        try:
            _ = db.psql(drop_sql, "postgres")
            tables = _table_inventory(db.DEFAULT_DATABASE)
            live_before = _snapshot(db.DEFAULT_DATABASE, tables)
            live_business_rows = sum(
                digest.row_count
                for table, digest in live_before.items()
                if table != "schema_migrations"
            )
            if live_business_rows == 0:
                raise RecoveryError(
                    "Phase 2 recovery is unverifiable: total live row count is zero"
                )
            dump = dump_phase2()
            dump_path = write_protected_text(root, DUMP_PARTS, dump)
            _ = db.psql(f'CREATE DATABASE "{RECOVERY_DATABASE}";', "postgres")
            try:
                restore_sql = dump_path.read_text(encoding="utf-8")
            except OSError as error:
                raise RecoveryError("protected Phase 2 dump could not be read") from error
            _ = db.psql(restore_sql, RECOVERY_DATABASE)
            restored_tables = _table_inventory(RECOVERY_DATABASE)
            if restored_tables != tables:
                raise RecoveryError("restored Phase 2 table inventory mismatch")
            restored = _snapshot(RECOVERY_DATABASE, tables)
            live_after = _snapshot(db.DEFAULT_DATABASE, tables)
            for table in tables:
                if live_before[table] != restored[table]:
                    expected = live_before[table]
                    actual = restored[table]
                    raise RecoveryError(
                        f"{table}: restored checksum or row count mismatch "
                        f"(expected rows={expected.row_count}, actual rows={actual.row_count})"
                    )
                if live_before[table] != live_after[table]:
                    raise RecoveryError(f"{table}: live table changed during recovery")
        except Exception as error:
            original_error = error
            raise
        finally:
            try:
                _ = db.psql(drop_sql, "postgres")
                if _temporary_database_exists():
                    raise RecoveryError("temporary database still exists after drop")
            except (db.DatabaseCommandError, db.JsonExtractionError, RecoveryError) as cleanup_error:
                _raise_with_cleanup(original_error, cleanup_error)

    for table in tables:
        digest = live_before[table]
        message = (
            f"phase2-recovery: {table} rows={digest.row_count}"
            f" checksum={digest.checksum} PASS"
        )
        print(message)
    print("phase2-recovery: live-schema-unchanged PASS")
    print("phase2-recovery: temporary-database-dropped PASS")
    print("phase2-recovery: PASS")
    return tables


def main() -> int:
    """Translate expected recovery failures into a clean nonzero result."""
    try:
        _ = verify_recovery()
    except (db.DatabaseCommandError, db.JsonExtractionError, RecoveryError) as error:
        print(f"phase2-recovery: FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
