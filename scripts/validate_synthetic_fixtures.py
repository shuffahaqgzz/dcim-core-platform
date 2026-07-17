#!/usr/bin/env python3
"""Validate presence and public-safe structure of mandatory synthetic fixtures."""
from __future__ import annotations

import csv
import ipaddress
import json
from pathlib import Path
import sys

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
    assets = FIXTURES / "assets.csv"
    if assets.exists():
        with assets.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        required_columns = {"asset_id", "manufacturer", "serial_number", "hostname", "ip_address", "location"}
        if not rows or not required_columns.issubset(rows[0]):
            errors.append("assets.csv lacks required columns or rows")
        for row in rows:
            if "SYNTHETIC" not in row["serial_number"] or not row["hostname"].endswith(".example.com"):
                errors.append("assets.csv contains non-synthetic identity")
            try:
                address = ipaddress.ip_address(row["ip_address"])
            except ValueError:
                errors.append("assets.csv contains invalid IP")
            else:
                if not any(address in network for network in DOC_NETWORKS):
                    errors.append("assets.csv contains non-documentation IP")
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
