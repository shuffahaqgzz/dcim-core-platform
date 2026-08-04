from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.phase2 import latency


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures/synthetic/events"


def canned_clock(*values: int) -> Iterator[int]:
    yield from values


class NearestRankTests(unittest.TestCase):
    def test_nearest_rank_covers_single_even_odd_and_twenty_samples(self) -> None:
        # Given: independently worked nearest-rank examples.
        cases = (
            ([7], 95, 7),
            ([1, 2, 3, 4], 50, 2),
            ([9, 1, 5, 3, 7], 50, 5),
            (list(range(1, 21)), 95, 19),
        )

        # When / Then: the selected rank matches each known literal.
        for samples, percentile, expected in cases:
            with self.subTest(samples=len(samples), percentile=percentile):
                self.assertEqual(expected, latency.nearest_rank(samples, percentile))


class WorkloadTests(unittest.TestCase):
    def test_generate_is_counted_unique_and_seed_deterministic(self) -> None:
        # Given: the same fixture source, count, and canned injection clock.
        def ids(seed: int) -> list[str]:
            clock = lambda: 1_800_000_000_000_000_000
            generated = [
                sample.envelope["event_id"]
                for sample in latency.generate(50, seed, FIXTURES, clock_ns=clock)
            ]
            self.assertTrue(all(isinstance(event_id, str) for event_id in generated))
            return [event_id for event_id in generated if isinstance(event_id, str)]

        # When: the workload is generated twice per seed and once with another seed.
        first = ids(42)
        replay = ids(42)
        different = ids(43)

        # Then: count and uniqueness hold, with deterministic seed behavior.
        self.assertEqual(50, len(first))
        self.assertEqual(50, len(set(first)))
        self.assertEqual(first, replay)
        self.assertNotEqual(first, different)

    def test_generate_records_seed_source_and_injection_timestamp(self) -> None:
        # Given: one canned nanosecond timestamp.
        clock = lambda: 1_800_000_000_123_456_000

        # When: one synthetic event is generated.
        sample = next(latency.generate(1, 17, FIXTURES, clock_ns=clock))

        # Then: provenance and timestamped envelope fields are retained internally.
        self.assertEqual(17, sample.seed)
        self.assertEqual("p1-redfish-health.json", sample.fixture_source)
        self.assertEqual(1_800_000_000_123_456_000, sample.t_injected_ns)
        self.assertEqual(sample.envelope["occurred_at"], sample.envelope["observed_at"])


class ReportTests(unittest.TestCase):
    def timings(self) -> list[latency.Timing]:
        return [
            latency.Timing(
                event_id="11111111-1111-4111-8111-111111111111",
                t_injected_ns=1_000,
                t_persisted_ns=2_500,
                t_dashboard_visible_ns=4_000,
            )
        ]

    def test_report_uses_intervals_without_absolute_timestamp_leakage(self) -> None:
        # Given: canned injection, persistence, and visibility timestamps.
        # When: the public report is built.
        report = latency.report(self.timings(), seed=42)
        encoded = json.dumps(report, sort_keys=True)
        samples = report["samples"]
        self.assertIsInstance(samples, list)
        sample = samples[0] if isinstance(samples, list) else None
        self.assertIsInstance(sample, dict)

        # Then: only the 1500/3000 ns intervals are exposed.
        self.assertEqual(1_500, sample["persist_latency_ns"] if isinstance(sample, dict) else None)
        self.assertEqual(3_000, sample["dashboard_latency_ns"] if isinstance(sample, dict) else None)
        for absolute in ("t_injected_ns", "t_persisted_ns", "t_dashboard_visible_ns"):
            self.assertNotIn(absolute, encoded)
        self.assertNotIn("2500", encoded)
        self.assertNotIn("4000", encoded)

    def test_report_schema_records_baseline_measurement_context(self) -> None:
        # Given / When: a one-sample report.
        report = latency.report(self.timings(), seed=42)

        # Then: every baseline-required context and distribution is present.
        self.assertEqual(
            {
                "sample_count",
                "seed",
                "fixture_source",
                "workload_class",
                "test_window",
                "clock_source",
                "percentile_method",
                "exclusions",
                "persist_latency_ns",
                "dashboard_latency_ns",
                "samples",
            },
            set(report),
        )
        self.assertEqual("event/trap (P1)", report["workload_class"])
        self.assertEqual("time.time_ns", report["clock_source"])
        self.assertEqual("nearest-rank", report["percentile_method"])
        persist = report["persist_latency_ns"]
        dashboard = report["dashboard_latency_ns"]
        self.assertIsInstance(persist, dict)
        self.assertIsInstance(dashboard, dict)
        self.assertEqual({"p50", "p95", "max"}, set(persist) if isinstance(persist, dict) else set())
        self.assertEqual({"p50", "p95", "max"}, set(dashboard) if isinstance(dashboard, dict) else set())

    def test_assertion_checks_dashboard_and_rejects_threshold_equality(self) -> None:
        # Given: fast persistence but dashboard visibility exactly at 5000 ms.
        timing = latency.Timing(
            event_id="11111111-1111-4111-8111-111111111111",
            t_injected_ns=0,
            t_persisted_ns=1,
            t_dashboard_visible_ns=5_000_000_000,
        )

        # When / Then: the strict dashboard threshold fails.
        with self.assertRaises(latency.LatencyThresholdError):
            latency.assert_dashboard_latency(latency.report([timing], seed=42))

    def test_nearest_rank_p95_rejects_ten_percent_slow_dashboard_samples(self) -> None:
        # Given: 45 one-nanosecond samples and five 6000 ms samples.
        timings = [
            latency.Timing(str(index), 0, 1, 1 if index < 45 else 6_000_000_000)
            for index in range(50)
        ]

        # When: the report computes the hand-worked rank 48.
        result = latency.report(timings, seed=42)
        dashboard = result["dashboard_latency_ns"]
        self.assertIsInstance(dashboard, dict)

        # Then: p95 is 6000 ms and the dashboard assertion rejects it.
        self.assertEqual(6_000_000_000, dashboard.get("p95") if isinstance(dashboard, dict) else None)
        with self.assertRaises(latency.LatencyThresholdError):
            latency.assert_dashboard_latency(result)


class KafkaOrderingTests(unittest.TestCase):
    def test_kafka_captures_and_writes_watermark_before_publication(self) -> None:
        # Given: fake future integration seams and a protected temporary output path.
        calls: list[str] = []
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            offsets = output.parent / "start-offsets.json"

            class Producer:
                def produce_envelope(self, *_args) -> None:
                    self.assert_offsets()
                    calls.append("publish")

                def assert_offsets(self) -> None:
                    self_outer.assertEqual({"0": 19}, json.loads(offsets.read_text()))

                def flush(self, _timeout: int) -> None:
                    calls.append("flush")

            class Stream:
                def capture_end_offsets(self, topic: str) -> dict[str, int]:
                    self_outer.assertEqual(latency.TOPIC, topic)
                    calls.append("capture")
                    return {"0": 19}

                def run_consumer(self, run_id, max_messages, idle_timeout_s, **options):
                    self_outer.assertEqual(("run", 2, 30), (run_id, max_messages, idle_timeout_s))
                    self_outer.assertEqual(offsets, options["start_offsets"])
                    calls.append("consume")
                    return {}

            self_outer = self
            clock = iter((1_800_000_000_000_000_000, 1_800_000_000_000_000_001,
                          1_800_000_000_000_000_010, 1_800_000_000_000_000_011,
                          1_800_000_000_000_000_020)).__next__
            with (
                patch.object(latency, "_kafka_seams", return_value=(Producer(), Stream())),
                patch.object(latency.db, "query_json", return_value=[{"present": True}]),
                patch.object(latency.noc, "materialize", side_effect=lambda _run: calls.append("noc")),
            ):
                timings = latency._kafka_leg("run", 2, 42, FIXTURES, output, clock)

        # When / Then: publication follows the durable pre-run watermark handoff.
        self.assertEqual(["capture", "publish", "publish", "flush", "consume", "noc"], calls)
        self.assertEqual(2, len(timings))


class CleanupTests(unittest.TestCase):
    def assert_cleanup(self, calls: list[str], run_id: str) -> None:
        expected_tables = ("dispositions", "noc_cards", "events", "run_manifests")
        self.assertEqual(4, len(calls))
        for sql, table in zip(calls, expected_tables, strict=True):
            self.assertEqual(
                f"DELETE FROM phase2.{table} WHERE run_id = '{run_id}';",
                sql,
            )

    def invoke(self, outcome: list[latency.Timing] | BaseException, asserted: bool) -> list[str]:
        calls: list[str] = []
        run_id = "latency-42-123"
        side_effect = outcome if isinstance(outcome, BaseException) else None
        return_value = None if side_effect else outcome
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(latency, "_run_leg", return_value=return_value, side_effect=side_effect),
            patch.object(latency.db, "psql", side_effect=lambda sql: calls.append(sql) or ""),
        ):
            try:
                latency.run_harness(
                    leg="direct",
                    count=1,
                    seed=42,
                    fixtures_dir=FIXTURES,
                    output=Path(directory) / "report.json",
                    assert_latency=asserted,
                    run_id=run_id,
                )
            except (latency.LatencyThresholdError, RuntimeError) as error:
                self.assertIsInstance(error, (latency.LatencyThresholdError, RuntimeError))
        self.assert_cleanup(calls, run_id)
        return calls

    def test_cleanup_runs_after_success(self) -> None:
        timing = latency.Timing("11111111-1111-4111-8111-111111111111", 0, 1, 2)
        self.invoke([timing], asserted=False)

    def test_cleanup_runs_after_threshold_failure(self) -> None:
        timing = latency.Timing(
            "11111111-1111-4111-8111-111111111111", 0, 1, 5_000_000_000
        )
        self.invoke([timing], asserted=True)

    def test_cleanup_runs_after_runtime_exception(self) -> None:
        self.invoke(RuntimeError("injected mid-run failure"), asserted=False)


if __name__ == "__main__":
    unittest.main()
