#!/usr/bin/env python3
"""Generate a public-safe evidence summary from external foundation evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

EVIDENCE_ALLOWLIST: frozenset[str] = frozenset({
    "schema_version",
    "commit",
    "capability_profiles",
    "utc_timestamp",
    "duration_seconds",
    "assertion_result",
    "synthetic_run_id",
    "mode",
    "image_digests",
})

REQUIRED_FIELDS: frozenset[str] = frozenset({
    "schema_version",
    "commit",
    "capability_profiles",
    "utc_timestamp",
    "duration_seconds",
    "assertion_result",
    "synthetic_run_id",
    "mode",
    "image_digests",
})


def validate_evidence_record(record: dict[str, object]) -> list[str]:
    """Return validation errors for a single evidence record."""
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"missing required field: {field}")
    extra = set(record) - EVIDENCE_ALLOWLIST
    for field in sorted(extra):
        errors.append(f"prohibited field present: {field}")
    if record.get("schema_version") != 2:
        errors.append("schema_version must be 2")
    return errors


def load_evidence_files(directory: Path) -> list[dict[str, Any]]:
    """Load valid evidence JSON files from a directory."""
    records: list[dict[str, Any]] = []
    if not directory.is_dir():
        return records
    for path in sorted(directory.iterdir()):
        if not path.name.endswith(".json"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        errors = validate_evidence_record(data)
        if not errors:
            records.append(data)
    return records


def summarize_evidence(
    records: list[dict[str, Any]], commit: str,
) -> dict[str, Any]:
    """Produce a public-safe summary from evidence records."""
    runs: list[dict[str, Any]] = []
    image_digests: dict[str, str] = {}

    for record in records:
        runs.append({
            "mode": record.get("mode"),
            "assertion_result": record.get("assertion_result"),
            "duration_seconds": record.get("duration_seconds"),
            "utc_timestamp": record.get("utc_timestamp"),
            "synthetic_run_id": record.get("synthetic_run_id"),
            "capability_profiles": record.get("capability_profiles"),
        })
        digests = record.get("image_digests")
        if isinstance(digests, dict):
            image_digests = dict(sorted(digests.items()))

    all_pass = bool(runs) and all(
        run["assertion_result"] == "pass" for run in runs
    )

    return {
        "schema_version": 1,
        "commit": commit,
        "overall_result": "pass" if all_pass else "fail",
        "runs": runs,
        "image_digests": image_digests,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate public-safe evidence summary",
    )
    parser.add_argument(
        "--evidence-dir", required=True, type=Path,
        help="directory containing evidence JSON files",
    )
    parser.add_argument(
        "--commit", required=True,
        help="git commit hash",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="output file path (stdout if omitted)",
    )
    arguments = parser.parse_args()

    records = load_evidence_files(arguments.evidence_dir)
    summary = summarize_evidence(records, arguments.commit)

    output = json.dumps(summary, indent=2, sort_keys=True) + "\n"

    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
