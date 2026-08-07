#!/usr/bin/env python3
"""Provision and verify the bounded Phase 2 Development Kafka topics."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
from typing import Final


BOOTSTRAP_SERVER: Final = "localhost:9092"
RETENTION_MS: Final = "2592000000"
MAX_MESSAGE_BYTES: Final = "1048576"
KAFKA_TOPICS: Final = "/opt/kafka/bin/kafka-topics.sh"
KAFKA_CONFIGS: Final = "/opt/kafka/bin/kafka-configs.sh"
ROOT: Final = Path(__file__).resolve().parents[2]
COMPOSE_FILE: Final = ROOT / "deploy/compose/dev-build/compose.yaml"
COMMAND_TIMEOUT_SECONDS: Final = 60


@dataclass(frozen=True, slots=True)
class TopicSpec:
    """Desired topology and bounded storage settings for one topic."""

    name: str
    partitions: int
    replication_factor: int
    retention_ms: str
    max_message_bytes: str


@dataclass(frozen=True, slots=True)
class TopicDescription:
    """Parsed fields from one Kafka topic summary line."""

    name: str
    partitions: int
    replication_factor: int
    configs: tuple[tuple[str, str], ...]


TOPIC_SPECS: Final = tuple(
    TopicSpec(
        name=name,
        partitions=1,
        replication_factor=1,
        retention_ms=RETENTION_MS,
        max_message_bytes=MAX_MESSAGE_BYTES,
    )
    for name in (
        "dcim.raw.synthetic",
        "dcim.normalized.events",
        "dcim.enriched.events",
        "dcim.dlq.synthetic",
    )
)


def parse_topic_descriptions(output: str) -> tuple[TopicDescription, ...]:
    """Parse Kafka summary lines without invoking Docker or Kafka."""
    descriptions: list[TopicDescription] = []
    for line in output.splitlines():
        if "PartitionCount:" not in line or "ReplicationFactor:" not in line:
            continue
        fields = {
            key.strip(): value.strip()
            for segment in line.split("\t")
            if ":" in segment
            for key, value in (segment.split(":", 1),)
        }
        config_pairs = tuple(
            (key.strip(), value.strip())
            for item in fields.get("Configs", "").split(",")
            if "=" in item
            for key, value in (item.split("=", 1),)
        )
        try:
            descriptions.append(
                TopicDescription(
                    name=fields["Topic"],
                    partitions=int(fields["PartitionCount"]),
                    replication_factor=int(fields["ReplicationFactor"]),
                    configs=config_pairs,
                )
            )
        except (KeyError, ValueError):
            continue
    return tuple(descriptions)


def validate_topic_descriptions(
    descriptions: tuple[TopicDescription, ...],
) -> tuple[str, ...]:
    """Return every difference from the exact four-topic contract."""
    errors: list[str] = []
    expected = {spec.name: spec for spec in TOPIC_SPECS}
    actual: dict[str, TopicDescription] = {}
    for description in descriptions:
        if description.name in actual:
            errors.append(f"duplicate topic description: {description.name}")
        actual[description.name] = description
    for name in sorted(expected.keys() - actual.keys()):
        errors.append(f"missing topic description: {name}")
    for name in sorted(actual.keys() - expected.keys()):
        errors.append(f"unexpected topic description: {name}")
    for name in sorted(expected.keys() & actual.keys()):
        spec = expected[name]
        description = actual[name]
        configs = dict(description.configs)
        if description.partitions != spec.partitions:
            errors.append(
                f"{name}: partitions={description.partitions}, expected {spec.partitions}"
            )
        if description.replication_factor != spec.replication_factor:
            errors.append(
                f"{name}: replication factor={description.replication_factor}, "
                f"expected {spec.replication_factor}"
            )
        for key, wanted in (
            ("retention.ms", spec.retention_ms),
            ("max.message.bytes", spec.max_message_bytes),
        ):
            observed = configs.get(key)
            if observed != wanted:
                errors.append(f"{name}: {key}={observed!r}, expected {wanted}")
    return tuple(errors)


def kafka_command(executable: str, *arguments: str) -> list[str]:
    """Build an isolated Development Compose Kafka CLI command."""
    runtime_root = Path(
        os.environ.get(
            "DCIM_RUNTIME_ROOT",
            Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
            / "dcim-core-platform/runtime",
        )
    )
    return [
        "docker",
        "compose",
        "--env-file",
        str(runtime_root / "dev-build/runtime.env"),
        "--env-file",
        str(runtime_root / "dev-build/images.env"),
        "-f",
        str(COMPOSE_FILE),
        "--profile",
        "data",
        "--project-name",
        "dcim-build",
        "exec",
        "-T",
        "kafka",
        executable,
        "--bootstrap-server",
        BOOTSTRAP_SERVER,
        *arguments,
    ]


def run_kafka(executable: str, *arguments: str) -> str:
    """Run one Kafka CLI operation and return its standard output."""
    completed = subprocess.run(
        kafka_command(executable, *arguments),
        check=True,
        capture_output=True,
        text=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    return completed.stdout


def provision() -> None:
    """Create missing topics and restore exact configs on existing topics."""
    for spec in TOPIC_SPECS:
        run_kafka(
            KAFKA_TOPICS,
            "--create",
            "--if-not-exists",
            "--topic",
            spec.name,
            "--partitions",
            str(spec.partitions),
            "--replication-factor",
            str(spec.replication_factor),
            "--config",
            f"retention.ms={spec.retention_ms}",
            "--config",
            f"max.message.bytes={spec.max_message_bytes}",
        )
        run_kafka(
            KAFKA_CONFIGS,
            "--alter",
            "--entity-type",
            "topics",
            "--entity-name",
            spec.name,
            "--add-config",
            (
                f"retention.ms={spec.retention_ms},"
                f"max.message.bytes={spec.max_message_bytes}"
            ),
        )


def verify() -> tuple[str, ...]:
    """Describe every approved topic and return contract differences."""
    output = "\n".join(
        run_kafka(KAFKA_TOPICS, "--describe", "--topic", spec.name)
        for spec in TOPIC_SPECS
    )
    return validate_topic_descriptions(parse_topic_descriptions(output))


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    """Parse the single verification mode switch."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="describe all four topics and assert topology and configs",
    )
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    """Provision by default, or verify without mutation."""
    options = parse_args(arguments)
    try:
        if options.verify:
            errors = verify()
            if errors:
                for error in errors:
                    print(error, file=sys.stderr)
                return 1
        else:
            provision()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print("Kafka topic command failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
