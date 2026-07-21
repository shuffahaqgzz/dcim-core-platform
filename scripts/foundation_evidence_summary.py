#!/usr/bin/env python3
"""Generate a public-safe evidence summary from external foundation evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
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
    "source_commit",
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

SMOKE_EVIDENCE_NAME = re.compile(r"^(fast|recovery)-.+\.json$")
SUMMARY_FIELDS: frozenset[str] = frozenset({
    "schema_version", "commit", "overall_result", "runs", "image_digests",
})
SUMMARY_RUN_FIELDS: frozenset[str] = frozenset({
    "mode", "assertion_result", "duration_seconds", "utc_timestamp",
    "synthetic_run_id", "capability_profiles", "source_commit",
})
ACCEPTANCE_REPORT_FIELDS: frozenset[str] = frozenset({
    "schema_version", "commit", "project_scope", "started_utc",
    "finished_utc", "result", "steps", "failure_reason",
})
ACCEPTANCE_STEP_FIELDS: frozenset[str] = frozenset({
    "step", "exit_code", "duration_seconds",
})


def validate_evidence_record(record: dict[str, object]) -> list[str]:
    """Return validation errors for a single evidence record."""
    errors = schema_evidence_errors(record)
    errors.extend(public_safety_evidence_errors(record))
    return errors


def schema_evidence_errors(record: dict[str, object]) -> list[str]:
    """Return schema-contract errors for a single evidence record."""
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"missing required field: {field}")
    if record.get("schema_version") != 2:
        errors.append("schema_version must be 2")
    return errors


def public_safety_evidence_errors(record: dict[str, object]) -> list[str]:
    """Return public-safety errors for a single evidence record."""
    errors: list[str] = []
    extra = set(record) - EVIDENCE_ALLOWLIST
    for field in sorted(extra):
        errors.append(f"prohibited field present: {field}")
    return errors


def extra_field_errors(
    record: dict[str, object], allowed: frozenset[str], *, prefix: str = "",
) -> list[str]:
    errors: list[str] = []
    extra = set(record) - allowed
    for field in sorted(extra):
        location = f"{prefix}{field}" if prefix else field
        errors.append(f"prohibited field present: {location}")
    return errors


def validate_summary_artifact(record: dict[str, Any]) -> list[str]:
    """Return validation errors for a generated public-safe summary artifact."""
    errors = extra_field_errors(record, SUMMARY_FIELDS)
    if record.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    runs = record.get("runs")
    if runs is not None:
        if not isinstance(runs, list):
            errors.append("runs must be a list")
        else:
            for index, run in enumerate(runs):
                if not isinstance(run, dict):
                    errors.append(f"runs[{index}] must be an object")
                    continue
                errors.extend(
                    extra_field_errors(
                        run, SUMMARY_RUN_FIELDS, prefix=f"runs[{index}].",
                    )
                )
    return errors


def validate_acceptance_report_artifact(record: dict[str, Any]) -> list[str]:
    """Return validation errors for a generated public-safe acceptance report."""
    errors = extra_field_errors(record, ACCEPTANCE_REPORT_FIELDS)
    if record.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    steps = record.get("steps")
    if steps is not None:
        if not isinstance(steps, list):
            errors.append("steps must be a list")
        else:
            for index, step in enumerate(steps):
                if not isinstance(step, dict):
                    errors.append(f"steps[{index}] must be an object")
                    continue
                errors.extend(
                    extra_field_errors(
                        step, ACCEPTANCE_STEP_FIELDS, prefix=f"steps[{index}].",
                    )
                )
    return errors


def generated_artifact_errors(name: str, record: dict[str, Any]) -> list[str] | None:
    if name == "phase1-clean-acceptance-summary.json":
        return validate_summary_artifact(record)
    if name == "clean-runtime-acceptance.json":
        return validate_acceptance_report_artifact(record)
    return None


def load_evidence_files_with_error_categories(
    directory: Path,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Load valid evidence JSON files and categorize validation errors.

    Schema-v1 smoke records were produced by earlier Development runs and are
    public-safe but not suitable for current summaries. Non-strict summaries
    may skip those legacy records; strict clean-runtime acceptance rejects them.
    """
    records: list[dict[str, Any]] = []
    schema_errors: list[str] = []
    safety_errors: list[str] = []
    if not directory.is_dir():
        return records, schema_errors, safety_errors
    for path in sorted(directory.iterdir()):
        if not path.name.endswith(".json"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            safety_errors.append(f"{path.name}: invalid JSON evidence")
            continue
        except OSError:
            safety_errors.append(f"{path.name}: unable to read evidence file")
            continue
        if not isinstance(data, dict):
            safety_errors.append(f"{path.name}: evidence JSON must be an object")
            continue
        artifact_errors = generated_artifact_errors(path.name, data)
        if artifact_errors is not None:
            safety_errors.extend(f"{path.name}: {error}" for error in artifact_errors)
            continue
        public_safety_errors = public_safety_evidence_errors(data)
        safety_errors.extend(f"{path.name}: {error}" for error in public_safety_errors)
        if not SMOKE_EVIDENCE_NAME.fullmatch(path.name):
            safety_errors.append(f"{path.name}: unrecognized evidence JSON file")
            continue
        contract_errors = schema_evidence_errors(data)
        if contract_errors:
            prefixed = [f"{path.name}: {error}" for error in contract_errors]
            if data.get("schema_version") == 1 and not public_safety_errors:
                schema_errors.extend(prefixed)
            else:
                safety_errors.extend(prefixed)
        elif not public_safety_errors:
            records.append(data)
    return records, schema_errors, safety_errors


def load_evidence_files_with_errors(directory: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Load valid evidence JSON files and report invalid direct JSON evidence."""
    records, schema_errors, safety_errors = load_evidence_files_with_error_categories(directory)
    return records, [*safety_errors, *schema_errors]


def load_evidence_files(directory: Path) -> list[dict[str, Any]]:
    """Load valid evidence JSON files from a directory."""
    records, _schema_errors, _safety_errors = load_evidence_files_with_error_categories(directory)
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
            "source_commit": record.get("commit"),
        })
        digests = record.get("image_digests")
        if isinstance(digests, dict):
            image_digests = dict(sorted(digests.items()))

    all_pass = bool(runs) and all(
        run["assertion_result"] == "pass" for run in runs
    ) and all(
        run["source_commit"] == commit for run in runs
    )

    return {
        "schema_version": 1,
        "commit": commit,
        "overall_result": "pass" if all_pass else "fail",
        "runs": runs,
        "image_digests": image_digests,
    }


def acceptance_errors(
    records: list[dict[str, Any]],
    *,
    commit: str,
    required_modes: set[str],
    require_pass: bool,
    strict_commit: bool,
) -> list[str]:
    errors: list[str] = []
    strict_requested = bool(required_modes or require_pass or strict_commit)
    if strict_requested and not records:
        errors.append("no valid evidence records found")
    modes = {str(record.get("mode")) for record in records}
    missing_modes = required_modes - modes
    if missing_modes:
        errors.append(f"missing required evidence modes: {sorted(missing_modes)}")
    if strict_commit:
        stale = sorted({
            str(record.get("mode"))
            for record in records
            if record.get("commit") != commit
        })
        if stale:
            errors.append(f"evidence is not bound to requested commit: {stale}")
    if require_pass:
        failing = sorted({
            str(record.get("mode"))
            for record in records
            if record.get("assertion_result") != "pass"
        })
        if failing:
            errors.append(f"non-passing evidence modes present: {failing}")
    return errors


def parse_required_modes(value: str | None) -> set[str]:
    if not value:
        return set()
    modes = {item.strip() for item in value.split(",") if item.strip()}
    invalid = modes - {"fast", "recovery"}
    if invalid:
        raise ValueError(f"invalid evidence mode requested: {sorted(invalid)}")
    return modes


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
    parser.add_argument(
        "--require-modes", default="",
        help="comma-separated evidence modes that must be present",
    )
    parser.add_argument(
        "--require-pass", action="store_true",
        help="return nonzero unless all loaded evidence records pass",
    )
    parser.add_argument(
        "--strict-commit", action="store_true",
        help="return nonzero unless every loaded evidence record matches --commit",
    )
    arguments = parser.parse_args()

    try:
        required_modes = parse_required_modes(arguments.require_modes)
    except ValueError as error:
        print(f"foundation-evidence-summary: {error}", file=sys.stderr)
        return 2
    records, schema_errors, safety_errors = load_evidence_files_with_error_categories(
        arguments.evidence_dir,
    )
    summary = summarize_evidence(records, arguments.commit)
    strict_requested = bool(required_modes or arguments.require_pass or arguments.strict_commit)
    errors = acceptance_errors(
        records,
        commit=arguments.commit,
        required_modes=required_modes,
        require_pass=arguments.require_pass,
        strict_commit=arguments.strict_commit,
    )
    if strict_requested:
        errors = [*safety_errors, *schema_errors, *errors]
    else:
        errors = [*safety_errors, *errors]
    if errors:
        for error in errors:
            print(f"foundation-evidence-summary: {error}", file=sys.stderr)
        return 1

    output = json.dumps(summary, indent=2, sort_keys=True) + "\n"

    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
