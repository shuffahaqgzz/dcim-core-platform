#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.9.2"]
# ///

# ─── How to run ───
# Run: python3 scripts/phase2/latency.py --leg direct --output latency.json
# Kafka requires the separately delivered producer and bounded-consumer seams.
# ──────────────────
"""Measure synthetic P1 persistence and synchronous NOC visibility intervals."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import random
import sys
from threading import Event
import time
from typing import assert_never, Final, Literal, Protocol, TypedDict
import uuid


ROOT: Final = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase2 import db, kafka_producer, noc, stream  # noqa: E402
from scripts.phase2.stream import ConsumerSummary  # noqa: E402


TOPIC: Final = "dcim.normalized.events"
FIXTURE_NAME: Final = "p1-redfish-health.json"
P95_LIMIT_NS: Final = 5_000_000_000
POLL_INTERVAL_SECONDS: Final = 0.05
EPOCH: Final = datetime(1970, 1, 1, tzinfo=UTC)


class LatencyError(RuntimeError):
    """The latency run could not produce a valid measurement."""


class LatencyThresholdError(LatencyError):
    """The dashboard p95 did not remain strictly below five seconds."""


class KafkaIntegrationError(LatencyError):
    """The separately delivered Kafka integration seam is unavailable."""


class ProducerSeam(Protocol):
    def produce_envelope(self, topic: str, key: str, value: bytes, headers: Mapping[str, str]) -> None: ...
    def flush(self, timeout: int) -> None: ...


class StreamSeam(Protocol):
    def capture_end_offsets(self, topic: str) -> dict[str, int]: ...
    def run_consumer(self, run_id: str, max_messages: int, idle_timeout_s: int, *, topic: str, start_offsets: Path) -> ConsumerSummary: ...


class LatencyDistribution(TypedDict):
    p50: int
    p95: int
    max: int


class LatencySample(TypedDict):
    event_id: str
    persist_latency_ns: int
    dashboard_latency_ns: int


class LatencyReport(TypedDict):
    sample_count: int
    seed: int
    fixture_source: str
    workload_class: str
    test_window: str
    clock_source: str
    percentile_method: str
    exclusions: list[str]
    persist_latency_ns: LatencyDistribution
    dashboard_latency_ns: LatencyDistribution
    samples: list[LatencySample]


@dataclass(frozen=True, slots=True)
class InjectedEvent:
    envelope: db.JsonObject
    t_injected_ns: int
    seed: int
    fixture_source: str


@dataclass(frozen=True, slots=True)
class Timing:
    event_id: str
    t_injected_ns: int
    t_persisted_ns: int
    t_dashboard_visible_ns: int


def _utc_timestamp(timestamp_ns: int) -> str:
    seconds, remainder_ns = divmod(timestamp_ns, 1_000_000_000)
    value = EPOCH + timedelta(seconds=seconds, microseconds=remainder_ns // 1_000)
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def generate(count: int, seed: int, fixtures_dir: Path, *, clock_ns: Callable[[], int] = time.time_ns) -> Iterator[InjectedEvent]:
    """Yield seeded unique fixture clones, stamping each immediately on injection."""
    from contracts.python.dcim_contracts.envelope import Envelope

    if count < 1:
        raise LatencyError("count must be positive")
    fixture = fixtures_dir / FIXTURE_NAME
    try:
        source = json.loads(fixture.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LatencyError("synthetic P1 fixture is unavailable") from error
    rng = random.Random(seed)
    for _ in range(count):
        injected = clock_ns()
        candidate = dict(source)
        candidate["event_id"] = str(uuid.UUID(int=rng.getrandbits(128)))
        candidate["occurred_at"] = _utc_timestamp(injected)
        candidate["observed_at"] = candidate["occurred_at"]
        canonical = Envelope.model_validate(candidate, strict=True).model_dump(mode="json", round_trip=True)
        yield InjectedEvent(canonical, injected, seed, fixture.name)


def nearest_rank(samples: Sequence[int], percentile: int) -> int:
    """Return the integer nearest-rank percentile for non-empty samples."""
    if not samples or percentile < 1 or percentile > 100:
        raise LatencyError("nearest-rank inputs are outside the supported range")
    ordered = sorted(samples)
    rank = (percentile * len(ordered) + 99) // 100
    return ordered[rank - 1]


def report(timings: Sequence[Timing], *, seed: int) -> LatencyReport:
    """Build an interval-only report with baseline measurement context."""
    if not timings:
        raise LatencyError("at least one timing sample is required")
    samples: list[LatencySample] = [
        {
            "event_id": item.event_id,
            "persist_latency_ns": item.t_persisted_ns - item.t_injected_ns,
            "dashboard_latency_ns": item.t_dashboard_visible_ns - item.t_injected_ns,
        }
        for item in timings
    ]
    persist = [item["persist_latency_ns"] for item in samples]
    dashboard = [item["dashboard_latency_ns"] for item in samples]

    def distribution(values: Sequence[int]) -> LatencyDistribution:
        return {"p50": nearest_rank(values, 50), "p95": nearest_rank(values, 95), "max": max(values)}

    return {
        "sample_count": len(samples),
        "seed": seed,
        "fixture_source": FIXTURE_NAME,
        "workload_class": "event/trap (P1)",
        "test_window": "first injection through synchronous NOC materialization",
        "clock_source": "time.time_ns",
        "percentile_method": "nearest-rank",
        "exclusions": ["polling feeds (<30 second class)"],
        "persist_latency_ns": distribution(persist),
        "dashboard_latency_ns": distribution(dashboard),
        "samples": samples,
    }


def assert_dashboard_latency(result: LatencyReport) -> None:
    """Enforce the strict event/trap dashboard p95 threshold."""
    p95 = result["dashboard_latency_ns"]["p95"]
    if p95 >= P95_LIMIT_NS:
        raise LatencyThresholdError("dashboard p95 must be below 5000 ms")


def _wait_until_persisted(event_id: str, clock_ns: Callable[[], int]) -> int:
    while True:
        rows = db.query_json(
            "SELECT json_build_object('present', EXISTS("
            "SELECT 1 FROM phase2.events WHERE event_id = "
            f"{db.literal(event_id)}::uuid))::text;"
        )
        if rows == [{"present": True}]:
            return clock_ns()
        Event().wait(POLL_INTERVAL_SECONDS)


def _finish_timings(persisted: Sequence[tuple[InjectedEvent, int]], run_id: str, clock_ns: Callable[[], int]) -> list[Timing]:
    noc.materialize(run_id)
    visible = clock_ns()
    return [
        Timing(str(sample.envelope["event_id"]), sample.t_injected_ns, stored, visible)
        for sample, stored in persisted
    ]


def _direct_leg(run_id: str, count: int, seed: int, fixtures_dir: Path, clock_ns: Callable[[], int]) -> list[Timing]:
    from scripts.phase2.execution import begin_execution
    from scripts.phase2.ledger import DispositionLedger
    from scripts.phase2.manifest import RunManifest, SourceSpec
    from scripts.phase2.persist import PostgresClaimStore
    from scripts.phase2.validate import DispositionEngine

    fixed_clock = _utc_timestamp(clock_ns())
    fixture = fixtures_dir / FIXTURE_NAME
    digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
    relative = str(fixture.relative_to(ROOT))
    sources = tuple(SourceSpec(f"latency-{index}", relative, digest) for index in range(count))
    context = begin_execution(RunManifest(run_id=run_id, fixed_clock=fixed_clock, sources=sources))
    persisted: list[tuple[InjectedEvent, int]] = []
    for ordinal, sample in enumerate(generate(count, seed, fixtures_dir, clock_ns=clock_ns)):
        ledger = DispositionLedger()
        store = PostgresClaimStore(context, sample.envelope, ordinal)
        disposition = DispositionEngine(store, ledger).handle(sample.envelope)
        if disposition.status != "accepted":
            raise LatencyError("direct latency sample was not accepted")
        persisted.append((sample, _wait_until_persisted(str(sample.envelope["event_id"]), clock_ns)))
    return _finish_timings(persisted, run_id, clock_ns)


def _kafka_seams() -> tuple[ProducerSeam, StreamSeam]:
    try:
        producer = kafka_producer.KafkaEnvelopeProducer()
        getattr(producer, "produce_envelope")
        getattr(producer, "flush")
        getattr(stream, "capture_end_offsets")
        getattr(stream, "run_consumer")
    except (ImportError, AttributeError) as error:
        raise KafkaIntegrationError(
            "Kafka leg requires kafka_producer produce/flush and stream watermark/consumer seams"
        ) from error
    return producer, stream


def _kafka_leg(run_id: str, count: int, seed: int, fixtures_dir: Path, output: Path, clock_ns: Callable[[], int]) -> list[Timing]:
    producer, stream = _kafka_seams()
    offsets_path = output.parent / "start-offsets.json"
    timings: list[Timing] = []
    events = generate(count, seed, fixtures_dir, clock_ns=clock_ns)
    for ordinal in range(count):
        starts = stream.capture_end_offsets(TOPIC)
        offsets_path.write_text(json.dumps(starts, sort_keys=True) + "\n", encoding="utf-8")
        sample = next(events)
        event_id = str(sample.envelope["event_id"])
        producer.produce_envelope(
            TOPIC,
            event_id,
            json.dumps(sample.envelope, sort_keys=True, separators=(",", ":")).encode(),
            {
                "schema_version": "0.1.0",
                "source_run_id": run_id,
                "input_ordinal": str(ordinal),
            },
        )
        producer.flush(30)
        stream.run_consumer(run_id, 1, 30, topic=TOPIC, start_offsets=offsets_path)
        persisted = _wait_until_persisted(event_id, clock_ns)
        noc.materialize(run_id)
        timings.append(Timing(event_id, sample.t_injected_ns, persisted, clock_ns()))
    return timings


def _run_leg(leg: Literal["direct", "kafka"], run_id: str, count: int, seed: int, fixtures_dir: Path, output: Path, clock_ns: Callable[[], int]) -> list[Timing]:
    match leg:
        case "direct":
            return _direct_leg(run_id, count, seed, fixtures_dir, clock_ns)
        case "kafka":
            return _kafka_leg(run_id, count, seed, fixtures_dir, output, clock_ns)
        case unreachable:
            assert_never(unreachable)


def _cleanup(run_id: str) -> None:
    first_error: db.DatabaseCommandError | None = None
    for table in ("dispositions", "noc_cards", "events", "run_manifests"):
        try:
            db.psql(f"DELETE FROM phase2.{table} WHERE run_id = {db.literal(run_id)};")
        except db.DatabaseCommandError as error:
            if first_error is None:
                first_error = error
    if first_error is not None:
        raise first_error


def run_harness(*, leg: Literal["direct", "kafka"], count: int, seed: int, fixtures_dir: Path, output: Path, assert_latency: bool, run_id: str | None = None, clock_ns: Callable[[], int] = time.time_ns) -> LatencyReport:
    """Run one isolated measurement and always remove its four run-scoped tables."""
    selected_run_id = run_id or f"latency-{seed}-{clock_ns()}"
    try:
        result = report(_run_leg(leg, selected_run_id, count, seed, fixtures_dir, output, clock_ns), seed=seed)
        output.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
        if assert_latency:
            assert_dashboard_latency(result)
        return result
    finally:
        _cleanup(selected_run_id)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leg", choices=("direct", "kafka"), required=True)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--assert", action="store_true", dest="assert_latency")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures-dir", type=Path, default=ROOT / "fixtures/synthetic/events")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        run_harness(leg=arguments.leg, count=arguments.count, seed=arguments.seed, fixtures_dir=arguments.fixtures_dir, output=arguments.output, assert_latency=arguments.assert_latency)
    except (LatencyError, db.DatabaseCommandError, OSError) as error:
        print(f"latency harness failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
