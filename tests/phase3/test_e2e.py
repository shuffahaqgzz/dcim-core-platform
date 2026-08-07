from __future__ import annotations

from contextlib import redirect_stderr
import fcntl
from io import StringIO
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import cast
from unittest.mock import patch
import unittest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase3 import e2e, e2e_dashboard


class E2EContractTests(unittest.TestCase):
    def make_state(self, directory: Path) -> e2e.E2EState:
        config = e2e.E2EConfig(
            output=directory / "evidence-e2e.json",
            fixtures_dir=ROOT / "fixtures/synthetic/events",
            token_file=directory / "internal-api-token",
        )
        return e2e.E2EState(config=config, run_id="e2e-test-run")

    def test_stages_execute_in_required_order(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            state = self.make_state(Path(raw_directory))
            called: list[str] = []

            def action(name: str):
                def run(_state: e2e.E2EState) -> None:
                    called.append(name)

                return run

            actions = tuple((name, action(name)) for name in e2e.STAGE_NAMES)
            e2e.execute_stages(state, actions=actions)

        self.assertEqual(
            (
                "topic-verify",
                "produce",
                "drain",
                "zero-loss",
                "dashboard",
                "latency",
            ),
            tuple(called),
        )

    def test_evidence_schema_carries_required_assertions_without_token(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            state = self.make_state(Path(raw_directory))
            state.producer_ledger = {"received": 6, "published": 6, "dlq": 0}
            state.consumer_ledger = {
                "received": 6,
                "accepted": 6,
                "quarantined": 0,
                "duplicate": 0,
            }
            state.database_counts = {
                "events": 6,
                "dispositions": 6,
                "accepted": 6,
                "quarantined": 0,
                "duplicate": 0,
            }
            state.dashboard = {
                "p1_visible": 2,
                "summary_p1": 2,
                "expected_p1": 2,
            }
            state.latency = {"leg": "kafka", "count": 50, "seed": 42, "p95_ms": 12.5}
            state.checks = {
                "zero_silent_loss": True,
                "producer_consumer_counts_match": True,
                "dashboard_visibility": True,
                "latency_p95_below_5000_ms": True,
                "latency_cleanup": True,
            }

            evidence = e2e.build_evidence(
                state,
                commit_sha="a" * 40,
                generated_at="2026-08-06T00:00:00Z",
            )

        self.assertEqual("1", evidence["schema_version"])
        checks = cast(dict[str, object], evidence["checks"])
        latency = cast(dict[str, object], evidence["latency"])
        self.assertTrue(checks["zero_silent_loss"])
        self.assertTrue(checks["dashboard_visibility"])
        self.assertLess(cast(float, latency["p95_ms"]), 5000)
        self.assertEqual(50, latency["count"])
        self.assertNotIn("internal-token-test-value", str(evidence))

    def test_missing_topic_aborts_at_stage_one_with_exact_error(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            output = Path(raw_directory) / "evidence-e2e.json"
            command = subprocess.CompletedProcess([], 1, "", "")
            stderr = StringIO()
            with patch.object(e2e, "_run_command", return_value=command) as run_command:
                with redirect_stderr(stderr):
                    result = e2e.main(
                        [
                            "--output",
                            str(output),
                            "--fixtures-dir",
                            str(ROOT / "fixtures/synthetic/events"),
                        ],
                    )

        self.assertEqual(1, result)
        self.assertEqual(
            "e2e: stage 1 topic-verify: FAIL: Kafka topic verification failed\n",
            stderr.getvalue(),
        )
        run_command.assert_called_once()

    def test_cleanup_removes_all_run_scoped_rows_in_fk_order(self) -> None:
        statements: list[str] = []
        with patch.object(e2e.db, "psql", side_effect=lambda sql: statements.append(sql) or ""):
            e2e.cleanup_run("e2e-test-run")

        self.assertEqual(4, len(statements))
        for table, statement in zip(
            ("dispositions", "noc_cards", "events", "run_manifests"),
            statements,
        ):
            self.assertIn(f"DELETE FROM phase2.{table}", statement)
        self.assertNotIn("internal-token-test-value", "".join(statements))

    def test_dashboard_baseline_uses_json_object_extraction_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            statements: list[str] = []

            def query(sql: str):
                statements.append(sql)
                raise e2e.E2EFailure("stop after baseline query")

            state = self.make_state(Path(raw_directory))
            with patch.object(e2e_dashboard.db, "query_json", side_effect=query):
                with self.assertRaises(e2e.E2EFailure):
                    e2e_dashboard.dashboard(state)

        self.assertEqual(1, len(statements))
        self.assertIn("row_to_json", statements[0])

    def test_service_check_wires_e2e_as_the_final_stage(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("scripts/phase3/e2e.py", makefile)
        self.assertIn("_service-check: phase3-deps phase3-test service-smoke e2e", makefile)
        self.assertIn("e2e: service-smoke", makefile)
        self.assertNotIn("KAFKA_BOOTSTRAP :=", makefile)
        self.assertEqual(
            2,
            makefile.count("scripts/phase2/kafka_host.sh --"),
        )
        self.assertNotIn("scripts/phase2/kafka_host.py --", makefile)
        self.assertNotIn("docker inspect --format", makefile)

    def test_service_check_serializes_before_running_prerequisites(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            # Given: the shared runtime lock is held by another service check.
            directory = Path(raw_directory)
            runtime_root = directory / "runtime"
            lock_path = runtime_root / "dev-build/service-check.lock"
            lock_path.parent.mkdir(parents=True)
            environment = {
                "DCIM_RUNTIME_ROOT": str(runtime_root),
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            }
            with lock_path.open("a+", encoding="utf-8") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

                # When: service-check is invoked through its real Make entry point.
                result = subprocess.run(
                    [
                        "make",
                        "--no-print-directory",
                        "-o",
                        "phase3-deps",
                        "-o",
                        "phase3-test",
                        "-o",
                        "service-smoke",
                        "-o",
                        "e2e",
                        "service-check",
                        "MAKE=/bin/true",
                        "SERVICE_CHECK_LOCK_TIMEOUT=0",
                    ],
                    cwd=ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )

                # Then: no prerequisite can complete until the runtime lock is released.
                self.assertNotEqual(0, result.returncode, result.stderr)
                self.assertNotIn("service-check: PASS", result.stdout)


if __name__ == "__main__":
    _ = unittest.main()
