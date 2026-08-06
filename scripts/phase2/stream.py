"""Bounded Kafka consumer; it is the only streamed-event persistence owner.

Stream executions intentionally skip ``reconcile_execution`` because their
manifest contains no finite source list.  The in-memory ledger is the bounded
consumer's zero-silent-loss check.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import UTC, datetime
import importlib
import json
from pathlib import Path
import sys
import time
from typing import Final, Protocol, TypedDict

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pydantic import ValidationError

from contracts.python.dcim_contracts.envelope import Envelope, JsonValue

from scripts.phase2.execution import ExecutionContext, begin_execution
from scripts.phase2.kafka_producer import KafkaEnvelopeProducer, bootstrap_servers
from scripts.phase2.ledger import DispositionLedger, LedgerJSON
from scripts.phase2.manifest import RunManifest
from scripts.phase2.persist import PostgresClaimStore, QuarantineInput, persist_quarantine
from scripts.phase2.validate import DispositionEngine

NORMALIZED_TOPIC: Final = "dcim.normalized.events"
DLQ_TOPIC: Final = "dcim.dlq.synthetic"
DEFAULT_GROUP: Final = "dcim-phase2-persist"


class OffsetRange(TypedDict):
    first: int
    last: int


class ConsumerSummary(TypedDict, total=False):
    consumer_group: str
    topic: str
    offsets: dict[str, OffsetRange]
    ledger: LedgerJSON
    run_id: str
    count: int
    missing_reason_count: int


class KafkaMessage(Protocol):
    def error(self) -> object | None: ...
    def headers(self) -> list[tuple[str, str | bytes | None]] | None: ...
    def offset(self) -> int | None: ...
    def partition(self) -> int | None: ...
    def value(self) -> bytes | None: ...


class KafkaPartition(Protocol):
    offset: int
    partition: int


class KafkaConsumer(Protocol):
    def assign(self, partitions: list[object]) -> None: ...
    def assignment(self) -> list[KafkaPartition]: ...
    def close(self) -> None: ...
    def commit(self, message: KafkaMessage) -> None: ...
    def poll(self, timeout: float) -> KafkaMessage | None: ...
    def seek(self, partition: object) -> None: ...
    def subscribe(self, topics: list[str]) -> None: ...


def _new_consumer(group_id: str):
    """Construct the lazily imported non-auto-committing Kafka consumer."""
    driver = importlib.import_module("confluent_kafka")
    return driver.Consumer({
        "bootstrap.servers": bootstrap_servers(),
        "group.id": group_id,
        "enable.auto.commit": False,
        "auto.offset.reset": "earliest",
    })


def _topic_partition(topic: str, partition: int, offset: int):
    driver = importlib.import_module("confluent_kafka")
    return driver.TopicPartition(topic, partition, offset)


def _header(message: KafkaMessage, name: str) -> str | None:
    for key, value in message.headers() or []:
        if key == name:
            return value.decode("utf-8") if isinstance(value, bytes) else value
    return None


def _raw_candidate(value: bytes) -> Mapping[str, JsonValue]:
    decoded: JsonValue = json.loads(value.decode("utf-8"))
    if not isinstance(decoded, dict):
        return {}
    return decoded


def _stream_context(run_id: str) -> ExecutionContext:
    manifest = RunManifest(run_id, datetime.now(UTC).isoformat().replace("+00:00", "Z"), ())
    object.__setattr__(manifest, "manifest_sha256", f"stream:{run_id}")
    return begin_execution(manifest)


def _load_offsets(path: Path, ranges: bool) -> dict[int, int | tuple[int, int]]:
    raw: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("offset file must be a partition mapping")
    result: dict[int, int | tuple[int, int]] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise ValueError("offset partitions must be strings")
        partition = int(key)
        if ranges:
            if not isinstance(value, list) or len(value) != 2 or not all(isinstance(item, int) for item in value):
                raise ValueError("replay offsets must be inclusive [start, end] pairs")
            start, end = value
            if not isinstance(start, int) or not isinstance(end, int):
                raise ValueError("replay offsets must contain integers")
            result[partition] = (start, end)
        elif isinstance(value, int):
            result[partition] = value
        else:
            raise ValueError("start offsets must be integers")
    return result


def _seek(consumer: KafkaConsumer, topic: str, offsets: Mapping[int, int | tuple[int, int]], ranges: bool) -> None:
    assignments: list[object] = []
    for partition, boundary in offsets.items():
        if ranges:
            if not isinstance(boundary, tuple):
                raise ValueError("replay offsets must be ranges")
            start = boundary[0]
        else:
            if not isinstance(boundary, int):
                raise ValueError("start offsets must be integers")
            start = boundary
        assignments.append(_topic_partition(topic, partition, start))
    consumer.assign(assignments)


def _record_offset(offsets: dict[str, OffsetRange], message: KafkaMessage) -> None:
    partition_number = message.partition()
    offset = message.offset()
    if partition_number is None or offset is None:
        raise RuntimeError("Kafka message lacks partition or offset")
    partition = str(partition_number)
    previous = offsets.get(partition)
    if previous is None:
        offsets[partition] = {"first": offset, "last": offset}
    else:
        previous["last"] = offset


def _quarantine(context: ExecutionContext, message: KafkaMessage, candidate: Mapping[str, JsonValue], producer: KafkaEnvelopeProducer, detail: str) -> str:
    source_run_id = _header(message, "source_run_id")
    offset = message.offset()
    payload = message.value()
    if offset is None or payload is None:
        raise RuntimeError("Kafka message lacks offset or payload")
    reason = "schema_invalid" if source_run_id is not None else "missing_source_run_id"
    persist_quarantine(context, QuarantineInput(candidate=candidate, reason=reason, detail=detail), offset)
    if source_run_id is not None:
        producer.produce_envelope(DLQ_TOPIC, None, payload, {"source_run_id": source_run_id, "reason": reason, "detail": detail})
    return reason


def run_consumer(run_id: str, max_messages: int, idle_timeout_s: float, topic: str = NORMALIZED_TOPIC, group_id: str = DEFAULT_GROUP, count_only: bool = False, from_offsets: Path | None = None, start_offsets: Path | None = None) -> ConsumerSummary:
    """Drain a finite Kafka window, persisting each normal-mode disposition first."""
    if from_offsets is not None and start_offsets is not None:
        raise ValueError("offset contracts are mutually exclusive")
    if not count_only and topic != NORMALIZED_TOPIC:
        raise ValueError("normal mode only consumes normalized events")
    ranges = from_offsets is not None
    offsets_path = from_offsets if ranges else start_offsets
    selected_offsets = _load_offsets(offsets_path, ranges) if offsets_path is not None else {}
    effective_group = f"{group_id}-{run_id}-replay" if ranges else group_id
    consumer = _new_consumer(effective_group)
    context = None if count_only else _stream_context(run_id)
    producer = None if count_only else KafkaEnvelopeProducer()
    ledger = DispositionLedger()
    offsets: dict[str, OffsetRange] = {}
    count = 0
    missing_reason_count = 0
    idle_since = time.monotonic()
    if selected_offsets:
        _seek(consumer, topic, selected_offsets, ranges)
    else:
        consumer.subscribe([topic])
    completed_partitions: set[int] = set()
    try:
        while count < max_messages and time.monotonic() - idle_since < idle_timeout_s:
            message = consumer.poll(min(0.1, idle_timeout_s))
            if message is None:
                continue
            idle_since = time.monotonic()
            if message.error() is not None:
                raise RuntimeError("Kafka consumer returned message error")
            partition = message.partition()
            offset = message.offset()
            if partition is None or offset is None:
                raise RuntimeError("Kafka message lacks partition or offset")
            boundary = selected_offsets.get(partition)
            if ranges and (not isinstance(boundary, tuple) or offset > boundary[1]):
                if isinstance(boundary, tuple):
                    completed_partitions.add(partition)
                if completed_partitions == set(selected_offsets):
                    break
                continue
            if count_only:
                if not selected_offsets and _header(message, "source_run_id") != run_id:
                    continue
                if topic == DLQ_TOPIC and not _header(message, "reason"):
                    missing_reason_count += 1
                count += 1
                consumer.commit(message)
                _record_offset(offsets, message)
                continue
            ledger.record("received")
            candidate: Mapping[str, JsonValue] = {}
            try:
                payload = message.value()
                if payload is None:
                    raise RuntimeError("Kafka message lacks payload")
                candidate = _raw_candidate(payload)
                envelope = Envelope.model_validate(candidate, strict=True)
            except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
                if context is None or producer is None:
                    raise RuntimeError("normal consumer dependencies unavailable")
                _quarantine(context, message, candidate, producer, type(error).__name__)
                ledger.record("quarantined")
            else:
                if context is None:
                    raise RuntimeError("normal consumer context unavailable")
                store = PostgresClaimStore(context, envelope.model_dump(mode="json", round_trip=True), offset)
                disposition = DispositionEngine(store, DispositionLedger()).handle(envelope.model_dump(mode="json", round_trip=True))
                ledger.record(disposition.status)
            consumer.commit(message)
            count += 1
            _record_offset(offsets, message)
            if ranges and isinstance(boundary, tuple) and offset >= boundary[1]:
                completed_partitions.add(partition)
                if completed_partitions == set(selected_offsets):
                    break
    finally:
        consumer.close()
    if not count_only:
        ledger.assert_balanced()
    summary: ConsumerSummary = {"consumer_group": effective_group, "topic": topic, "offsets": offsets, "run_id": run_id}
    if count_only:
        summary["count"] = count
        summary["missing_reason_count"] = missing_reason_count
    else:
        summary["ledger"] = ledger.to_json()
    return summary


def capture_end_offsets(topic: str) -> dict[str, int]:
    """Return the current per-partition end watermark for latency harnesses."""
    consumer = _new_consumer(f"{DEFAULT_GROUP}-watermark")
    try:
        metadata = consumer.list_topics(topic, timeout=10.0)
        partitions = metadata.topics[topic].partitions
        return {
            str(partition): consumer.get_watermark_offsets(
                _topic_partition(topic, partition, 0), timeout=10.0
            )[1]
            for partition in partitions
        }
    finally:
        consumer.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--topic", default=NORMALIZED_TOPIC)
    parser.add_argument("--group-id", default=DEFAULT_GROUP)
    parser.add_argument("--count-only", action="store_true")
    parser.add_argument("--from-offsets", type=Path)
    parser.add_argument("--start-offsets", type=Path)
    parser.add_argument("--max-messages", required=True, type=int)
    parser.add_argument("--idle-timeout-seconds", required=True, type=float)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    print(json.dumps(run_consumer(arguments.run_id, arguments.max_messages, arguments.idle_timeout_seconds, arguments.topic, arguments.group_id, arguments.count_only, arguments.from_offsets, arguments.start_offsets), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
