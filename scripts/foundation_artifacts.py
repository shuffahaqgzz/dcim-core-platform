#!/usr/bin/env python3
"""Fetch immutable public runtime artifacts into protected external storage."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "deploy/compose/images.json"


def outside_repository(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        return resolved
    raise ValueError("DCIM_RUNTIME_ROOT must resolve outside repository")


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def fetch(runtime_root: Path) -> None:
    root = outside_repository(runtime_root)
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    directory = root / "dev-build/artifacts"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    for artifact in inventory["artifacts"]:
        destination = directory / artifact["filename"]
        if destination.exists():
            if digest(destination) != artifact["sha256"]:
                raise ValueError(f"existing artifact checksum mismatch: {artifact['filename']}")
            destination.chmod(0o444)
            continue
        descriptor, temporary_name = tempfile.mkstemp(prefix=".download-", dir=directory)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as output, urlopen(artifact["download"], timeout=60) as source:
                while block := source.read(1024 * 1024):
                    output.write(block)
            if digest(temporary) != artifact["sha256"]:
                raise ValueError(f"downloaded artifact checksum mismatch: {artifact['filename']}")
            temporary.chmod(0o444)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        fetch(arguments.runtime_root)
    except (OSError, ValueError) as error:
        print(f"foundation-artifacts: {error}", file=sys.stderr)
        return 1
    print("foundation-artifacts: verified immutable public artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
