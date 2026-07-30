"""Shared protected Compose/PostgreSQL access for Phase 2 tooling."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
from typing import assert_never, Final, Never, override, TypeAlias

from scripts.protected_runtime import (
    external_runtime_root,
    protected_runtime_path,
    validate_compose_project_name,
)


JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

ROOT: Final = Path(__file__).resolve().parents[2]
COMPOSE_FILE: Final = ROOT / "deploy/compose/dev-build/compose.yaml"
ACCEPTANCE_OVERRIDE_NAME: Final = "acceptance-compose.override.yaml"
PROFILES: Final = ("data", "observability", "smoke")
DEFAULT_DATABASE: Final = "dcim_foundation"
COMMAND_TIMEOUT_SECONDS: Final = 180


@dataclass(frozen=True, slots=True)
class DatabaseCommandError(RuntimeError):
    """A bounded database command failed without exposing protected output."""

    reason: str

    @override
    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class JsonExtractionError(ValueError):
    """One psql extraction line violated the JSON-object protocol."""

    line_number: int
    reason: str

    @override
    def __str__(self) -> str:
        return f"JSON extraction line {self.line_number}: {self.reason}"


class _NonFiniteJsonError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class _DuplicateJsonKeyError(ValueError):
    key: str


def _reject_nonfinite_json(_value: str) -> Never:
    raise _NonFiniteJsonError


def _unique_json_object(pairs: list[tuple[str, JsonValue]]) -> JsonObject:
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(key)
        result[key] = value
    return result


def _runtime_root() -> Path:
    raw = os.environ.get("DCIM_RUNTIME_ROOT")
    if not raw:
        raise DatabaseCommandError("DCIM_RUNTIME_ROOT is required")
    try:
        return external_runtime_root(Path(raw))
    except ValueError as error:
        raise DatabaseCommandError(str(error)) from error


def _compose_project_name() -> str:
    value = os.environ.get("COMPOSE_PROJECT_NAME", "dcim-build")
    try:
        return validate_compose_project_name(value)
    except ValueError as error:
        raise DatabaseCommandError(str(error)) from error


def _compose_override_path(root: Path, project: str) -> Path | None:
    raw = os.environ.get("DCIM_COMPOSE_OVERRIDE")
    if project == "dcim-build":
        if raw:
            raise DatabaseCommandError(
                "Compose override is prohibited for normal lifecycle"
            )
        return None
    if not raw:
        raise DatabaseCommandError("acceptance Compose override is required")
    try:
        expected = protected_runtime_path(
            root, "dev-build", ACCEPTANCE_OVERRIDE_NAME
        )
    except ValueError as error:
        raise DatabaseCommandError(str(error)) from error
    supplied = Path(os.path.abspath(os.fspath(Path(raw).expanduser())))
    if supplied != expected:
        raise DatabaseCommandError("acceptance Compose override path mismatch")
    if not expected.is_file() or expected.is_symlink():
        raise DatabaseCommandError("acceptance Compose override is unavailable")
    return expected


def compose_prefix() -> list[str]:
    """Return the protected, profile-complete Compose argv prefix."""
    root = _runtime_root()
    project = _compose_project_name()
    command = [
        "docker",
        "compose",
        "--env-file",
        str(root / "dev-build/runtime.env"),
        "--env-file",
        str(root / "dev-build/images.env"),
        "-f",
        str(COMPOSE_FILE),
    ]
    override = _compose_override_path(root, project)
    if override is not None:
        command.extend(("-f", str(override)))
    for profile in PROFILES:
        command.extend(("--profile", profile))
    return command


def psql(sql: str, database: str = DEFAULT_DATABASE) -> str:
    """Pipe SQL to the protected Compose PostgreSQL service."""
    project = _compose_project_name()
    command = [
        *compose_prefix(),
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "dcim_bootstrap",
        "-d",
        database,
        "-v",
        "ON_ERROR_STOP=1",
        "-X",
        "-A",
        "-t",
    ]
    environment = os.environ.copy()
    environment["COMPOSE_PROJECT_NAME"] = project
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            input=sql,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
            shell=False,
            env=environment,
        )
    except subprocess.TimeoutExpired as error:
        raise DatabaseCommandError("PostgreSQL command timed out") from error
    except OSError as error:
        raise DatabaseCommandError("PostgreSQL command could not start") from error
    if result.returncode:
        raise DatabaseCommandError(
            f"PostgreSQL command failed with exit {result.returncode}"
        )
    return result.stdout


def psql_file(path: Path, database: str = DEFAULT_DATABASE) -> str:
    """Pipe one UTF-8 Python-owned SQL text file to PostgreSQL."""
    try:
        sql = path.read_text(encoding="utf-8")
    except OSError as error:
        raise DatabaseCommandError(f"SQL input file is unavailable: {path.name}") from error
    return psql(sql, database)


def parse_json_rows(output: str) -> list[JsonObject]:
    """Parse one JSON object per non-empty psql result row."""
    if not output:
        return []
    rows: list[JsonObject] = []
    for line_number, line in enumerate(output.splitlines(), start=1):
        if not line.strip():
            raise JsonExtractionError(line_number, "blank row")
        try:
            decoded: JsonValue = json.loads(
                line,
                object_pairs_hook=_unique_json_object,
                parse_constant=_reject_nonfinite_json,
            )
        except (
            json.JSONDecodeError,
            _DuplicateJsonKeyError,
            _NonFiniteJsonError,
        ) as error:
            raise JsonExtractionError(line_number, "malformed JSON") from error
        match decoded:
            case dict() as row:
                rows.append(row)
            case str() | int() | float() | None | list():
                raise JsonExtractionError(line_number, "expected a JSON object")
            case unreachable:
                assert_never(unreachable)
    return rows


def query_json(sql: str, database: str = DEFAULT_DATABASE) -> list[JsonObject]:
    """Execute an extraction-protocol query and return parsed objects."""
    return parse_json_rows(psql(sql, database))
