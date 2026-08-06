from __future__ import annotations

import ast
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.phase2 import kafka_host


ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/phase2/kafka_host.py"
WRAPPER = ROOT / "scripts/phase2/kafka_host.sh"
MAPPING = b"192.0.2.7 kafka # dcim-build dev plane (host-side gate access)\n"


class HostsTransformationTests(unittest.TestCase):
    def test_mapping_preserves_original_bytes_and_adds_exact_line(self) -> None:
        # Given: a hosts file with comments and no terminal newline.
        original = b"127.0.0.1 localhost\n# synthetic hosts\n::1 localhost"

        # When: the temporary Kafka mapping is rendered.
        updated = kafka_host.add_kafka_mapping(original, "192.0.2.7")

        # Then: every original byte is preserved and the exact mapping is appended.
        self.assertEqual(original + b"\n" + MAPPING, updated)

    def test_exact_mapping_is_idempotent(self) -> None:
        # Given: the exact temporary mapping is already present.
        original = b"127.0.0.1 localhost\n" + MAPPING

        # When: the same mapping is requested again.
        updated = kafka_host.add_kafka_mapping(original, "192.0.2.7")

        # Then: no bytes are changed.
        self.assertEqual(original, updated)

    def test_conflicting_kafka_mapping_fails_closed(self) -> None:
        # Given: an existing Kafka hostname bound to a different address.
        original = b"127.0.0.1 localhost\n192.0.2.8 kafka alias\n"

        # When/Then: rendering refuses to shadow the conflicting mapping.
        with self.assertRaises(kafka_host.HostsConflictError):
            kafka_host.add_kafka_mapping(original, "192.0.2.7")

    def test_invalid_address_fails_without_echoing_input(self) -> None:
        # Given: an invalid inspect result containing a private marker.
        address = "private-invalid-address"

        # When/Then: validation fails with a stable public-safe error.
        with self.assertRaises(kafka_host.InvalidAddressError) as caught:
            kafka_host.add_kafka_mapping(b"127.0.0.1 localhost\n", address)
        self.assertNotIn(address, str(caught.exception))

    def test_transform_writes_only_the_transformed_hosts_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kafka-host-transform-") as temporary:
            # Given: exact source and destination files from mktemp-style paths.
            directory = Path(temporary)
            source = directory / "original"
            destination = directory / "updated"
            original = b"127.0.0.1 localhost\n"
            source.write_bytes(original)
            destination.write_bytes(b"")

            # When: the helper transforms the hosts file.
            kafka_host.transform_hosts(source, destination, "192.0.2.7")

            # Then: the destination is the original bytes plus the exact mapping.
            self.assertEqual(original + MAPPING, destination.read_bytes())

    def test_cli_conflict_does_not_output_or_overwrite_raw_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kafka-host-conflict-") as temporary:
            # Given: a conflict and an existing destination sentinel.
            directory = Path(temporary)
            source = directory / "original"
            destination = directory / "updated"
            source.write_bytes(b"private-host-entry\n192.0.2.8 kafka\n")
            destination.write_bytes(b"sentinel")
            stderr = StringIO()

            # When: the CLI transformation fails closed.
            with redirect_stderr(stderr):
                status = kafka_host.main(
                    ["192.0.2.7", str(source), str(destination)]
                )

            # Then: only a stable error is emitted and output remains untouched.
            self.assertEqual(1, status)
            self.assertEqual(b"sentinel", destination.read_bytes())
            self.assertNotIn("private-host-entry", stderr.getvalue())
            self.assertNotIn("192.0.2.8", stderr.getvalue())


class KafkaHostStaticContractTests(unittest.TestCase):
    def test_python_helper_has_no_process_or_privilege_orchestration(self) -> None:
        # Given: the complete Python helper syntax tree.
        source = HELPER.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(HELPER))

        # When: imports and calls are inspected.
        imported = {
            alias.name.split(".", maxsplit=1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported.update(
            node.module.split(".", maxsplit=1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        )
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }

        # Then: Python remains a pure stdlib file transformer without subprocess.
        self.assertNotIn("subprocess", imported)
        self.assertNotIn("system", calls)
        self.assertNotIn("popen", calls)

    def test_shell_wrapper_has_bounded_silent_restoring_contract(self) -> None:
        # Given: the host-side orchestration wrapper.
        source = WRAPPER.read_text(encoding="utf-8")

        # When/Then: orchestration is argv-based, bounded, silent, and trapped.
        required = (
            'mktemp "${TMPDIR:-/tmp}/dcim-kafka-host.original.XXXXXX"',
            'mktemp "${TMPDIR:-/tmp}/dcim-kafka-host.updated.XXXXXX"',
            'cp -- /etc/hosts "$original_hosts"',
            'timeout 10 docker inspect --format "$inspect_format" dcim-build-kafka-1',
            'python3 "$helper" "$kafka_ip" "$original_hosts" "$updated_hosts"',
            'sudo -n tee -- /etc/hosts < "$updated_hosts"',
            'sudo -n tee -- /etc/hosts < "$original_hosts"',
            'DCIM_KAFKA_BOOTSTRAP="kafka:9092" "$@"',
            "trap cleanup EXIT",
            "trap 'exit 129' HUP",
            "trap 'exit 130' INT",
            "trap 'exit 143' TERM",
            'rm -f -- "$original_hosts"',
            'rm -f -- "$updated_hosts"',
        )
        for contract in required:
            self.assertIn(contract, source)
        self.assertNotIn("eval", source)
        self.assertNotIn("sudo tee", source)

        result = subprocess.run(
            ["bash", "-n", str(WRAPPER)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_make_targets_use_wrapper_and_compose_keeps_kafka_internal(self) -> None:
        # Given: the Make gate and Development Compose contract.
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        compose = (ROOT / "deploy/compose/dev-build/compose.yaml").read_text(encoding="utf-8")
        kafka_block = compose.split("  kafka:\n", 1)[1].split("\n  postgres-exporter:\n", 1)[0]

        # When/Then: both host-side gates use the wrapper without host exposure.
        self.assertEqual(2, makefile.count("scripts/phase2/kafka_host.sh --"))
        self.assertNotIn("scripts/phase2/kafka_host.py --", makefile)
        self.assertNotIn("docker inspect --format", makefile)
        self.assertIn("KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092", kafka_block)
        self.assertNotIn("ports:", kafka_block)
        self.assertNotIn("network_mode:", kafka_block)
        self.assertNotIn("privileged:", kafka_block)
        self.assertNotIn("pid:", kafka_block)
        self.assertNotIn("ipc:", kafka_block)


if __name__ == "__main__":
    _ = unittest.main()
