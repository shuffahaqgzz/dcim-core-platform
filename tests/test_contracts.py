from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-json.py"
SPEC = importlib.util.spec_from_file_location("validate_json", SCRIPT)
assert SPEC and SPEC.loader
validate_json = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_json)


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads((ROOT / "schemas/event-envelope.schema.json").read_text(encoding="utf-8"))
        cls.fixture = json.loads((ROOT / "fixtures/synthetic/events/p1-redfish-health.json").read_text(encoding="utf-8"))

    def validate(self, event: object) -> list[str]:
        errors: list[str] = []
        validate_json.validate_event(event, ROOT / "fixtures/synthetic/events/in-memory.json", set(self.schema["required"]), errors)
        return errors

    def test_reference_fixture_is_valid(self) -> None:
        self.assertEqual([], self.validate(self.fixture))

    def test_missing_priority_is_rejected(self) -> None:
        event = deepcopy(self.fixture)
        event.pop("priority")
        self.assertTrue(any("missing required keys" in error for error in self.validate(event)))

    def test_non_utc_timestamp_is_rejected(self) -> None:
        event = deepcopy(self.fixture)
        event["occurred_at"] = "2026-07-16T07:00:00+07:00"
        self.assertTrue(any("occurred_at" in error for error in self.validate(event)))

    def test_ip_is_not_used_as_identity(self) -> None:
        enrichment = self.fixture["enrichment"]
        self.assertNotRegex(enrichment["asset_identity"], r"^(?:\d{1,3}\.){3}\d{1,3}$")
        self.assertNotRegex(enrichment["ci_identity"], r"^(?:\d{1,3}\.){3}\d{1,3}$")


if __name__ == "__main__":
    unittest.main()
