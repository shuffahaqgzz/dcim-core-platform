"""Build and adapt the bounded synthetic fixture input set."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Literal, override

from connectors.redfish.adapter import RedfishFixtureAdapter
from connectors.snmp.adapter import SNMPv3FixtureAdapter
from contracts.python.dcim_contracts.disposition import JsonValue

from .errors import KillSwitchEngaged, Phase2Error
from .manifest import RunManifest, SourceSpec


@dataclass(frozen=True, slots=True)
class RunnerInputError(Phase2Error):
    error_type: Literal[
        "fixtures_empty", "json_syntax_error", "json_root_not_object"
    ]
    detail: str

    @override
    def __str__(self) -> str:
        return f"{self.error_type}: {self.detail}"


def build_manifest(
    run_id: str,
    fixtures_dir: Path,
    fixed_clock: str,
    repository_root: Path,
) -> RunManifest:
    paths = tuple(sorted(fixtures_dir.glob("*.json")))
    if not paths:
        raise RunnerInputError(
            error_type="fixtures_empty",
            detail="fixtures directory contains no JSON inputs",
        )
    sources = tuple(
        SourceSpec(
            name=path.name,
            fixture_path=str(path.resolve().relative_to(repository_root))
            if path.resolve().is_relative_to(repository_root)
            else path.name,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in paths
    )
    return RunManifest(run_id=run_id, fixed_clock=fixed_clock, sources=sources)


def _load_json(path: Path) -> dict[str, JsonValue]:
    try:
        candidate = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RunnerInputError(
            error_type="json_syntax_error",
            detail="fixture is not valid JSON",
        ) from error
    if not isinstance(candidate, dict):
        raise RunnerInputError(
            error_type="json_root_not_object",
            detail="fixture root must be a JSON object",
        )
    return candidate


def _is_killed(fixtures_dir: Path) -> bool:
    return os.environ.get("PHASE2_KILL_SWITCH") == "1" or (
        fixtures_dir / ".phase2-stop"
    ).exists()


def adapt_input(
    path: Path,
    fixtures_dir: Path,
    fixed_clock: str,
) -> Mapping[str, JsonValue]:
    raw = _load_json(path)
    source = raw.get("source")
    connector = source.get("connector") if isinstance(source, dict) else None
    stop_file = fixtures_dir / ".phase2-stop"
    kill_flag = lambda: _is_killed(fixtures_dir)
    if connector == "redfish-fixture":
        return next(
            iter(RedfishFixtureAdapter([path], fixed_clock, kill_flag, stop_file))
        )
    if connector == "snmpv3-fixture" or path.name == "p2-network-utilization.json":
        return next(
            iter(SNMPv3FixtureAdapter([path], fixed_clock, kill_flag, stop_file))
        )
    if kill_flag():
        raise KillSwitchEngaged("Phase 2 fixture runner kill switch engaged")
    return raw


def input_paths(manifest: RunManifest, fixtures_dir: Path) -> Iterator[Path]:
    by_name = {path.name: path for path in fixtures_dir.glob("*.json")}
    for source in manifest.sources:
        yield by_name[source.name]
