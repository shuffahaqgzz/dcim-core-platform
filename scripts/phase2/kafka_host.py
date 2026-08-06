#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

# ─── How to run ───
# 1. Install uv (if installed scripts are preferred):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run with Python's standard library:
#      python3 scripts/phase2/kafka_host.py -- COMMAND [ARG ...]
# 3. Or make executable and run:
#      chmod +x scripts/phase2/kafka_host.py && ./scripts/phase2/kafka_host.py -- COMMAND [ARG ...]
# ──────────────────

"""Run a host-side Kafka gate with temporary internal-name resolution."""

from __future__ import annotations

import ipaddress
import os
from pathlib import Path
import subprocess
import sys
from typing import Final, Sequence


HOSTS_PATH: Final = Path("/etc/hosts")
KAFKA_CONTAINER: Final = "dcim-build-kafka-1"
KAFKA_BOOTSTRAP: Final = "kafka:9092"
HOSTS_COMMENT: Final = "dcim-build dev plane (host-side gate access)"
INSPECT_TIMEOUT_SECONDS: Final = 10
SUDO_TIMEOUT_SECONDS: Final = 10


class KafkaHostError(Exception):
    pass


class KafkaInspectError(KafkaHostError):
    def __str__(self) -> str:
        return "Kafka container address unavailable"


class HostsConflictError(KafkaHostError):
    def __str__(self) -> str:
        return "conflicting kafka hostname mapping already exists"


class HostsReadError(KafkaHostError):
    def __str__(self) -> str:
        return "hosts file could not be read"


class HostsWriteError(KafkaHostError):
    def __str__(self) -> str:
        return "temporary hosts mapping could not be updated or restored"


class ChildLaunchError(KafkaHostError):
    def __str__(self) -> str:
        return "gate command could not be launched"


class CommandRequiredError(KafkaHostError):
    def __str__(self) -> str:
        return "gate command is required after --"


def add_kafka_mapping(original: bytes, address: str) -> bytes:
    mapping = f"{address} kafka # {HOSTS_COMMENT}\n".encode("ascii")
    address_bytes = address.encode("ascii")
    for raw_line in original.splitlines():
        fields = raw_line.split(b"#", 1)[0].split()
        if len(fields) >= 2 and b"kafka" in fields[1:] and fields[0] != address_bytes:
            raise HostsConflictError
    if mapping.rstrip(b"\n") in original.splitlines():
        return original
    separator = b"" if not original or original.endswith(b"\n") else b"\n"
    return original + separator + mapping


def resolve_kafka_ip() -> str:
    try:
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{range .NetworkSettings.Networks}}{{println .IPAddress}}{{end}}",
                KAFKA_CONTAINER,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=INSPECT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise KafkaInspectError from error
    addresses = result.stdout.split()
    if result.returncode != 0 or len(addresses) != 1:
        raise KafkaInspectError
    try:
        return str(ipaddress.ip_address(addresses[0].decode("ascii")))
    except (UnicodeDecodeError, ValueError) as error:
        raise KafkaInspectError from error


def read_hosts(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise HostsReadError from error


def write_hosts(path: Path, content: bytes) -> None:
    if os.access(path, os.W_OK):
        try:
            path.write_bytes(content)
        except OSError as error:
            raise HostsWriteError from error
        return
    try:
        result = subprocess.run(
            ["sudo", "-n", "tee", "--", str(path)],
            input=content,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=SUDO_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HostsWriteError from error
    if result.returncode != 0:
        raise HostsWriteError


def run_with_kafka_host(command: Sequence[str], *, hosts_path: Path = HOSTS_PATH) -> int:
    original = read_hosts(hosts_path)
    updated = add_kafka_mapping(original, resolve_kafka_ip())
    restore_required = updated != original
    try:
        if restore_required:
            write_hosts(hosts_path, updated)
        environment = os.environ.copy()
        environment["DCIM_KAFKA_BOOTSTRAP"] = KAFKA_BOOTSTRAP
        try:
            result = subprocess.run(list(command), env=environment, check=False)
        except OSError as error:
            raise ChildLaunchError from error
        return result.returncode
    finally:
        if restore_required:
            write_hosts(hosts_path, original)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    if not arguments:
        error = CommandRequiredError()
        print(f"kafka-host: FAIL: {error}", file=sys.stderr)
        return 2
    try:
        return run_with_kafka_host(arguments)
    except KafkaHostError as error:
        print(f"kafka-host: FAIL: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("kafka-host: FAIL: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
