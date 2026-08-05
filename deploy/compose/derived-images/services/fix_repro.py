#!/usr/bin/env python3

from __future__ import annotations

import base64
import hashlib
import pathlib
import re
import sys

VENV = pathlib.Path("/opt/venv")
PIP_BUILD_PATH = re.compile(rb"pip-install-[^/]+/confluent-kafka_[^/]+/")


def scrub_cimpl() -> int:
    count = 0
    for path in VENV.rglob("cimpl*.so"):
        original = path.read_bytes()
        rewritten = PIP_BUILD_PATH.sub(lambda match: b"." * len(match.group()), original)
        if rewritten != original:
            path.write_bytes(rewritten)
            count += 1
    return count


def rewrite_record() -> int:
    count = 0
    for record in VENV.rglob("confluent_kafka-*.dist-info/RECORD"):
        lines: list[str] = []
        changed = False
        for line in record.read_text(encoding="utf-8").splitlines(True):
            if line.startswith("confluent_kafka/cimpl"):
                name = line.split(",", 1)[0]
                payload = (record.parent.parent / name).read_bytes()
                digest = (
                    base64.urlsafe_b64encode(hashlib.sha256(payload).digest())
                    .decode("ascii")
                    .rstrip("=")
                )
                lines.append(f"{name},sha256={digest},{len(payload)}\n")
                changed = True
            else:
                lines.append(line)
        if changed:
            record.write_text("".join(lines), encoding="utf-8")
            count += 1
    return count


def main() -> int:
    scrubbed = scrub_cimpl()
    records = rewrite_record()
    print(f"fix-repro: scrubbed_cimpl={scrubbed} records={records}", flush=True)
    if scrubbed < 1:
        print("fix-repro: expected at least one cimpl*.so", file=sys.stderr)
        return 1
    if records < 1:
        print("fix-repro: expected at least one confluent_kafka RECORD", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
