#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

# ─── How to run ───
# 1. Start the synthetic foundation PostgreSQL service.
# 2. Run: python3 scripts/phase2/capacity.py
# 3. Negative test: python3 scripts/phase2/capacity.py --force-threshold-for-test 100
# ──────────────────
"""Apply the Phase 1 90-percent logical-capacity admission threshold.

The threshold and its "stop admission at the same threshold" requirement come
from docs/plan/PHASE1-COMPACT-INFRASTRUCTURE-FOUNDATION.md:248-251.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from pathlib import Path
import sys
from typing import Final, override


ROOT: Final = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase2 import db  # noqa: E402


ADMISSION_THRESHOLD_PERCENT: Final = 90.0
POSTGRES_LOGICAL_BUDGET_BYTES: Final = 20 * 1024 * 1024 * 1024
ADMISSION_POLICY_SOURCE: Final = (
    "docs/plan/PHASE1-COMPACT-INFRASTRUCTURE-FOUNDATION.md:248-251"
)


@dataclass(frozen=True, slots=True)
class CapacityError(RuntimeError):
    """Capacity input or measurement violated the admission contract."""

    reason: str

    @override
    def __str__(self) -> str:
        return self.reason


class CapacityNamespace(argparse.Namespace):
    def __init__(self) -> None:
        super().__init__()
        self.force_threshold_for_test: float | None = None


def measured_usage_percent() -> float:
    """Return PostgreSQL logical use against the Phase 1 20-GiB budget."""
    rows = db.query_json(
        f"""
SELECT json_build_object(
    'usage_percent',
    round((100.0 * pg_database_size(current_database())
        / {POSTGRES_LOGICAL_BUDGET_BYTES})::numeric, 6)
)::text;
"""
    )
    if len(rows) != 1:
        raise CapacityError("capacity measurement returned unexpected rows")
    value = rows[0].get("usage_percent")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CapacityError("capacity measurement returned an invalid percentage")
    return float(value)


def admit(usage_percent: float) -> bool:
    """Return whether one new run remains below the exact policy threshold."""
    if not math.isfinite(usage_percent):
        raise CapacityError("capacity percentage must be finite")
    if usage_percent < 0.0 or usage_percent > 100.0:
        raise CapacityError("capacity percentage must be between 0 and 100")
    return usage_percent < ADMISSION_THRESHOLD_PERCENT


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--force-threshold-for-test",
        type=float,
        metavar="PCT",
        help=(
            "force a refusal for a controlled negative test; the value must be"
            f" at or above {ADMISSION_THRESHOLD_PERCENT:g} percent and can never"
            " grant admission"
        ),
    )
    return parser


def forced_refusal_usage(value: float) -> float:
    """Accept an injected usage value only when it forces a refusal."""
    if not math.isfinite(value):
        raise CapacityError("capacity percentage must be finite")
    if value < 0.0 or value > 100.0:
        raise CapacityError("capacity percentage must be between 0 and 100")
    if value < ADMISSION_THRESHOLD_PERCENT:
        raise CapacityError(
            "--force-threshold-for-test can only force a refusal:"
            f" {value:.6f}% is below the {ADMISSION_THRESHOLD_PERCENT:g}%"
            f" admission threshold ({ADMISSION_POLICY_SOURCE});"
            " omit the flag to measure real logical usage"
        )
    return value


def run(argv: list[str] | None = None) -> int:
    """Measure or force-refuse logical usage and print the admission disposition."""
    arguments = _parser().parse_args(argv, namespace=CapacityNamespace())
    forced: float | None = arguments.force_threshold_for_test
    usage = (
        measured_usage_percent()
        if forced is None
        else forced_refusal_usage(forced)
    )
    if not admit(usage):
        reason = (
            f"phase2-capacity: REFUSED: logical usage {usage:.6f}%"
            " is at or above the 90% admission threshold"
        )
        print(reason, file=sys.stderr)
        return 1
    print(
        f"phase2-capacity: usage={usage:.6f}% below 90% admission threshold PASS"
    )
    return 0


def main() -> int:
    """Translate expected capacity failures into a clean nonzero result."""
    try:
        return run()
    except (CapacityError, db.DatabaseCommandError, db.JsonExtractionError) as error:
        print(f"phase2-capacity: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
