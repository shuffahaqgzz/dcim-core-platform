from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import tempfile
from typing import Protocol, runtime_checkable
import unittest

from connectors.redfish import RedfishFixtureAdapter
from connectors.redfish.adapter import CanonicalEnvelope, JsonValue
from scripts.phase2.errors import KillSwitchEngaged


ROOT = Path(__file__).resolve().parents[2]
CONNECTOR_ROOT = ROOT / "connectors" / "redfish"
FIXTURE = ROOT / "fixtures" / "synthetic" / "events" / "p1-redfish-health.json"
VALIDATOR_PATH = ROOT / "scripts" / "validate-json.py"
REQUIRED_ENVELOPE_FIELDS = {
    "correlation_id",
    "enrichment",
    "event_id",
    "event_type",
    "observed_at",
    "occurred_at",
    "payload",
    "priority",
    "schema_version",
    "source",
}
FORBIDDEN_IMPORTS = {
    "http.client",
    "httpx",
    "requests",
    "socket",
    "subprocess",
    "urllib",
}
FORBIDDEN_CALLS = {
    "delete",
    "patch",
    "post",
    "put",
    "reset",
    "set",
}
WRITE_CALLS = {
    "mkdir",
    "rename",
    "replace",
    "rmdir",
    "touch",
    "unlink",
    "write",
    "write_bytes",
    "write_text",
    "writelines",
}


@runtime_checkable
class EventValidator(Protocol):
    def validate_event(
        self,
        data: JsonValue,
        path: Path,
        required: set[str],
        errors: list[str],
    ) -> None: ...


class RedfishFixtureAdapterTests(unittest.TestCase):
    def test_fixture_replay_when_enabled_yields_schema_valid_redfish_envelope(
        self,
    ) -> None:
        adapter = RedfishFixtureAdapter(
            fixture_paths=[FIXTURE],
            clock="2026-07-29T00:00:00Z",
            kill_flag=lambda: False,
            stop_file=None,
        )

        events = list(adapter)

        self.assertEqual(1, len(events))
        event = events[0]
        source = event["source"]
        if not isinstance(source, dict):
            self.fail("adapter source must be a JSON object")
        self.assertEqual("2026-07-29T00:00:00Z", event["observed_at"])
        self.assertEqual(
            {
                "system": "redfish-synthetic",
                "instance": "bmc-001.example.invalid",
                "connector": "redfish-fixture-adapter",
                "transport": "redfish",
                "native_event_id": "SYNTHETIC-EVENT-0001",
            },
            source,
        )
        self.assertEqual([], self.validation_errors(event))

    def test_stop_file_when_present_fails_closed_before_first_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            stop_file = Path(temporary_directory) / "redfish.stop"
            stop_file.touch()
            adapter = RedfishFixtureAdapter(
                fixture_paths=[FIXTURE],
                clock="2026-07-29T00:00:00Z",
                kill_flag=lambda: False,
                stop_file=stop_file,
            )
            emitted: list[CanonicalEnvelope] = []

            with self.assertRaises(KillSwitchEngaged):
                emitted.extend(adapter)

        self.assertEqual([], emitted)

    def test_config_kill_flag_when_engaged_fails_closed_before_first_fixture(
        self,
    ) -> None:
        adapter = RedfishFixtureAdapter(
            fixture_paths=[FIXTURE],
            clock="2026-07-29T00:00:00Z",
            kill_flag=lambda: True,
            stop_file=None,
        )
        emitted: list[CanonicalEnvelope] = []

        with self.assertRaises(KillSwitchEngaged):
            emitted.extend(adapter)

        self.assertEqual([], emitted)

    def test_kill_switch_is_checked_before_each_fixture(self) -> None:
        checks = iter((False, True))
        adapter = RedfishFixtureAdapter(
            fixture_paths=[FIXTURE, FIXTURE],
            clock="2026-07-29T00:00:00Z",
            kill_flag=lambda: next(checks),
            stop_file=None,
        )
        events = iter(adapter)

        first = next(events)
        source = first["source"]
        if not isinstance(source, dict):
            self.fail("adapter source must be a JSON object")

        self.assertEqual("SYNTHETIC-EVENT-0001", source["native_event_id"])
        with self.assertRaises(KillSwitchEngaged):
            _ = next(events)

    def test_connector_ast_has_no_network_write_or_control_surface(self) -> None:
        python_files = sorted(CONNECTOR_ROOT.glob("*.py"))
        self.assertTrue(python_files)

        for path in python_files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertEqual([], self.forbidden_imports(tree))
                self.assertEqual([], self.forbidden_calls(tree))
                self.assertEqual([], self.write_calls(tree))
                self.assertEqual([], self.write_modes(tree))

    def validation_errors(self, event: CanonicalEnvelope) -> list[str]:
        spec = importlib.util.spec_from_file_location("validate_json", VALIDATOR_PATH)
        if spec is None or spec.loader is None:
            self.fail("unable to load the repository JSON validator")
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        if not isinstance(validator, EventValidator):
            self.fail("repository JSON validator has an unexpected interface")
        errors: list[str] = []
        validator.validate_event(
            event,
            FIXTURE,
            set(REQUIRED_ENVELOPE_FIELDS),
            errors,
        )
        return errors

    @staticmethod
    def forbidden_imports(tree: ast.AST) -> list[str]:
        imports = [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        ]
        imports.extend(
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        )
        return sorted(
            imported
            for imported in imports
            if any(
                imported == forbidden or imported.startswith(f"{forbidden}.")
                for forbidden in FORBIDDEN_IMPORTS
            )
        )

    @staticmethod
    def forbidden_calls(tree: ast.AST) -> list[str]:
        calls = [
            node.func.id.lower()
            if isinstance(node.func, ast.Name)
            else node.func.attr.lower()
            if isinstance(node.func, ast.Attribute)
            else ""
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        ]
        return sorted(call for call in calls if call in FORBIDDEN_CALLS)

    @staticmethod
    def write_calls(tree: ast.AST) -> list[str]:
        return sorted(
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in WRITE_CALLS
        )

    @staticmethod
    def write_modes(tree: ast.AST) -> list[str]:
        modes: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else ""
            )
            if name != "open":
                continue
            mode_nodes = list(node.args[1:2])
            mode_nodes.extend(
                keyword.value for keyword in node.keywords if keyword.arg == "mode"
            )
            for mode_node in mode_nodes:
                if (
                    isinstance(mode_node, ast.Constant)
                    and isinstance(mode_node.value, str)
                    and any(character in mode_node.value for character in "wax+")
                ):
                    modes.append(mode_node.value)
        return sorted(modes)


if __name__ == "__main__":
    _ = unittest.main()
