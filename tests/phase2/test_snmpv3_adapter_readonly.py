from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from connectors.snmp import SNMPv3FixtureAdapter
from connectors.snmp.adapter import CanonicalEnvelope
from scripts.phase2.errors import KillSwitchEngaged


ROOT = Path(__file__).resolve().parents[2]
CONNECTOR_ROOT = ROOT / "connectors" / "snmp"
FIXTURE = ROOT / "fixtures" / "synthetic" / "events" / "p2-network-utilization.json"
VALIDATOR_PATH = ROOT / "scripts" / "validate-json.py"
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_json", VALIDATOR_PATH
)
assert VALIDATOR_SPEC and VALIDATOR_SPEC.loader
validate_json = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(validate_json)


class SNMPv3FixtureAdapterTests(unittest.TestCase):
    def adapter(
        self,
        *,
        fixture_paths: list[Path] | None = None,
        kill_flag=lambda: False,
        stop_file: Path | None = None,
    ) -> SNMPv3FixtureAdapter:
        return SNMPv3FixtureAdapter(
            fixture_paths=fixture_paths or [FIXTURE],
            clock="2026-07-29T00:00:00Z",
            kill_flag=kill_flag,
            stop_file=stop_file,
        )

    def test_fixture_replay_yields_schema_valid_snmpv3_envelope(self) -> None:
        # Given: the approved synthetic P2 network-utilization fixture.
        expected_native_id = json.loads(FIXTURE.read_text(encoding="utf-8"))[
            "source"
        ]["native_event_id"]

        # When: the read-only fixture adapter replays it at a fixed clock.
        events = list(self.adapter())

        # Then: one canonical, schema-valid SNMPv3 envelope is emitted.
        self.assertEqual(1, len(events))
        event = events[0]
        source = event["source"]
        if not isinstance(source, dict):
            self.fail("source must be an object")
        self.assertEqual("2026-07-29T00:00:00Z", event["observed_at"])
        self.assertEqual(
            {
                "system": "snmpv3-synthetic",
                "transport": "snmpv3",
                "connector": "snmpv3-fixture-adapter",
                "native_event_id": expected_native_id,
            },
            {
                key: source[key]
                for key in ("system", "transport", "connector", "native_event_id")
            },
        )
        schema = json.loads(
            (ROOT / "schemas" / "event-envelope.schema.json").read_text(
                encoding="utf-8"
            )
        )
        errors: list[str] = []
        validate_json.validate_event(event, FIXTURE, set(schema["required"]), errors)
        self.assertEqual([], errors)

    def test_stop_file_prevents_any_fixture_replay(self) -> None:
        # Given: the stop-file tier is engaged before replay begins.
        with tempfile.TemporaryDirectory() as directory:
            stop_file = Path(directory) / "snmpv3.stop"
            stop_file.write_text("stop\n", encoding="utf-8")
            emitted: list[CanonicalEnvelope] = []

            # When: iteration is attempted.
            with self.assertRaises(KillSwitchEngaged):
                emitted.extend(self.adapter(stop_file=stop_file))

        # Then: the adapter emits no envelope.
        self.assertEqual([], emitted)

    def test_config_kill_flag_prevents_any_fixture_replay(self) -> None:
        # Given: the config-flag tier is engaged.
        emitted: list[CanonicalEnvelope] = []

        # When: iteration is attempted.
        with self.assertRaises(KillSwitchEngaged):
            emitted.extend(self.adapter(kill_flag=lambda: True))

        # Then: the adapter emits no envelope.
        self.assertEqual([], emitted)

    def test_kill_switch_is_checked_before_each_fixture(self) -> None:
        # Given: the kill flag engages after the first fixture.
        checks = iter((False, True))
        iterator = iter(
            self.adapter(
                fixture_paths=[FIXTURE, FIXTURE],
                kill_flag=lambda: next(checks),
            )
        )

        # When: the second fixture would be replayed.
        first = next(iterator)
        with self.assertRaises(KillSwitchEngaged):
            next(iterator)

        # Then: only the first fixture reached the output boundary.
        first_source = first["source"]
        if not isinstance(first_source, dict):
            self.fail("source must be an object")
        self.assertEqual("snmpv3", first_source["transport"])

    def test_adapter_ast_has_no_network_write_or_snmp_stack_capability(self) -> None:
        # Given: every Python module in the SNMP connector package.
        modules = sorted(CONNECTOR_ROOT.glob("*.py"))
        prohibited_imports = {
            "easysnmp",
            "http",
            "httpx",
            "netsnmp",
            "pysnmp",
            "requests",
            "scapy",
            "snmpsim",
            "socket",
            "subprocess",
            "urllib",
        }
        prohibited_file_calls = {
            "chmod",
            "mkdir",
            "rename",
            "replace",
            "rmdir",
            "touch",
            "unlink",
            "write",
            "write_bytes",
            "write_text",
        }
        prohibited_control_calls = {
            "configure",
            "firmware",
            "power",
            "reset",
            "set",
            "set_cmd",
            "set_request",
            "shell",
        }
        findings: list[str] = []

        # When: imports, calls, open modes, and SET-class tokens are inspected.
        for module in modules:
            source = module.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(module))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".", maxsplit=1)[0]
                        if root in prohibited_imports:
                            findings.append(f"{module.name}: import {alias.name}")
                if isinstance(node, ast.ImportFrom) and node.module:
                    root = node.module.split(".", maxsplit=1)[0]
                    if root in prohibited_imports:
                        findings.append(f"{module.name}: from {node.module}")
                if isinstance(node, ast.Call):
                    function = node.func
                    call_name = (
                        function.attr
                        if isinstance(function, ast.Attribute)
                        else function.id
                        if isinstance(function, ast.Name)
                        else ""
                    )
                    if call_name in prohibited_file_calls:
                        findings.append(f"{module.name}: file call {call_name}")
                    if call_name in prohibited_control_calls or call_name.startswith(
                        "set_"
                    ):
                        findings.append(f"{module.name}: control call {call_name}")
                    if call_name == "open":
                        mode = (
                            node.args[0].value
                            if node.args
                            and isinstance(node.args[0], ast.Constant)
                            and isinstance(node.args[0].value, str)
                            else "r"
                        )
                        if any(marker in mode for marker in ("w", "a", "x", "+")):
                            findings.append(f"{module.name}: open mode {mode}")
            compact_source = source.lower().replace("_", "").replace(" ", "")
            for token in (
                "snmpset",
                "setcmd",
                "setrequest",
                "writecommunity",
            ):
                if token in compact_source:
                    findings.append(f"{module.name}: token {token}")

        # Then: fixture replay exposes no connected or control-capable path.
        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
