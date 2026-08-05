from __future__ import annotations

import json
import sys
import tempfile
from typing import Protocol
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase2 import stream
from scripts.phase2.execution import ExecutionContext


class SeekTarget(Protocol):
    def offset(self) -> int: ...


class FakeMessage:
    def __init__(self, offset: int, value: bytes, headers: list[tuple[str, str]]) -> None:
        self._offset = offset
        self._value = value
        self._headers = headers

    def error(self) -> None:
        return None

    def offset(self) -> int:
        return self._offset

    def partition(self) -> int:
        return 0

    def value(self) -> bytes:
        return self._value

    def headers(self) -> list[tuple[str, str]]:
        return self._headers


class FakeConsumer:
    def __init__(self, messages: list[FakeMessage]) -> None:
        self.messages = messages
        self.committed: list[int] = []
        self.seeks: list[int] = []
        self.topics: list[str] = []

    def subscribe(self, topics: list[str]) -> None:
        self.topics = topics

    def poll(self, timeout: float) -> FakeMessage | None:
        return self.messages.pop(0) if self.messages else None

    def commit(self, message: FakeMessage) -> None:
        self.committed.append(message.offset())

    def seek(self, partition: SeekTarget) -> None:
        self.seeks.append(partition.offset())

    def assignment(self) -> list[object]:
        return []

    def close(self) -> None:
        return None


class FakeProducer:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def produce_envelope(self, topic: str, key: str | None, value: bytes, headers: dict[str, str]) -> None:
        self.calls.append(f"dlq:{headers['reason']}")


class Offset:
    def __init__(self, offset: int) -> None:
        self._offset = offset

    def offset(self) -> int:
        return self._offset


class FakeStore:
    def __init__(self, calls: list[str], result: str = "new", *_: object) -> None:
        self.calls = calls
        self.result = result

    def try_claim(self, event_id: str, content_sha256: str) -> str:
        self.calls.append("claim")
        return self.result


class StreamConsumerTests(unittest.TestCase):
    def test_consumer_persists_before_each_offset_commit(self) -> None:
        # Given: one valid normalized event followed by one malformed event.
        valid = (ROOT / "fixtures/synthetic/events/p1-redfish-health.json").read_bytes()
        consumer = FakeConsumer([
            FakeMessage(7, valid, [("source_run_id", "run-7")]),
            FakeMessage(8, b"{", [("source_run_id", "run-7")]),
        ])
        calls: list[str] = []

        # When: the bounded consumer drains both records.
        with (
            patch.object(stream, "_new_consumer", return_value=consumer),
            patch.object(stream, "begin_execution", return_value=ExecutionContext("run-7", "2026-08-05T00:00:00Z", 1)),
            patch.object(stream, "PostgresClaimStore", lambda *_args: FakeStore(calls)),
            patch.object(stream, "persist_quarantine", side_effect=lambda *args: calls.append("quarantine")),
            patch.object(stream, "KafkaEnvelopeProducer", return_value=FakeProducer(calls)),
        ):
            summary = stream.run_consumer("run-7", 2, 0.01)

        # Then: durable claim/quarantine precede their respective commits; DLQ follows quarantine.
        self.assertEqual(consumer.committed, [7, 8])
        self.assertEqual(calls, ["claim", "quarantine", "dlq:schema_invalid"])
        self.assertEqual(summary.get("ledger"), {"received": 2, "accepted": 1, "quarantined": 1, "duplicate": 0})
        self.assertEqual(summary.get("offsets"), {"0": {"first": 7, "last": 8}})

    def test_consumer_leaves_offset_uncommitted_when_quarantine_fails(self) -> None:
        # Given: a malformed record and a failed durable quarantine transaction.
        consumer = FakeConsumer([FakeMessage(9, b"{", [("source_run_id", "run-7")])])
        with (
            patch.object(stream, "_new_consumer", return_value=consumer),
            patch.object(stream, "begin_execution", return_value=ExecutionContext("run-7", "2026-08-05T00:00:00Z", 1)),
            patch.object(stream, "persist_quarantine", side_effect=RuntimeError("database unavailable")),
            patch.object(stream, "KafkaEnvelopeProducer") as producer,
        ):
            # When/Then: the failure escapes before DLQ or offset commit.
            with self.assertRaises(RuntimeError):
                stream.run_consumer("run-7", 1, 0.01)
        self.assertEqual(consumer.committed, [])
        producer.return_value.produce_envelope.assert_not_called()

    def test_count_only_filters_foreign_run_without_persisting(self) -> None:
        # Given: one foreign and one selected record without an explicit offset window.
        consumer = FakeConsumer([
            FakeMessage(1, b"foreign", [("source_run_id", "other-run")]),
            FakeMessage(2, b"selected", [("source_run_id", "run-7")]),
        ])
        # When: count-only mode drains the bounded input.
        with patch.object(stream, "_new_consumer", return_value=consumer):
            summary = stream.run_consumer("run-7", 2, 0.01, count_only=True)
        # Then: only the selected immutable source-run header is counted and committed.
        self.assertEqual(summary.get("count"), 1)
        self.assertEqual(consumer.committed, [2])

    def test_consumer_leaves_offset_uncommitted_when_dlq_delivery_fails(self) -> None:
        # Given: a malformed record whose durable quarantine succeeds.
        consumer = FakeConsumer([FakeMessage(10, b"{", [("source_run_id", "run-7")])])
        with (
            patch.object(stream, "_new_consumer", return_value=consumer),
            patch.object(stream, "begin_execution", return_value=ExecutionContext("run-7", "2026-08-05T00:00:00Z", 1)),
            patch.object(stream, "persist_quarantine"),
            patch.object(stream, "KafkaEnvelopeProducer") as producer,
        ):
            producer.return_value.produce_envelope.side_effect = RuntimeError("dlq unavailable")

            # When / Then: the DLQ failure exits without an offset commit.
            with self.assertRaisesRegex(RuntimeError, "dlq unavailable"):
                stream.run_consumer("run-7", 1, 0.01)
        self.assertEqual(consumer.committed, [])

    def test_from_offsets_replays_exact_window_as_duplicates(self) -> None:
        # Given: an inclusive replay window and valid records inside and beyond it.
        valid = (ROOT / "fixtures/synthetic/events/p1-redfish-health.json").read_bytes()
        consumer = FakeConsumer([
            FakeMessage(4, valid, [("source_run_id", "run-7")]),
            FakeMessage(5, valid, [("source_run_id", "run-7")]),
            FakeMessage(6, valid, [("source_run_id", "run-7")]),
        ])
        with self.subTest("replay"):
            with tempfile.TemporaryDirectory() as directory:
                offsets = Path(directory) / "offsets.json"
                offsets.write_text(json.dumps({"0": [4, 5]}), encoding="utf-8")
                with (
                    patch.object(stream, "_new_consumer", return_value=consumer),
                    patch.object(stream, "_topic_partition", side_effect=lambda _topic, _partition, offset: Offset(offset)),
                    patch.object(stream, "begin_execution", return_value=ExecutionContext("run-7", "2026-08-05T00:00:00Z", 1)),
                    patch.object(stream, "PostgresClaimStore", lambda *_args: FakeStore([], "duplicate")),
                    patch.object(stream, "KafkaEnvelopeProducer"),
                ):
                    # When: the explicit offset range is drained.
                    summary = stream.run_consumer("run-7", 3, 0.01, from_offsets=offsets)

        # Then: the consumer seeks exactly to the start and records duplicate dispositions only.
        self.assertEqual(consumer.seeks, [4])
        self.assertEqual(consumer.committed, [4, 5])
        self.assertEqual(summary.get("ledger"), {"received": 2, "accepted": 0, "quarantined": 0, "duplicate": 2})

    def test_start_offsets_seeks_start_and_drains_until_idle(self) -> None:
        # Given: a starting position and two matching count-only records.
        consumer = FakeConsumer([
            FakeMessage(11, b"one", [("source_run_id", "run-7")]),
            FakeMessage(12, b"two", [("source_run_id", "run-7")]),
        ])
        with tempfile.TemporaryDirectory() as directory:
            offsets = Path(directory) / "offsets.json"
            offsets.write_text(json.dumps({"0": 11}), encoding="utf-8")
            with (
                patch.object(stream, "_new_consumer", return_value=consumer),
                patch.object(stream, "_topic_partition", side_effect=lambda _topic, _partition, offset: Offset(offset)),
            ):
                # When: the start-offset contract drains until the input becomes idle.
                summary = stream.run_consumer("run-7", 3, 0.001, count_only=True, start_offsets=offsets)

        # Then: the requested start is sought and both available messages are committed.
        self.assertEqual(consumer.seeks, [11])
        self.assertEqual(summary.get("count"), 2)
        self.assertEqual(consumer.committed, [11, 12])

    def test_missing_source_run_id_quarantines_without_dlq(self) -> None:
        # Given: malformed data without the source-run lineage header.
        consumer = FakeConsumer([FakeMessage(13, b"{", [])])
        calls: list[str] = []
        with (
            patch.object(stream, "_new_consumer", return_value=consumer),
            patch.object(stream, "begin_execution", return_value=ExecutionContext("run-7", "2026-08-05T00:00:00Z", 1)),
            patch.object(stream, "persist_quarantine", side_effect=lambda *_args: calls.append("missing_source_run_id")),
            patch.object(stream, "KafkaEnvelopeProducer", return_value=FakeProducer(calls)),
        ):
            # When: the bounded consumer receives the unlineaged invalid record.
            summary = stream.run_consumer("run-7", 1, 0.01)

        # Then: it is durably quarantined but never copied into the DLQ.
        self.assertEqual(calls, ["missing_source_run_id"])
        self.assertEqual(consumer.committed, [13])
        self.assertEqual(summary.get("ledger"), {"received": 1, "accepted": 0, "quarantined": 1, "duplicate": 0})


if __name__ == "__main__":
    unittest.main()
