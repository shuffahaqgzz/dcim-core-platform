#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.9.2"]
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly:
#      uv run scripts/phase2/run.py --run-id ID --fixtures-dir DIR --fixed-clock UTC
# 3. Or make executable and run through the uv shebang:
#      chmod +x scripts/phase2/run.py && ./scripts/phase2/run.py --help
# ──────────────────
"""Run the synthetic Phase 2 fixture pipeline transactionally."""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Final, Literal, override

from pydantic import ValidationError


ROOT: Final = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from connectors.redfish.adapter import RedfishFixtureAdapter  # noqa: E402
from connectors.snmp.adapter import SNMPv3FixtureAdapter  # noqa: E402
from contracts.python.dcim_contracts.disposition import JsonValue  # noqa: E402
from scripts.phase2.db import (  # noqa: E402
    DatabaseCommandError,
    JsonExtractionError,
)
from scripts.phase2.errors import (  # noqa: E402
    KillSwitchEngaged,
    ManifestDriftError,
    Phase2Error,
    SilentLossError,
)
from scripts.phase2.ledger import DispositionLedger  # noqa: E402
from scripts.phase2.manifest import RunManifest, SourceSpec  # noqa: E402
from scripts.phase2.persist import (  # noqa: E402
    IdentityQuarantined,
    PersistenceContext,
    PersistenceError,
    PostgresClaimStore,
    QuarantineInput,
    persist_manifest,
    persist_quarantine,
)
from scripts.phase2.validate import DispositionEngine  # noqa: E402


@dataclass(frozen=True, slots=True)
class RunnerInputError(Phase2Error):
    """A fixture input cannot cross the JSON boundary."""

    error_type: Literal[
        "fixtures_empty", "json_syntax_error", "json_root_not_object"
    ]
    detail: str

    @override
    def __str__(self) -> str:
        return f"{self.error_type}: {self.detail}"


def _manifest(run_id: str, fixtures_dir: Path, fixed_clock: str) -> RunManifest:
    paths = tuple(sorted(fixtures_dir.glob("*.json")))
    if not paths:
        raise RunnerInputError(
            error_type="fixtures_empty",
            detail="fixtures directory contains no JSON inputs",
        )
    sources = tuple(
        SourceSpec(
            name=path.name,
            fixture_path=str(path.resolve().relative_to(ROOT))
            if path.resolve().is_relative_to(ROOT)
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


def _adapt(path: Path, fixtures_dir: Path, fixed_clock: str) -> Mapping[str, JsonValue]:
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


def _inputs(manifest: RunManifest, fixtures_dir: Path) -> Iterator[Path]:
    by_name = {path.name: path for path in fixtures_dir.glob("*.json")}
    for source in manifest.sources:
        yield by_name[source.name]


def execute(run_id: str, fixtures_dir: Path, fixed_clock: str) -> dict[str, JsonValue]:
    """Execute one manifest-first batch and return its balanced summary."""
    manifest = _manifest(run_id, fixtures_dir, fixed_clock)
    persist_manifest(manifest)
    context = PersistenceContext(run_id=run_id, fixed_clock=fixed_clock)
    ledger = DispositionLedger()

    for path in _inputs(manifest, fixtures_dir):
        ledger.record("received")
        try:
            candidate = _adapt(path, fixtures_dir, fixed_clock)
            engine_ledger = DispositionLedger()
            store = PostgresClaimStore(context, candidate)
            disposition = DispositionEngine(store, engine_ledger).handle(candidate)
        except KillSwitchEngaged:
            raw = _load_json(path)
            persist_quarantine(
                context,
                QuarantineInput(
                    candidate=raw,
                    reason="kill_switch_engaged",
                    detail="kill_switch_engaged before fixture processing",
                ),
            )
            ledger.record("quarantined")
            raise
        except RunnerInputError as error:
            persist_quarantine(
                context,
                QuarantineInput(
                    candidate={},
                    reason="schema_invalid",
                    detail=f"{error.error_type}:{error.detail}",
                ),
            )
            ledger.record("quarantined")
            continue
        except IdentityQuarantined:
            ledger.record("quarantined")
            continue
        except ValidationError as error:
            candidate = _load_json(path)
            validation_types = sorted(
                {str(item["type"]) for item in error.errors(include_url=False)}
            )
            reason = (
                "payload_invalid"
                if "payload_invalid" in validation_types
                else "schema_invalid"
            )
            persist_quarantine(
                context,
                QuarantineInput(
                    candidate=candidate,
                    reason=reason,
                    detail=",".join(validation_types),
                ),
            )
            ledger.record("quarantined")
            continue
        ledger.record(disposition.status)

    ledger.assert_zero_silent_loss()
    counts = ledger.to_json()
    return {
        "run_id": run_id,
        "counts": counts,
        "manifest_sha256": manifest.manifest_sha256,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--fixtures-dir", required=True, type=Path)
    parser.add_argument("--fixed-clock", required=True)
    return parser


def run(argv: list[str] | None = None) -> int:
    """Parse the exact CLI contract, execute, and print success JSON."""
    arguments = _parser().parse_args(argv)
    summary = execute(arguments.run_id, arguments.fixtures_dir, arguments.fixed_clock)
    print(
        json.dumps(
            summary,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return 0


def main() -> int:
    """Translate expected failures into nonzero output without a success summary."""
    try:
        return run()
    except (
        DatabaseCommandError,
        JsonExtractionError,
        KillSwitchEngaged,
        ManifestDriftError,
        PersistenceError,
        RunnerInputError,
        SilentLossError,
    ) as error:
        print(f"phase2 batch failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
