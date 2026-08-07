from __future__ import annotations

import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase2 import kafka_producer
from scripts.phase2 import run as pipeline
from scripts.phase2.errors import KafkaPublishError
from scripts.phase2.execution import ExecutionContext


FIXTURES = ROOT / "fixtures" / "synthetic" / "events"
FIXED_CLOCK = "2026-07-30T00:00:00Z"
VALID_FIXTURES = (
    "p1-redfish-health.json",
    "p1-ups-alarm.json",
    "p2-network-utilization.json",
)
# Captured from the pre-stream batch pipeline (git main) with the claim store
# faked to "new" and reconciliation returning the six accepted counts. The
# manifest digest is fixture-derived and therefore stable.
BATCH_BASELINE_STDOUT = (
    '{"counts":{"accepted":6,"duplicate":0,"quarantined":0,"received":6},'
    '"durability_guarantee":"durable per input from the moment its '
    "disposition transaction is acknowledged; loss before that point is "
    "detectable by reconciling manifest source_count against persisted "
    'dispositions per execution (scripts/phase2/reconcile.py)",'
    '"execution_sequence":1,'
    '"manifest_sha256":'
    '"f8cf622c98036aa7793f6bd4597ae67f31b414844f166fe0bb53f5e733611153",'
    '"reconciled":true,"run_id":"batch-freeze-baseline"}\n'
)


class FakeStreamProducer:
    """Records every publish the stream branch performs."""

    instances: list[FakeStreamProducer] = []

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.calls: list[dict[str, object]] = []
        self.flushes: list[float] = []
        FakeStreamProducer.instances.append(self)

    def produce_envelope(
        self,
        topic: str,
        key: str | None,
        value: bytes,
        headers: dict[str, str],
    ) -> None:
        self.calls.append(
            {
                "topic": topic,
                "key": key,
                "value": value,
                "headers": dict(headers),
            }
        )

    def flush(self, timeout: float) -> None:
        self.flushes.append(timeout)


class FakeDriver:
    """Scriptable stand-in for the confluent_kafka Producer surface."""

    def __init__(self) -> None:
        self.produced: list[dict[str, object]] = []
        self.flush_returns: list[int] = [0]
        self.delivery: tuple[object, object] | None = None
        self.raise_on_produce: BaseException | None = None
        self._callback = None

    def produce(self, topic: str, **kwargs: object) -> None:
        if self.raise_on_produce is not None:
            raise self.raise_on_produce
        self.produced.append({"topic": topic, **kwargs})
        self._callback = kwargs.get("on_delivery")

    def flush(self, timeout: float) -> int:
        if self.delivery is not None and self._callback is not None:
            error, message = self.delivery
            self._callback(error, message)
        if self.flush_returns:
            return self.flush_returns.pop(0)
        return 0


class FakeClaimStore:
    def __init__(self, context: object, candidate: object, ordinal: int) -> None:
        self.candidate = candidate

    def try_claim(self, event_id: str, content_sha256: str) -> str:
        return "new"


def build_stream_fixtures(directory: Path) -> None:
    """Create three valid and two invalid synthetic stream inputs."""
    for name in VALID_FIXTURES:
        shutil.copy(FIXTURES / name, directory / name)
    (directory / "bad-envelope.json").write_text(
        json.dumps({"schema_version": "0.1.0", "event_id": "not-a-uuid"}),
        encoding="utf-8",
    )
    (directory / "bad-json-syntax.json").write_text("{not json", encoding="utf-8")


class StreamModeTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeStreamProducer.instances = []
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.fixtures_dir = Path(self.temporary_directory.name)
        build_stream_fixtures(self.fixtures_dir)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_stream(self, run_id: str = "stream-test-run") -> tuple[int, str]:
        stdout = io.StringIO()
        with (
            patch(
                "scripts.phase2.kafka_producer.KafkaEnvelopeProducer",
                FakeStreamProducer,
            ),
            redirect_stdout(stdout),
        ):
            exit_code = pipeline.run(
                [
                    "--run-id",
                    run_id,
                    "--fixtures-dir",
                    str(self.fixtures_dir),
                    "--fixed-clock",
                    FIXED_CLOCK,
                    "--mode",
                    "stream",
                ]
            )
        return exit_code, stdout.getvalue()

    def test_stream_publishes_valid_and_dlq_with_required_headers(self) -> None:
        # Given: three valid fixtures and two invalid fixtures.

        # When: the pipeline runs in stream mode.
        exit_code, output = self.run_stream()

        # Then: the ledger summary is the only stdout contract.
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(output), {"received": 5, "published": 3, "dlq": 2}
        )
        self.assertEqual(len(FakeStreamProducer.instances), 1)
        producer = FakeStreamProducer.instances[0]
        normalized = [
            call
            for call in producer.calls
            if call["topic"] == "dcim.normalized.events"
        ]
        dlq = [
            call
            for call in producer.calls
            if call["topic"] == "dcim.dlq.synthetic"
        ]
        self.assertEqual(len(normalized), 3)
        self.assertEqual(len(dlq), 2)

        # Sorted fixture order: bad-envelope(0), bad-json-syntax(1), then the
        # three valid fixtures at ordinals 2, 3, 4.
        envelopes = [
            json.loads(call["value"].decode("utf-8")) for call in normalized
        ]
        for call, envelope, ordinal in zip(normalized, envelopes, ("2", "3", "4")):
            self.assertEqual(call["key"], envelope["event_id"])
            self.assertEqual(
                call["headers"],
                {
                    "schema_version": "0.1.0",
                    "source_run_id": "stream-test-run",
                    "input_ordinal": ordinal,
                },
            )

        for call, fixture_name in zip(
            dlq, ("bad-envelope.json", "bad-json-syntax.json")
        ):
            self.assertIsNone(call["key"])
            headers = call["headers"]
            self.assertEqual(headers["reason"], "schema_invalid")
            self.assertTrue(headers["detail"])
            self.assertEqual(headers["source_fixture"], fixture_name)
            self.assertEqual(headers["source_run_id"], "stream-test-run")
            self.assertEqual(
                call["value"],
                (self.fixtures_dir / fixture_name).read_bytes(),
            )
        self.assertEqual(producer.flushes, [30.0])

    def test_stream_payload_invalid_reason_matches_batch_vocabulary(self) -> None:
        # Given: a fixture whose payload violates its event type contract.
        (self.fixtures_dir / "bad-envelope.json").unlink()
        (self.fixtures_dir / "bad-json-syntax.json").unlink()
        broken = json.loads((FIXTURES / "p1-redfish-health.json").read_text())
        broken["payload"] = {"health": "Warning"}
        (self.fixtures_dir / "zz-bad-payload.json").write_text(
            json.dumps(broken), encoding="utf-8"
        )
        for name in VALID_FIXTURES:
            (self.fixtures_dir / name).unlink()

        # When: the pipeline runs in stream mode.
        exit_code, output = self.run_stream()

        # Then: the DLQ reason uses the batch quarantine vocabulary.
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(output), {"received": 1, "published": 0, "dlq": 1}
        )
        dlq = FakeStreamProducer.instances[0].calls[0]
        self.assertEqual(dlq["topic"], "dcim.dlq.synthetic")
        self.assertEqual(dlq["headers"]["reason"], "payload_invalid")
        self.assertEqual(dlq["headers"]["detail"], "payload_invalid")

    def test_stream_never_invokes_database_or_manifest_write(self) -> None:
        # Given: every database boundary of the batch path is trip-wired.
        with (
            patch("scripts.phase2.run.begin_execution") as begin_execution,
            patch("scripts.phase2.run.PostgresClaimStore") as claim_store,
            patch("scripts.phase2.run.persist_quarantine") as quarantine,
            patch("scripts.phase2.run.reconcile_execution") as reconcile,
            patch(
                "scripts.phase2.db.psql",
                side_effect=AssertionError("psql invoked in stream mode"),
            ),
            patch(
                "scripts.phase2.kafka_producer.KafkaEnvelopeProducer",
                FakeStreamProducer,
            ),
        ):
            # When: the pipeline runs in stream mode.
            exit_code, _ = self.run_stream()

        # Then: no batch persistence seam was touched.
        self.assertEqual(exit_code, 0)
        begin_execution.assert_not_called()
        claim_store.assert_not_called()
        quarantine.assert_not_called()
        reconcile.assert_not_called()

    def test_batch_mode_imports_no_confluent_kafka(self) -> None:
        # Given: an import hook that fails any confluent_kafka import.
        script = (
            "import sys\n"
            "class Blocker:\n"
            "    def find_module(self, name, path=None):\n"
            "        if name.split('.')[0] == 'confluent_kafka':\n"
            "            raise AssertionError('confluent_kafka imported')\n"
            "sys.meta_path.insert(0, Blocker())\n"
            "from scripts.phase2 import run\n"
            "args = run._parser().parse_args([\n"
            "    '--run-id', 'x', '--fixtures-dir', '.',\n"
            "    '--fixed-clock', '2026-07-30T00:00:00Z',\n"
            "])\n"
            "assert args.mode == 'batch', args.mode\n"
            "raise SystemExit(1 if 'confluent_kafka' in sys.modules else 0)\n"
        )

        # When: the run module is imported and batch mode parsed.
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        # Then: batch is the default and confluent_kafka was never imported.
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_batch_stdout_is_byte_identical_to_baseline(self) -> None:
        # Given: the batch database seams faked to their happy-path behavior.
        context = ExecutionContext(
            run_id="batch-freeze-baseline",
            fixed_clock=FIXED_CLOCK,
            execution_sequence=1,
        )
        counts = {"received": 6, "accepted": 6, "quarantined": 0, "duplicate": 0}
        stdout = io.StringIO()

        # When: the batch pipeline runs over the standard fixtures.
        with (
            patch("scripts.phase2.run.begin_execution", return_value=context),
            patch("scripts.phase2.run.PostgresClaimStore", FakeClaimStore),
            patch("scripts.phase2.run.reconcile_execution", return_value=counts),
            redirect_stdout(stdout),
        ):
            exit_code = pipeline.run(
                [
                    "--run-id",
                    "batch-freeze-baseline",
                    "--fixtures-dir",
                    str(FIXTURES),
                    "--fixed-clock",
                    FIXED_CLOCK,
                ]
            )

        # Then: stdout is byte-identical to the pre-stream baseline.
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), BATCH_BASELINE_STDOUT)


class KafkaEnvelopeProducerTests(unittest.TestCase):
    def test_constructor_passes_exact_config_and_env_bootstrap(self) -> None:
        # Given: a fake confluent_kafka module and a broker override.
        created: list[dict[str, object]] = []

        class FakeProducerClass:
            def __init__(self, config: dict[str, object]) -> None:
                created.append(config)

            def produce(self, topic: str, **kwargs: object) -> None:
                return None

            def flush(self, timeout: float) -> int:
                return 0

        fake_module = types.SimpleNamespace(Producer=FakeProducerClass)
        with (
            patch.dict(sys.modules, {"confluent_kafka": fake_module}),
            patch.dict(
                os.environ, {"DCIM_KAFKA_BOOTSTRAP": "synthetic-broker:19092"}
            ),
        ):
            # When: the producer is constructed without a driver.
            kafka_producer.KafkaEnvelopeProducer()

        # Then: the exact pinned config reached the driver constructor.
        self.assertEqual(
            created,
            [
                {
                    "bootstrap.servers": "synthetic-broker:19092",
                    "acks": "all",
                    "enable.idempotence": True,
                    "retries": 3,
                    "message.max.bytes": 1048576,
                }
            ],
        )

    def test_constructor_defaults_bootstrap_to_compose_broker(self) -> None:
        # Given: no broker override in the environment.
        created: list[dict[str, object]] = []

        class FakeProducerClass:
            def __init__(self, config: dict[str, object]) -> None:
                created.append(config)

            def produce(self, topic: str, **kwargs: object) -> None:
                return None

            def flush(self, timeout: float) -> int:
                return 0

        fake_module = types.SimpleNamespace(Producer=FakeProducerClass)
        with (
            patch.dict(sys.modules, {"confluent_kafka": fake_module}),
            patch.dict(os.environ, {}, clear=True),
        ):
            kafka_producer.KafkaEnvelopeProducer()

        # Then
        self.assertEqual(created[0]["bootstrap.servers"], "kafka:9092")

    def test_produce_envelope_delivers_with_headers(self) -> None:
        # Given: a driver that delivers successfully.
        driver = FakeDriver()
        producer = kafka_producer.KafkaEnvelopeProducer(driver=driver)

        # When
        producer.produce_envelope(
            topic="dcim.normalized.events",
            key="event-1",
            value=b"{}",
            headers={"source_run_id": "run-1"},
        )

        # Then
        self.assertEqual(driver.produced[0]["topic"], "dcim.normalized.events")
        self.assertEqual(driver.produced[0]["key"], "event-1")
        self.assertEqual(
            driver.produced[0]["headers"], {"source_run_id": "run-1"}
        )

    def test_delivery_callback_error_raises_publish_error(self) -> None:
        # Given: a driver whose delivery callback reports a broker error.
        driver = FakeDriver()
        driver.delivery = (RuntimeError("synthetic broker failure"), None)
        producer = kafka_producer.KafkaEnvelopeProducer(driver=driver)

        # When / Then
        with self.assertRaises(KafkaPublishError) as raised:
            producer.produce_envelope("dcim.normalized.events", "k", b"v", {})
        self.assertEqual(
            str(raised.exception),
            "delivery to topic dcim.normalized.events failed with "
            "1 broker-reported error(s)",
        )
        self.assertNotIn("synthetic broker failure", str(raised.exception))

    def test_delivery_callback_message_error_raises_publish_error(self) -> None:
        # Given: a delivery callback whose message carries the error.
        driver = FakeDriver()

        class FakeMessage:
            def error(self) -> object:
                return RuntimeError("synthetic message failure")

        driver.delivery = (None, FakeMessage())
        producer = kafka_producer.KafkaEnvelopeProducer(driver=driver)

        # When / Then
        with self.assertRaises(KafkaPublishError) as raised:
            producer.produce_envelope("dcim.dlq.synthetic", None, b"v", {})
        self.assertEqual(
            str(raised.exception),
            "delivery to topic dcim.dlq.synthetic failed with "
            "1 broker-reported error(s)",
        )
        self.assertNotIn("synthetic message failure", str(raised.exception))

    def test_flush_timeout_with_pending_messages_raises(self) -> None:
        # Given: a driver that never drains its queue.
        driver = FakeDriver()
        driver.flush_returns = [2]
        producer = kafka_producer.KafkaEnvelopeProducer(driver=driver)

        # When / Then
        with self.assertRaisesRegex(KafkaPublishError, "timed out"):
            producer.produce_envelope("dcim.normalized.events", "k", b"v", {})

    def test_full_local_queue_raises_publish_error(self) -> None:
        # Given: a driver whose local queue is full.
        driver = FakeDriver()
        driver.raise_on_produce = BufferError("queue full")
        producer = kafka_producer.KafkaEnvelopeProducer(driver=driver)

        # When / Then
        with self.assertRaisesRegex(KafkaPublishError, "queue is full"):
            producer.produce_envelope("dcim.normalized.events", "k", b"v", {})

    def test_flush_with_pending_messages_raises(self) -> None:
        # Given: a driver with outstanding messages at drain time.
        driver = FakeDriver()
        driver.flush_returns = [1]
        producer = kafka_producer.KafkaEnvelopeProducer(driver=driver)

        # When / Then
        with self.assertRaisesRegex(KafkaPublishError, "pending"):
            producer.flush(1.0)


if __name__ == "__main__":
    unittest.main()
