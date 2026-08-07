from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import unittest

from scripts.phase2 import kafka_host


ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "scripts/phase2/kafka_host.sh"


class KafkaBootstrapTests(unittest.TestCase):
    def test_fixed_synthetic_address_is_returned_as_bootstrap(self) -> None:
        self.assertEqual("192.0.2.2:9092", kafka_host.bootstrap_servers())

    def test_non_fixed_address_fails_without_echoing_input(self) -> None:
        address = "private-invalid-address"
        with self.assertRaises(kafka_host.KafkaHostError) as caught:
            kafka_host.bootstrap_servers(address)
        self.assertNotIn(address, str(caught.exception))


class KafkaHostStaticContractTests(unittest.TestCase):
    def test_python_helper_has_no_process_or_privilege_orchestration(self) -> None:
        source = (ROOT / "scripts/phase2/kafka_host.py").read_text(encoding="utf-8")
        tree = ast.parse(source, filename="scripts/phase2/kafka_host.py")

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

        self.assertNotIn("subprocess", imported)
        self.assertNotIn("system", calls)
        self.assertNotIn("popen", calls)

    def test_shell_wrapper_has_no_host_mutation_and_uses_bounded_state_check(self) -> None:
        source = WRAPPER.read_text(encoding="utf-8")
        required = (
            "timeout 10 docker inspect --format '{{.State.Status}}' dcim-build-kafka-1",
            "running|stopped|exited|created|dead)",
            'DCIM_KAFKA_BOOTSTRAP="192.0.2.2:9092" "$@"',
        )
        for contract in required:
            self.assertIn(contract, source)
        for prohibited in ("sudo", "/etc/hosts", "mktemp", "kafka_host.py"):
            self.assertNotIn(prohibited, source)
        self.assertNotIn("eval", source)

        result = subprocess.run(
            ["bash", "-n", str(WRAPPER)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_make_and_compose_keep_kafka_internal_without_host_exposure(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        compose = (ROOT / "deploy/compose/dev-build/compose.yaml").read_text(encoding="utf-8")
        kafka_block = compose.split("  kafka:\n", 1)[1].split("\n  postgres-exporter:\n", 1)[0]

        self.assertEqual(2, makefile.count("scripts/phase2/kafka_host.sh --"))
        self.assertNotIn("scripts/phase2/kafka_host.py --", makefile)
        self.assertNotIn("docker inspect --format", makefile)
        self.assertIn("KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://192.0.2.2:9092", kafka_block)
        self.assertIn("ipv4_address: 192.0.2.2", kafka_block)
        self.assertIn("subnet: 192.0.2.0/24", compose)
        self.assertIn("ip_range: 192.0.2.128/25", compose)
        for prohibited in ("ports:", "network_mode:", "privileged:", "pid:", "ipc:"):
            self.assertNotIn(prohibited, kafka_block)


if __name__ == "__main__":
    _ = unittest.main()
