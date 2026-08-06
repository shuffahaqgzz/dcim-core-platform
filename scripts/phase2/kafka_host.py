#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

# ─── How to run ───
# 1. Install uv (if installed scripts are preferred):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Transform a hosts file with Python's standard library:
#      python3 scripts/phase2/kafka_host.py ADDRESS INPUT OUTPUT
# 3. Or make executable and run:
#      chmod +x scripts/phase2/kafka_host.py && ./scripts/phase2/kafka_host.py ADDRESS INPUT OUTPUT
# ──────────────────

"""Validate and transform hosts-file bytes for temporary Kafka resolution."""

from __future__ import annotations

import ipaddress
from pathlib import Path
import sys
from typing import Final, Sequence


HOSTS_COMMENT: Final = "dcim-build dev plane (host-side gate access)"


class KafkaHostError(Exception):
    pass


class InvalidAddressError(KafkaHostError):
    def __str__(self) -> str:
        return "Kafka container address is invalid"


class HostsConflictError(KafkaHostError):
    def __str__(self) -> str:
        return "conflicting kafka hostname mapping already exists"


class HostsReadError(KafkaHostError):
    def __str__(self) -> str:
        return "hosts input could not be read"


class HostsWriteError(KafkaHostError):
    def __str__(self) -> str:
        return "hosts output could not be written"


class ArgumentsError(KafkaHostError):
    def __str__(self) -> str:
        return "address, input path, and output path are required"


def add_kafka_mapping(original: bytes, address: str) -> bytes:
    try:
        normalized_address = str(ipaddress.ip_address(address))
        address_bytes = normalized_address.encode("ascii")
    except (UnicodeEncodeError, ValueError) as error:
        raise InvalidAddressError from error

    mapping = f"{normalized_address} kafka # {HOSTS_COMMENT}\n".encode("ascii")
    for raw_line in original.splitlines():
        fields = raw_line.split(b"#", 1)[0].split()
        if len(fields) >= 2 and b"kafka" in fields[1:] and fields[0] != address_bytes:
            raise HostsConflictError
    if mapping.rstrip(b"\n") in original.splitlines():
        return original
    separator = b"" if not original or original.endswith(b"\n") else b"\n"
    return original + separator + mapping


def transform_hosts(source: Path, destination: Path, address: str) -> None:
    try:
        original = source.read_bytes()
    except OSError as error:
        raise HostsReadError from error
    updated = add_kafka_mapping(original, address)
    try:
        destination.write_bytes(updated)
    except OSError as error:
        raise HostsWriteError from error


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 3:
        error = ArgumentsError()
        print(f"kafka-host: FAIL: {error}", file=sys.stderr)
        return 2
    address, source, destination = arguments
    try:
        transform_hosts(Path(source), Path(destination), address)
    except KafkaHostError as error:
        print(f"kafka-host: FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
