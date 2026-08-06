from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch
import unittest

from scripts.phase2 import kafka_host


ROOT = Path(__file__).resolve().parents[2]
MAPPING = b"192.0.2.7 kafka # dcim-build dev plane (host-side gate access)\n"


class HostsTransformationTests(unittest.TestCase):
    def test_mapping_preserves_original_bytes_and_adds_exact_line(self) -> None:
        # Given: a hosts file with comments and no terminal newline.
        original = b"127.0.0.1 localhost\n# synthetic hosts\n::1 localhost"

        # When: the temporary Kafka mapping is rendered.
        updated = kafka_host.add_kafka_mapping(original, "192.0.2.7")

        # Then: every original byte is preserved and the exact mapping is appended.
        self.assertEqual(original + b"\n" + MAPPING, updated)

    def test_conflicting_kafka_mapping_fails_closed(self) -> None:
        # Given: an existing Kafka hostname bound to a different address.
        original = b"127.0.0.1 localhost\n192.0.2.8 kafka alias\n"

        # When/Then: rendering refuses to shadow the conflicting mapping.
        with self.assertRaises(kafka_host.HostsConflictError):
            kafka_host.add_kafka_mapping(original, "192.0.2.7")


class KafkaHostRunnerTests(unittest.TestCase):
    def test_success_restores_original_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            # Given: a writable synthetic hosts file and a successful child.
            hosts_path = Path(raw_directory) / "hosts"
            original = b"127.0.0.1 localhost\n"
            hosts_path.write_bytes(original)
            completed = subprocess.CompletedProcess(["synthetic-child"], 0)

            with (
                patch.object(kafka_host, "resolve_kafka_ip", return_value="192.0.2.7"),
                patch.object(kafka_host.subprocess, "run", return_value=completed),
            ):
                # When: the child completes successfully.
                status = kafka_host.run_with_kafka_host(
                    ["synthetic-child"], hosts_path=hosts_path
                )

            # Then: success is returned and the exact original is restored.
            self.assertEqual(0, status)
            self.assertEqual(original, hosts_path.read_bytes())

    def test_child_exit_code_and_environment_are_returned_before_restore(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            # Given: a writable synthetic hosts file and a successful IP lookup.
            hosts_path = Path(raw_directory) / "hosts"
            original = b"127.0.0.1 localhost\n"
            hosts_path.write_bytes(original)

            def child_run(
                argv: list[str], *, env: dict[str, str], check: bool
            ) -> subprocess.CompletedProcess[str]:
                self.assertEqual(["synthetic-child", "arg"], argv)
                self.assertEqual(MAPPING, hosts_path.read_bytes()[len(original) :])
                self.assertFalse(check)
                self.assertEqual("kafka:9092", env["DCIM_KAFKA_BOOTSTRAP"])
                return subprocess.CompletedProcess(argv, 23)

            with (
                patch.object(kafka_host, "resolve_kafka_ip", return_value="192.0.2.7"),
                patch.object(kafka_host.subprocess, "run", side_effect=child_run),
            ):
                # When: the child exits unsuccessfully.
                status = kafka_host.run_with_kafka_host(
                    ["synthetic-child", "arg"], hosts_path=hosts_path
                )

            # Then: its exit status is returned and the exact original is restored.
            self.assertEqual(23, status)
            self.assertEqual(original, hosts_path.read_bytes())

    def test_child_launch_error_restores_original_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            # Given: a hosts file that can be modified before child launch.
            hosts_path = Path(raw_directory) / "hosts"
            original = b"127.0.0.1 localhost\n"
            hosts_path.write_bytes(original)

            with (
                patch.object(kafka_host, "resolve_kafka_ip", return_value="192.0.2.7"),
                patch.object(kafka_host.subprocess, "run", side_effect=OSError("private detail")),
            ):
                # When/Then: a launch error is converted to a public-safe failure.
                with self.assertRaises(kafka_host.ChildLaunchError) as caught:
                    kafka_host.run_with_kafka_host(["missing-child"], hosts_path=hosts_path)

            self.assertNotIn("private detail", str(caught.exception))
            self.assertEqual(original, hosts_path.read_bytes())

    def test_keyboard_interrupt_restores_original_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            # Given: a child interrupted after the mapping is installed.
            hosts_path = Path(raw_directory) / "hosts"
            original = b"127.0.0.1 localhost\n"
            hosts_path.write_bytes(original)

            with (
                patch.object(kafka_host, "resolve_kafka_ip", return_value="192.0.2.7"),
                patch.object(kafka_host.subprocess, "run", side_effect=KeyboardInterrupt),
            ):
                # When/Then: the interrupt propagates only after restoration.
                with self.assertRaises(KeyboardInterrupt):
                    kafka_host.run_with_kafka_host(["synthetic-child"], hosts_path=hosts_path)

            self.assertEqual(original, hosts_path.read_bytes())

    def test_inspect_failure_never_exposes_captured_output(self) -> None:
        # Given: docker inspect output containing text that must remain private.
        completed = subprocess.CompletedProcess(
            ["docker", "inspect"], 1, stdout=b"private stdout", stderr=b"private stderr"
        )

        with patch.object(kafka_host.subprocess, "run", return_value=completed):
            # When/Then: failure reports only a stable public-safe message.
            with self.assertRaises(kafka_host.KafkaInspectError) as caught:
                kafka_host.resolve_kafka_ip()

        self.assertNotIn("private", str(caught.exception))

    def test_inspect_uses_bounded_argv_and_returns_validated_address(self) -> None:
        # Given: docker inspect returns one synthetic container address.
        completed = subprocess.CompletedProcess(
            ["docker", "inspect"], 0, stdout=b"192.0.2.7\n", stderr=b""
        )

        with patch.object(
            kafka_host.subprocess, "run", return_value=completed
        ) as run:
            # When: the current Kafka address is resolved.
            address = kafka_host.resolve_kafka_ip()

        # Then: inspect is bounded, silent, argv-based, and validated.
        self.assertEqual("192.0.2.7", address)
        run.assert_called_once_with(
            [
                "docker",
                "inspect",
                "--format",
                "{{range .NetworkSettings.Networks}}{{println .IPAddress}}{{end}}",
                "dcim-build-kafka-1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=kafka_host.INSPECT_TIMEOUT_SECONDS,
            check=False,
        )

    def test_read_only_hosts_uses_passwordless_sudo_without_output(self) -> None:
        # Given: a hosts path the workspace user cannot write.
        completed = subprocess.CompletedProcess(["sudo", "-n", "tee"], 0)

        with (
            patch.object(kafka_host.os, "access", return_value=False),
            patch.object(kafka_host.subprocess, "run", return_value=completed) as run,
        ):
            # When: exact bytes are written through the privileged boundary.
            kafka_host.write_hosts(Path("/etc/hosts"), MAPPING)

        # Then: sudo is non-interactive and all helper output is suppressed.
        run.assert_called_once_with(
            ["sudo", "-n", "tee", "--", "/etc/hosts"],
            input=MAPPING,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=kafka_host.SUDO_TIMEOUT_SECONDS,
            check=False,
        )


class KafkaHostStaticContractTests(unittest.TestCase):
    def test_make_targets_use_helper_and_compose_keeps_kafka_internal(self) -> None:
        # Given: the Make gate and Development Compose contract.
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        compose = (ROOT / "deploy/compose/dev-build/compose.yaml").read_text(encoding="utf-8")
        kafka_block = compose.split("  kafka:\n", 1)[1].split("\n  postgres-exporter:\n", 1)[0]

        # When/Then: both host-side gates use the helper without host exposure.
        self.assertEqual(2, makefile.count("scripts/phase2/kafka_host.py --"))
        self.assertNotIn("docker inspect --format", makefile)
        self.assertIn("KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092", kafka_block)
        self.assertNotIn("ports:", kafka_block)
        self.assertNotIn("network_mode:", kafka_block)
        self.assertNotIn("privileged:", kafka_block)
        self.assertNotIn("pid:", kafka_block)
        self.assertNotIn("ipc:", kafka_block)


if __name__ == "__main__":
    _ = unittest.main()
