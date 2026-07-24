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

    def event_fixture(self, name: str) -> object:
        return json.loads((ROOT / "fixtures/synthetic/events" / name).read_text(encoding="utf-8"))

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

    def test_missing_event_id_is_rejected(self) -> None:
        event = deepcopy(self.fixture)
        event.pop("event_id")
        errors = self.validate(event)
        self.assertNotEqual([], errors)
        self.assertTrue(any("event_id" in error for error in errors))

    def test_non_utc_timestamp_is_rejected(self) -> None:
        event = deepcopy(self.fixture)
        event["occurred_at"] = "2026-07-16T07:00:00+07:00"
        self.assertTrue(any("occurred_at" in error for error in self.validate(event)))

    def test_ip_is_not_used_as_identity(self) -> None:
        enrichment = self.fixture["enrichment"]
        self.assertNotRegex(enrichment["asset_identity"], r"^(?:\d{1,3}\.){3}\d{1,3}$")
        self.assertNotRegex(enrichment["ci_identity"], r"^(?:\d{1,3}\.){3}\d{1,3}$")

    def test_p3_event_fixture_is_valid(self) -> None:
        event = self.event_fixture("p3-camera-health-offline.json")
        self.assertEqual([], self.validate(event))
        self.assertEqual("P3", event["priority"])

    def test_syslog_event_fixture_is_valid(self) -> None:
        event = self.event_fixture("p2-syslog-link-flap.json")
        self.assertEqual([], self.validate(event))
        self.assertEqual("syslog", event["source"]["transport"])

    def test_stream_event_fixture_is_valid(self) -> None:
        event = self.event_fixture("p2-stream-metric-sample.json")
        self.assertEqual([], self.validate(event))
        self.assertEqual("stream", event["source"]["transport"])


class ContextContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context_dir = ROOT / "fixtures/synthetic/context"
        cls.asset_schema = json.loads((ROOT / "schemas/asset.schema.json").read_text(encoding="utf-8"))
        cls.ci_schema = json.loads((ROOT / "schemas/ci.schema.json").read_text(encoding="utf-8"))

    def context_fixtures(self, prefix: str) -> list[object]:
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(self.context_dir.glob(f"{prefix}-*.json"))]

    def assert_context_fixture_matches_schema(self, fixture: object, schema: object) -> None:
        self.assertIsInstance(fixture, dict)
        self.assertIsInstance(schema, dict)
        self.assertTrue(set(schema["required"]).issubset(fixture))
        self.assertTrue(set(fixture).issubset(schema["properties"]))

        for alias in fixture["aliases"]:
            self.assertTrue(set(schema["properties"]["aliases"]["items"]["required"]).issubset(alias))
            self.assertIn(alias["type"], schema["properties"]["aliases"]["items"]["properties"]["type"]["enum"])
            self.assertGreaterEqual(alias["confidence"], 0)
            self.assertLessEqual(alias["confidence"], 1)

    def test_asset_context_fixtures_validate_against_asset_schema(self) -> None:
        fixtures = self.context_fixtures("asset")
        self.assertEqual(3, len(fixtures))
        for fixture in fixtures:
            with self.subTest(asset_id=fixture["asset_id"]):
                self.assert_context_fixture_matches_schema(fixture, self.asset_schema)
                identity = fixture["identity"]
                self.assertTrue(
                    "native_uuid" in identity
                    or {"manufacturer", "serial_number"}.issubset(identity)
                )

    def test_ci_context_fixtures_validate_against_ci_schema(self) -> None:
        fixtures = self.context_fixtures("ci")
        self.assertEqual(3, len(fixtures))
        for fixture in fixtures:
            with self.subTest(ci_id=fixture["ci_id"]):
                self.assert_context_fixture_matches_schema(fixture, self.ci_schema)

    def test_context_collision_fixture_has_ambiguous_disposition(self) -> None:
        fixture_names = (
            "asset-synthetic-edge-alpha.json",
            "asset-synthetic-edge-beta.json",
        )
        fixtures = [
            json.loads((self.context_dir / name).read_text(encoding="utf-8"))
            for name in fixture_names
        ]
        collision_candidates = [
            fixture["asset_id"]
            for fixture in fixtures
            if any(
                alias["type"] == "hostname"
                and alias["value"] == "synthetic-edge-collision.example.invalid"
                for alias in fixture["aliases"]
            )
        ]

        self.assertEqual(
            ["10000000-0000-4000-8000-000000000001", "10000000-0000-4000-8000-000000000002"],
            collision_candidates,
        )
        self.assertEqual("ambiguous", "ambiguous" if len(collision_candidates) > 1 else "accepted")


if __name__ == "__main__":
    unittest.main()
