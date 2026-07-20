#!/usr/bin/env python3
"""Interactively remove only allowlisted dcim-build named volumes."""

from __future__ import annotations

import os
import subprocess
import sys


ALLOWED = {
    "dcim-build-postgres-data", "dcim-build-kafka-data", "dcim-build-prometheus-data",
}


def main() -> int:
    if os.environ.get("CI") or not sys.stdin.isatty():
        print("foundation-reset: interactive terminal required; unavailable in CI", file=sys.stderr)
        return 1
    result = subprocess.run(
        ["docker", "volume", "ls", "--filter", "label=com.docker.compose.project=dcim-build", "--format", "{{.Name}}"],
        capture_output=True, text=True, check=False, timeout=15,
    )
    if result.returncode:
        print("foundation-reset: unable to resolve dcim-build volumes", file=sys.stderr)
        return 1
    resolved = {line for line in result.stdout.splitlines() if line}
    unexpected = resolved - ALLOWED
    if unexpected:
        print("foundation-reset: unexpected labeled volume; refusing reset", file=sys.stderr)
        return 1
    confirmation = input("Type 'reset dcim-build' to remove resolved dcim-build volumes: ")
    if confirmation != "reset dcim-build":
        print("foundation-reset: cancelled", file=sys.stderr)
        return 1
    if not resolved:
        print("foundation-reset: no dcim-build volumes found")
        return 0
    removal = subprocess.run(
        ["docker", "volume", "rm", *sorted(resolved)], check=False, timeout=30,
    )
    return removal.returncode


if __name__ == "__main__":
    raise SystemExit(main())
