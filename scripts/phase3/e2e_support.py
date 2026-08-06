from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Final

from scripts.phase2 import db


ROOT: Final = Path(__file__).resolve().parents[2]
DEFAULT_FIXED_CLOCK: Final = "2026-08-06T00:00:00Z"
COMMAND_TIMEOUT_SECONDS: Final = 300


class E2EFailure(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StageFailure(E2EFailure):
    number: int
    name: str
    reason: str

    def __str__(self) -> str:
        return f"e2e: stage {self.number} {self.name}: FAIL: {self.reason}"


@dataclass(frozen=True, slots=True)
class E2EConfig:
    output: Path
    fixtures_dir: Path
    token_file: Path
    fixed_clock: str = DEFAULT_FIXED_CLOCK
    idle_timeout_seconds: float = 30.0


@dataclass(slots=True)
class E2EState:
    config: E2EConfig
    run_id: str
    completed_stages: list[str] = field(default_factory=list)
    producer_ledger: dict[str, int] = field(default_factory=dict)
    consumer_ledger: dict[str, int] = field(default_factory=dict)
    database_counts: dict[str, int] = field(default_factory=dict)
    dashboard: dict[str, int] = field(default_factory=dict)
    latency: dict[str, int | float | str] = field(default_factory=dict)
    checks: dict[str, bool] = field(default_factory=dict)
    work_dir: Path | None = None
    start_offsets: Path | None = None
    temporary_files: list[Path] = field(default_factory=list)
    stream_started: bool = False
    cleanup_complete: bool = False


def _run_command(
    command: list[str],
    label: str,
    *,
    cwd: Path = ROOT,
    timeout: int = COMMAND_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise E2EFailure(f"{label} command failed") from error


def parse_object(raw: str, context: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise E2EFailure(f"{context} output is not valid JSON") from error
    if not isinstance(value, dict):
        raise E2EFailure(f"{context} output is not a JSON object")
    return value


def read_json_object(path: Path, context: str) -> dict[str, object]:
    try:
        return parse_object(path.read_text(encoding="utf-8"), context)
    except OSError as error:
        raise E2EFailure(f"{context} output is unavailable") from error


def integer(value: object, context: str) -> int:
    if type(value) is not int or value < 0:
        raise E2EFailure(f"{context} count is invalid")
    return value


def cleanup_run(run_id: str) -> None:
    for table in ("dispositions", "noc_cards", "events", "run_manifests"):
        try:
            db.psql(
                f"DELETE FROM phase2.{table} WHERE run_id = {db.literal(run_id)};"
            )
        except db.DatabaseCommandError as error:
            raise E2EFailure("E2E database cleanup failed") from error


def cleanup_files(state: E2EState) -> None:
    for path in state.temporary_files:
        try:
            path.unlink(missing_ok=True)
        except OSError as error:
            raise E2EFailure("E2E temporary cleanup failed") from error
    if state.work_dir is not None:
        try:
            state.work_dir.rmdir()
        except OSError as error:
            raise E2EFailure("E2E work-directory cleanup failed") from error


def commit_sha() -> str:
    result = _run_command(["git", "rev-parse", "HEAD"], "commit lookup")
    if result.returncode != 0:
        raise E2EFailure("commit lookup failed")
    value = result.stdout.strip()
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise E2EFailure("commit lookup returned an invalid SHA")
    return value


def build_evidence(
    state: E2EState,
    *,
    commit_sha: str,
    generated_at: str,
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "commit_sha": commit_sha,
        "timestamp": generated_at,
        "run_id": state.run_id,
        "stages": list(state.completed_stages),
        "producer_ledger": dict(state.producer_ledger),
        "consumer_ledger": dict(state.consumer_ledger),
        "counts": dict(state.database_counts),
        "dashboard": dict(state.dashboard),
        "latency": dict(state.latency),
        "checks": dict(state.checks),
    }


def write_evidence(state: E2EState, evidence: dict[str, object]) -> None:
    state.config.output.parent.mkdir(parents=True, exist_ok=True)
    state.config.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
