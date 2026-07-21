from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/foundation_smoke.py"
RECIPES = ROOT / "deploy/compose/derived-images/recipes.json"
LICENSE_DISPOSITIONS = ROOT / "deploy/compose/derived-images/license-dispositions.json"
IMAGE_INVENTORY = ROOT / "deploy/compose/images.json"
SPEC = importlib.util.spec_from_file_location("foundation_smoke", SCRIPT)
assert SPEC and SPEC.loader
FOUNDATION_SMOKE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FOUNDATION_SMOKE
SPEC.loader.exec_module(FOUNDATION_SMOKE)


def write_image_lock(plane: Path) -> None:
    (plane / "derived-images-lock.json").write_text(
        json.dumps({
            "schema_version": 2,
            "publication": False,
            "manifest_sha256": hashlib.sha256(RECIPES.read_bytes()).hexdigest(),
            "license_dispositions_sha256": hashlib.sha256(
                LICENSE_DISPOSITIONS.read_bytes()
            ).hexdigest(),
            "images": [
                {"component": component, "image_id": f"sha256:{index:064x}"}
                for index, component in enumerate(
                    ("postgres", "kafka", "grafana", "postgres-exporter"), start=1,
                )
            ],
        }),
        encoding="utf-8",
    )


def add_fake_image_environment(environment: dict[str, str]) -> None:
    inventory = json.loads(IMAGE_INVENTORY.read_text(encoding="utf-8"))
    references = {item["component"]: item["image"] for item in inventory["images"]}
    environment["FAKE_PROMETHEUS_IMAGE"] = references["Prometheus"]
    environment["FAKE_JMX_IMAGE"] = references["JMX exporter Java runtime"]


def write_inspection_only_docker(path: Path) -> None:
    path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import os
            import sys

            container = sys.argv[2]
            derived = {
                "dcim-build-postgres-1": "sha256:" + f"{1:064x}",
                "dcim-build-kafka-1": "sha256:" + f"{2:064x}",
                "dcim-build-grafana-1": "sha256:" + f"{3:064x}",
                "dcim-build-postgres-exporter-1": "sha256:" + f"{4:064x}",
            }
            if container in derived:
                print(derived[container] + "|synthetic-derived")
            elif container == "dcim-build-prometheus-1":
                print("sha256:" + "a" * 64 + "|" + os.environ["FAKE_PROMETHEUS_IMAGE"])
            elif container == "dcim-build-kafka-jmx-exporter-1":
                print("sha256:" + "b" * 64 + "|" + os.environ["FAKE_JMX_IMAGE"])
            else:
                sys.exit(1)
            """
        ),
        encoding="utf-8",
    )
    path.chmod(0o755)


class FoundationSmokeContractTests(unittest.TestCase):
    def test_normal_compose_prefix_rejects_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"
            plane = runtime_root / "dev-build"
            plane.mkdir(parents=True)
            runtime_root.chmod(0o700)
            plane.chmod(0o700)
            environment = {
                "DCIM_RUNTIME_ROOT": str(runtime_root),
                "COMPOSE_PROJECT_NAME": "dcim-build",
                "DCIM_COMPOSE_OVERRIDE": str(plane / "acceptance-compose.override.yaml"),
            }

            with (
                mock.patch.dict(os.environ, environment, clear=True),
                self.assertRaisesRegex(FOUNDATION_SMOKE.SmokeFailure, "prohibited"),
            ):
                FOUNDATION_SMOKE.compose_prefix()

    def test_acceptance_compose_prefix_requires_valid_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"
            plane = runtime_root / "dev-build"
            plane.mkdir(parents=True)
            runtime_root.chmod(0o700)
            plane.chmod(0o700)
            environment = {
                "DCIM_RUNTIME_ROOT": str(runtime_root),
                "COMPOSE_PROJECT_NAME": "dcim-build-acceptance-abcdef123456",
            }

            with (
                mock.patch.dict(os.environ, environment, clear=True),
                self.assertRaisesRegex(FOUNDATION_SMOKE.SmokeFailure, "required"),
            ):
                FOUNDATION_SMOKE.compose_prefix()

            environment["DCIM_COMPOSE_OVERRIDE"] = str(plane / "wrong.yaml")
            with (
                mock.patch.dict(os.environ, environment, clear=True),
                self.assertRaisesRegex(FOUNDATION_SMOKE.SmokeFailure, "mismatch"),
            ):
                FOUNDATION_SMOKE.compose_prefix()

    def test_acceptance_compose_prefix_includes_external_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"
            plane = runtime_root / "dev-build"
            plane.mkdir(parents=True)
            runtime_root.chmod(0o700)
            plane.chmod(0o700)
            override = plane / "acceptance-compose.override.yaml"
            override.write_text("networks: {}\n", encoding="utf-8")
            environment = {
                "DCIM_RUNTIME_ROOT": str(runtime_root),
                "COMPOSE_PROJECT_NAME": "dcim-build-acceptance-abcdef123456",
                "DCIM_COMPOSE_OVERRIDE": str(override),
            }

            with mock.patch.dict(os.environ, environment, clear=True):
                command = FOUNDATION_SMOKE.compose_prefix()

            self.assertIn(str(override), command)
            self.assertEqual(2, command.count("-f"))

    def test_evidence_rejects_tampered_lock_and_nonrunning_image_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            plane = root / "dev-build"
            plane.mkdir(parents=True)
            root.chmod(0o700)
            plane.chmod(0o700)
            write_image_lock(plane)
            lock_path = plane / "derived-images-lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            lock["manifest_sha256"] = "0" * 64
            lock_path.write_text(json.dumps(lock), encoding="utf-8")

            with self.assertRaisesRegex(FOUNDATION_SMOKE.SmokeFailure, "recipe"):
                FOUNDATION_SMOKE.foundation_image_digests(root)

            write_image_lock(plane)
            with (
                mock.patch.object(
                    FOUNDATION_SMOKE,
                    "run",
                    return_value=("sha256:" + "f" * 64) + "|ignored",
                ),
                self.assertRaisesRegex(FOUNDATION_SMOKE.SmokeFailure, "running image"),
            ):
                FOUNDATION_SMOKE.foundation_image_digests(root)

    def test_controlled_ninety_percent_refusal_fails_if_writes_are_allowed(self) -> None:
        unsafe = {"logical_usage_ratio": 0.90, "writes_allowed": True, "disposition": "unsafe"}
        with (
            mock.patch.object(FOUNDATION_SMOKE, "capacity_disposition", return_value=unsafe),
            self.assertRaisesRegex(FOUNDATION_SMOKE.SmokeFailure, "90 percent"),
        ):
            FOUNDATION_SMOKE.assert_controlled_capacity_refusal()

    def test_fast_smoke_refuses_before_any_write_at_ninety_percent(self) -> None:
        with (
            mock.patch.object(FOUNDATION_SMOKE, "query_scalar", return_value=0.90),
            mock.patch.object(FOUNDATION_SMOKE, "ensure_kafka_topic") as kafka_write,
            mock.patch.object(FOUNDATION_SMOKE, "postgres_round_trip") as postgres_write,
            self.assertRaisesRegex(FOUNDATION_SMOKE.SmokeFailure, "90 percent"),
        ):
            FOUNDATION_SMOKE.fast_smoke("synthetic-0123456789abcdef")

        kafka_write.assert_not_called()
        postgres_write.assert_not_called()

    def test_oversize_rejection_uses_unchanged_broker_offset(self) -> None:
        producer = subprocess.CompletedProcess(["docker"], 0, "", "")
        with (
            mock.patch.object(FOUNDATION_SMOKE, "compose_prefix", return_value=["docker"]),
            mock.patch.object(FOUNDATION_SMOKE, "kafka_next_offset", side_effect=[7, 7]),
            mock.patch.object(FOUNDATION_SMOKE.subprocess, "run", return_value=producer),
            mock.patch.object(FOUNDATION_SMOKE.time, "sleep"),
        ):
            FOUNDATION_SMOKE.kafka_rejects_oversize_message()

    def test_oversize_acceptance_advances_offset_even_if_client_fails(self) -> None:
        producer = subprocess.CompletedProcess(["docker"], 1, "", "broker rejected later")
        with (
            mock.patch.object(FOUNDATION_SMOKE, "compose_prefix", return_value=["docker"]),
            mock.patch.object(FOUNDATION_SMOKE, "kafka_next_offset", side_effect=[7, 8]),
            mock.patch.object(FOUNDATION_SMOKE.subprocess, "run", return_value=producer),
            mock.patch.object(FOUNDATION_SMOKE.time, "sleep"),
            self.assertRaisesRegex(FOUNDATION_SMOKE.SmokeFailure, "oversize"),
        ):
            FOUNDATION_SMOKE.kafka_rejects_oversize_message()

    def test_recovery_observability_waits_for_exporter_backend(self) -> None:
        delayed = FOUNDATION_SMOKE.SmokeFailure("backend not ready")
        with (
            mock.patch.object(
                FOUNDATION_SMOKE, "assert_observability", side_effect=[delayed, None]
            ) as assertion,
            mock.patch.object(FOUNDATION_SMOKE.time, "sleep") as sleep,
            mock.patch.object(
                FOUNDATION_SMOKE.time, "monotonic", side_effect=[0.0, 0.0, 1.0]
            ),
        ):
            FOUNDATION_SMOKE.wait_for_observability(timeout=30)

        self.assertEqual(2, assertion.call_count)
        sleep.assert_called_once_with(5)

    def test_capacity_refuses_writes_at_ninety_percent(self) -> None:
        result = subprocess.run(
            ["python3", str(SCRIPT), "capacity", "--ratio", "0.90"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(0, result.returncode)
        disposition = json.loads(result.stdout)
        self.assertEqual("refused-capacity-critical", disposition["disposition"])
        self.assertFalse(disposition["writes_allowed"])

    def test_capacity_allows_writes_below_ninety_percent(self) -> None:
        result = subprocess.run(
            ["python3", str(SCRIPT), "capacity", "--ratio", "0.899"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)["writes_allowed"])

    def test_evidence_contains_only_public_safe_allowlisted_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            runtime_root = temporary / "runtime"
            plane = runtime_root / "dev-build"
            plane.mkdir(parents=True)
            runtime_root.chmod(0o700)
            plane.chmod(0o700)
            write_image_lock(plane)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            write_inspection_only_docker(fake_bin / "docker")
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
            add_fake_image_environment(environment)
            result = subprocess.run(
                [
                    "python3", str(SCRIPT), "evidence", "--runtime-root", str(runtime_root),
                    "--mode", "fast", "--run-id", "synthetic-0123456789abcdef",
                    "--duration", "1.25", "--result", "pass",
                ],
                cwd=ROOT, env=environment, capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            output = (
                runtime_root / "dev-build/evidence/fast-synthetic-0123456789abcdef.json"
            )
            evidence = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(2, evidence["schema_version"])
            self.assertEqual(
                {"schema_version", "commit", "capability_profiles", "utc_timestamp",
                 "duration_seconds", "assertion_result", "synthetic_run_id", "mode",
                 "image_digests"},
                set(evidence),
            )
            self.assertEqual(
                {"grafana", "jmx-exporter-java-runtime", "kafka", "postgres",
                 "postgres-exporter", "prometheus"},
                set(evidence["image_digests"]),
            )
            serialized = output.read_text(encoding="utf-8")
            for prohibited in ("hostname", "runtime_root", "environment", "credential", "container"):
                self.assertNotIn(prohibited, serialized.lower())

    def test_recovery_fails_when_state_disappears_during_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            runtime_root = temporary / "runtime"
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            fake_docker = fake_bin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import json
                    import os
                    from pathlib import Path
                    import re
                    import sys

                    state_path = Path(os.environ["FAKE_DOCKER_STATE"])
                    state = json.loads(state_path.read_text()) if state_path.exists() else {}
                    arguments = sys.argv[1:]

                    def save():
                        state_path.write_text(json.dumps(state))

                    if "restart" in arguments:
                        state.clear()
                        save()
                    elif any(item.endswith("kafka-topics.sh") for item in arguments) and "--list" in arguments:
                        print("__consumer_offsets")
                        print("dcim.synthetic.smoke.v1")
                    elif any(item.endswith("kafka-console-producer.sh") for item in arguments):
                        payload = sys.stdin.read()
                        match = re.search(r"synthetic-[0-9a-f]+", payload)
                        if match:
                            state["kafka"] = match.group(0)
                            save()
                    elif any(item.endswith("kafka-get-offsets.sh") for item in arguments):
                        print(f"dcim.synthetic.smoke.v1:0:{1 if state.get('kafka') else 0}")
                    elif any(item.endswith("kafka-console-consumer.sh") for item in arguments):
                        if state.get("kafka"):
                            print(json.dumps({"run_id": state["kafka"]}))
                    elif "pg_dump" in arguments:
                        print("CREATE SCHEMA foundation;")
                    elif "psql" in arguments:
                        sql = arguments[arguments.index("-c") + 1] if "-c" in arguments else sys.stdin.read()
                        match = re.search(r"synthetic-[0-9a-f]+", sql)
                        if "INSERT INTO" in sql and match:
                            state["postgres"] = match.group(0)
                            save()
                            print(match.group(0))
                        elif "SELECT run_id" in sql and match and state.get("postgres") == match.group(0):
                            print(match.group(0))
                        elif "string_agg" in sql:
                            print("1:synthetic-checksum")
                    elif any("/api/v1/targets" in item for item in arguments):
                        jobs = ["prometheus", "postgres-exporter", "kafka-jmx-exporter", "grafana"]
                        print(json.dumps({"status": "success", "data": {"activeTargets": [
                            {"labels": {"job": job}, "health": "up"} for job in jobs
                        ]}}))
                    elif any("/api/v1/rules" in item for item in arguments):
                        names = ["FoundationTargetDown", "PostgreSQLExporterBackendDown",
                                 "KafkaBrokerNotActive", "KafkaStorageSeventyPercent",
                                 "KafkaStorageEightyFivePercent", "KafkaStorageNinetyPercent"]
                        print(json.dumps({"status": "success", "data": {"groups": [
                            {"rules": [{"name": name} for name in names]}
                        ]}}))
                    elif any("/api/v1/query" in item for item in arguments):
                        value = "0" if any("kafka_log_size_bytes" in item for item in arguments) else "1"
                        print(json.dumps({"status": "success", "data": {"result": [
                            {"value": [0, value]}
                        ]}}))
                    elif arguments and arguments[0] == "inspect":
                        container = arguments[1]
                        derived = {
                            "dcim-build-postgres-1": "sha256:" + f"{1:064x}",
                            "dcim-build-kafka-1": "sha256:" + f"{2:064x}",
                            "dcim-build-grafana-1": "sha256:" + f"{3:064x}",
                            "dcim-build-postgres-exporter-1": "sha256:" + f"{4:064x}",
                        }
                        if any("{{.Image}}" in item for item in arguments):
                            if container in derived:
                                print(derived[container] + "|synthetic-derived")
                            elif container == "dcim-build-prometheus-1":
                                print("sha256:" + "a" * 64 + "|" + os.environ["FAKE_PROMETHEUS_IMAGE"])
                            elif container == "dcim-build-kafka-jmx-exporter-1":
                                print("sha256:" + "b" * 64 + "|" + os.environ["FAKE_JMX_IMAGE"])
                        else:
                            print("127.0.0.1")
                    sys.exit(0)
                    """
                ),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
            environment["DCIM_RUNTIME_ROOT"] = str(runtime_root)
            environment["FAKE_DOCKER_STATE"] = str(temporary / "docker-state.json")
            add_fake_image_environment(environment)
            plane = runtime_root / "dev-build"
            plane.mkdir(parents=True)
            runtime_root.chmod(0o700)
            plane.chmod(0o700)
            write_image_lock(plane)

            result = subprocess.run(
                ["python3", str(SCRIPT), "recovery"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("persistence", result.stderr.lower())

    def test_fast_evidence_cannot_claim_pass_after_five_minutes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            runtime_root = temporary / "runtime"
            plane = runtime_root / "dev-build"
            plane.mkdir(parents=True)
            runtime_root.chmod(0o700)
            plane.chmod(0o700)
            write_image_lock(plane)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            write_inspection_only_docker(fake_bin / "docker")
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
            add_fake_image_environment(environment)

            result = subprocess.run(
                [
                    "python3", str(SCRIPT), "evidence", "--runtime-root", str(runtime_root),
                    "--mode", "fast", "--run-id", "synthetic-fedcba9876543210",
                    "--duration", "300.001", "--result", "pass",
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            output = plane / "evidence/fast-synthetic-fedcba9876543210.json"
            self.assertEqual(
                "fail", json.loads(output.read_text(encoding="utf-8"))["assertion_result"],
            )

    def test_fast_smoke_requires_oversize_kafka_message_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            runtime_root = temporary / "runtime"
            plane = runtime_root / "dev-build"
            plane.mkdir(parents=True)
            runtime_root.chmod(0o700)
            plane.chmod(0o700)
            write_image_lock(plane)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            fake_docker = fake_bin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import json
                    import os
                    from pathlib import Path
                    import re
                    import sys

                    arguments = sys.argv[1:]
                    state_path = Path(os.environ["FAKE_DOCKER_STATE"])
                    state = json.loads(state_path.read_text()) if state_path.exists() else {}
                    if any("/api/v1/query" in item for item in arguments):
                        print(json.dumps({"status": "success", "data": {"result": [
                            {"value": [0, "0"]}
                        ]}}))
                    elif "psql" in arguments:
                        sql = arguments[arguments.index("-c") + 1]
                        match = re.search(r"synthetic-[0-9a-f]+", sql)
                        if match:
                            state["run_id"] = match.group(0)
                            state_path.write_text(json.dumps(state))
                            print(match.group(0))
                    elif any(item.endswith("kafka-topics.sh") for item in arguments) and "--list" in arguments:
                        print("__consumer_offsets")
                        print("dcim.synthetic.smoke.v1")
                    elif any(item.endswith("kafka-get-offsets.sh") for item in arguments):
                        print(f"dcim.synthetic.smoke.v1:0:{state.get('offset', 0)}")
                    elif any(item.endswith("kafka-console-producer.sh") for item in arguments):
                        payload = sys.stdin.read()
                        match = re.search(r"synthetic-[0-9a-f]+", payload)
                        if len(payload) > 1_048_576:
                            state["offset"] = state.get("offset", 0) + 1
                            state_path.write_text(json.dumps(state))
                        elif match:
                            state["run_id"] = match.group(0)
                            state["offset"] = state.get("offset", 0) + 1
                            state_path.write_text(json.dumps(state))
                    elif any(item.endswith("kafka-console-consumer.sh") for item in arguments):
                        print(json.dumps({"run_id": state.get("run_id")}))
                    elif arguments and arguments[0] == "inspect":
                        container = arguments[1]
                        derived = {
                            "dcim-build-postgres-1": "sha256:" + f"{1:064x}",
                            "dcim-build-kafka-1": "sha256:" + f"{2:064x}",
                            "dcim-build-grafana-1": "sha256:" + f"{3:064x}",
                            "dcim-build-postgres-exporter-1": "sha256:" + f"{4:064x}",
                        }
                        if container in derived:
                            print(derived[container] + "|synthetic-derived")
                        elif container == "dcim-build-prometheus-1":
                            print("sha256:" + "a" * 64 + "|" + os.environ["FAKE_PROMETHEUS_IMAGE"])
                        elif container == "dcim-build-kafka-jmx-exporter-1":
                            print("sha256:" + "b" * 64 + "|" + os.environ["FAKE_JMX_IMAGE"])
                    sys.exit(0)
                    """
                ),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
            environment["DCIM_RUNTIME_ROOT"] = str(runtime_root)
            environment["FAKE_DOCKER_STATE"] = str(temporary / "docker-state.json")
            add_fake_image_environment(environment)

            result = subprocess.run(
                ["python3", str(SCRIPT), "fast"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("oversize", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
