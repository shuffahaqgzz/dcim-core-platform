#!/usr/bin/env python3
"""Validate presence and public-safe structure of mandatory synthetic fixtures."""
from __future__ import annotations

import csv
import ipaddress
import json
from pathlib import Path
import sys

from check_public_repo_safety import scan_paths

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "synthetic"
REQUIRED = (
    "events/p1-redfish-health.json",
    "events/p1-ups-alarm.json",
    "events/p2-network-utilization.json",
    "events/p2-nas-capacity.json",
    "events/p2-nvr-health.json",
    "events/p2-server-capacity.json",
    "assets.csv",
    "invalid/invalid-event.json",
    "sanitization/expected-sanitized-event.json",
)
DOC_NETWORKS = tuple(ipaddress.ip_network(item) for item in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24"))


def validate_asset_row(row: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if not row.get("asset_id", "").startswith("SYNTHETIC-"):
        errors.append("asset_id lacks explicit synthetic marker")
    if not row.get("manufacturer", "").lower().startswith(("example", "synthetic")):
        errors.append("manufacturer lacks explicit public-safe marker")
    if not row.get("serial_number", "").startswith("SYNTHETIC-"):
        errors.append("serial_number lacks explicit synthetic marker")
    if not row.get("hostname", "").endswith((".example.com", ".example.invalid")):
        errors.append("hostname is not a documentation domain")
    if not row.get("location", "").startswith("GENERIC-"):
        errors.append("location lacks explicit generic marker")
    try:
        address = ipaddress.ip_address(row.get("ip_address", ""))
    except ValueError:
        errors.append("ip_address is invalid")
    else:
        if not any(address in network for network in DOC_NETWORKS):
            errors.append("ip_address is not a documentation address")
    return errors


def fixture_inventory_errors(relative_paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in sorted(relative_paths):
        if path.as_posix() in {"README.md", "assets.csv"} or path.suffix == ".json":
            continue
        errors.append(f"unsupported synthetic fixture: {path.as_posix()}")
    return errors


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (FIXTURES / relative).is_file():
            errors.append(f"missing fixture: {relative}")
    for path in FIXTURES.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
    fixture_paths = sorted(path for path in FIXTURES.rglob("*") if path.is_file())
    errors.extend(
        fixture_inventory_errors([path.relative_to(FIXTURES) for path in fixture_paths])
    )
    for finding in scan_paths(fixture_paths, ROOT):
        errors.append(
            f"public-safety violation {finding.path} [{finding.rule}]; value=<redacted>"
        )
    assets = FIXTURES / "assets.csv"
    if assets.exists():
        with assets.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        required_columns = {"asset_id", "manufacturer", "serial_number", "hostname", "ip_address", "location"}
        if not rows or not required_columns.issubset(rows[0]):
            errors.append("assets.csv lacks required columns or rows")
        for row_number, row in enumerate(rows, 2):
            for error in validate_asset_row(row):
                errors.append(f"assets.csv row {row_number}: {error}")
    invalid = FIXTURES / "invalid" / "invalid-event.json"
    if invalid.exists():
        data = json.loads(invalid.read_text(encoding="utf-8"))
        if data.get("expected_disposition") != "quarantine" or not data.get("expected_reason"):
            errors.append("invalid fixture lacks quarantine reason")
    if errors:
        print("Synthetic fixture validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Synthetic fixture validation passed ({len(REQUIRED)} mandatory fixtures).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
