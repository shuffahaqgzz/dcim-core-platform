#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Verify one run:
#      uv run scripts/phase2/reconcile.py --run-id ID
# 3. Or use the repository Python:
#      python3 scripts/phase2/reconcile.py --all
# ──────────────────
"""Verify durable Phase 2 dispositions from PostgreSQL."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import assert_never, Final, override, TypedDict


ROOT: Final = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase2.db import (  # noqa: E402
    DatabaseCommandError,
    JsonExtractionError,
    JsonObject,
    literal,
    query_json,
)
from scripts.phase2.errors import Phase2Error  # noqa: E402
from scripts.phase2.execution import (  # noqa: E402
    ExecutionContext,
    ReconciliationError,
    reconcile_execution,
)


@dataclass(frozen=True, slots=True)
class ReconcileCliError(Phase2Error):
    """The requested reconciliation scope cannot be verified."""

    reason: str

    @override
    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class ManifestExecution:
    run_id: str
    fixed_clock: str
    execution_sequence: int


class ReconcileSummary(TypedDict, total=False):
    reconciled: bool
    execution_count: int
    run_count: int
    run_id: str
    execution_sequences: list[int]


def _manifest_rows(run_id: str | None) -> list[JsonObject]:
    predicate = "" if run_id is None else f"WHERE run_id = {literal(run_id)}"
    return query_json(
        f"""
SELECT json_build_object(
    'run_id', run_id,
    'fixed_clock', fixed_clock,
    'last_execution_sequence', last_execution_sequence
)::text
FROM phase2.run_manifests
{predicate}
ORDER BY run_id;
"""
    )


def _manifest_executions(
    run_id: str | None, execution_sequence: int | None
) -> list[ManifestExecution]:
    rows = _manifest_rows(run_id)
    if run_id is not None and not rows:
        raise ReconcileCliError(f"run_id {run_id} has no manifest row")
    executions: list[ManifestExecution] = []
    for row in rows:
        values = (
            row.get("run_id"),
            row.get("fixed_clock"),
            row.get("last_execution_sequence"),
        )
        match values:
            case (str() as stored_run_id, str() as fixed_clock, int() as last):
                pass
            case unreachable:
                assert_never(unreachable)
        if last == 0:
            raise ReconcileCliError(f"run_id {stored_run_id} has nothing to verify")
        if execution_sequence is not None and execution_sequence > last:
            raise ReconcileCliError(
                f"execution_sequence {execution_sequence} for run_id {stored_run_id} "
                f"exceeds last_execution_sequence {last}"
            )
        sequences = (
            range(1, last + 1)
            if execution_sequence is None
            else (execution_sequence,)
        )
        executions.extend(
            ManifestExecution(stored_run_id, fixed_clock, sequence)
            for sequence in sequences
        )
    if not executions:
        raise ReconcileCliError("no manifests found; nothing to verify")
    return executions


def _failure_detail(execution: ManifestExecution) -> str:
    rows = query_json(
        f"""
SELECT json_build_object(
    'expected', manifest.source_count,
    'actual', count(disposition.disposition_id),
    'terminal', count(disposition.disposition_id) FILTER (
        WHERE disposition.status IN ('accepted', 'quarantined', 'duplicate')
    ),
    'ordinals', COALESCE(
        json_agg(disposition.input_ordinal ORDER BY disposition.input_ordinal)
            FILTER (WHERE disposition.disposition_id IS NOT NULL),
        '[]'::json
    )
)::text
FROM phase2.run_manifests AS manifest
LEFT JOIN phase2.dispositions AS disposition
    ON disposition.run_id = manifest.run_id
    AND disposition.execution_sequence = {execution.execution_sequence}
WHERE manifest.run_id = {literal(execution.run_id)}
GROUP BY manifest.run_id, manifest.source_count
ORDER BY manifest.run_id;
"""
    )
    if len(rows) != 1:
        return "expected=unknown actual=unknown"
    row = rows[0]
    return (
        f"expected={row.get('expected')} actual={row.get('actual')} "
        f"terminal={row.get('terminal')} ordinals={row.get('ordinals')}"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--run-id")
    scope.add_argument("--all", action="store_true")
    parser.add_argument("--execution-sequence", type=int)
    return parser


def run(argv: list[str] | None = None) -> int:
    """Verify the requested execution scope and print canonical success JSON."""
    arguments = _parser().parse_args(argv)
    if arguments.execution_sequence is not None and arguments.run_id is None:
        raise ReconcileCliError("--execution-sequence requires --run-id")
    if arguments.execution_sequence is not None and arguments.execution_sequence < 1:
        raise ReconcileCliError("--execution-sequence must be at least 1")
    executions = _manifest_executions(
        arguments.run_id, arguments.execution_sequence
    )
    failures: list[str] = []
    for execution in executions:
        context = ExecutionContext(
            run_id=execution.run_id,
            fixed_clock=execution.fixed_clock,
            execution_sequence=execution.execution_sequence,
        )
        try:
            reconcile_execution(context)
        except ReconciliationError as error:
            failures.append(
                f"ReconciliationError: {error}; {_failure_detail(execution)}"
            )
    if failures:
        raise ReconcileCliError("\n".join(failures))
    run_ids = sorted({execution.run_id for execution in executions})
    summary: ReconcileSummary = {
        "execution_count": len(executions),
        "reconciled": True,
        "run_count": len(run_ids),
    }
    if arguments.run_id is not None:
        summary["run_id"] = arguments.run_id
        summary["execution_sequences"] = [
            execution.execution_sequence for execution in executions
        ]
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
    """Translate expected reconciliation failures into a clean nonzero result."""
    try:
        return run()
    except (
        DatabaseCommandError,
        JsonExtractionError,
        ReconcileCliError,
    ) as error:
        print(f"phase2 reconciliation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
