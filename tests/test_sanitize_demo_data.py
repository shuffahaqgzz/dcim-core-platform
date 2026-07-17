from __future__ import annotations

import importlib.util
import ipaddress
import io
import json
from contextlib import redirect_stderr
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sanitize_demo_data.py"
SPEC = importlib.util.spec_from_file_location("sanitize_demo", SCRIPT)
assert SPEC and SPEC.loader
sanitize_demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sanitize_demo)


class SanitizerTests(unittest.TestCase):
    salt = "unit-test-supplied-salt"

    def sample(self) -> dict[str, object]:
        hostname = "private-host" + ".corp"
        address = "10." + "22.33.44"
        return {
            "hostname": hostname,
            "event_type": "server.health.degraded",
            "schema_version": "0.1.0",
            "event_id": "12345678-1234-4234-8234-123456789012",
            "correlation_id": "12345678-1234-4234-8234-123456789012",
            "native_event_id": "REAL-OFFICE-EVENT-991",
            "system": "office-source.company.com",
            "interface_alias": "SECRET-SITE-UPLINK",
            "pool": "PRIVATE-NAS-POOL",
            "ip_address": address,
            "serial_number": "REAL-SERIAL-123",
            "url": f"https://{hostname}/health",
            "location": "Private Site Rack 9",
            "nested": {"camera_name": "Lobby Camera", "raw_message": f"{hostname} at {address} failed"},
            "unknown_nested": {"origin": hostname, "note": "Confidential project phrase", "network_note": "contact " + "device" + ".company.com", "compressed_ipv6": "fd00" + "::" + "1234"},
            "vendor_auth_token_value": "synthetic-sensitive-value",
            "hardware_serial_code": "REAL-NESTED-SERIAL",
            "credential_ref": "vault://vendor/live",
        }

    def test_original_identifiers_removed_and_nested_redacted(self) -> None:
        output = sanitize_demo.sanitize(self.sample(), self.salt)
        rendered = json.dumps(output)
        hostname = "private-host" + ".corp"
        address = "10." + "22.33.44"
        public_host = "device" + ".company.com"
        ipv6 = "fd00" + "::" + "1234"
        for original in (hostname, address, public_host, ipv6, "Confidential project phrase", "synthetic-sensitive-value", "REAL-SERIAL-123", "REAL-NESTED-SERIAL", "REAL-OFFICE-EVENT-991", "office-source.company.com", "SECRET-SITE-UPLINK", "PRIVATE-NAS-POOL", "Private Site Rack 9", "Lobby Camera"):
            self.assertNotIn(original, rendered)
        self.assertEqual("<REMOVED>", output["credential_ref"])
        self.assertIn(str(output["hostname"]), str(output["url"]))
        self.assertEqual("server.health.degraded", output["event_type"])
        self.assertEqual("0.1.0", output["schema_version"])
        self.assertEqual(output["event_id"], output["correlation_id"])

    def test_pseudonym_is_stable_and_input_not_modified(self) -> None:
        source = self.sample()
        before = json.dumps(source, sort_keys=True)
        first = sanitize_demo.sanitize(source, self.salt)
        second = sanitize_demo.sanitize(source, self.salt)
        self.assertEqual(first, second)
        self.assertEqual(before, json.dumps(source, sort_keys=True))

    def test_output_ip_uses_documentation_range(self) -> None:
        output = sanitize_demo.sanitize(self.sample(), self.salt)
        address = ipaddress.ip_address(output["ip_address"])
        networks = [ipaddress.ip_network(item) for item in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]
        self.assertTrue(any(address in network for network in networks))

    def test_invalid_json_fails_without_modifying_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.json"
            output_path = Path(directory) / "output.json"
            input_path.write_text("{invalid", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                result = sanitize_demo.main([str(input_path), str(output_path), "--salt", self.salt])
            self.assertEqual(1, result)
            self.assertEqual("{invalid", input_path.read_text(encoding="utf-8"))
            self.assertFalse(output_path.exists())

    def test_missing_salt_and_same_path_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text("{}", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                missing_salt = sanitize_demo.main([str(path), str(Path(directory) / "out.json")])
                same_path = sanitize_demo.main([str(path), str(path), "--salt", self.salt])
            self.assertEqual(2, missing_salt)
            self.assertEqual(1, same_path)

    def test_jsonl_input_produces_jsonl_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.jsonl"
            output_path = Path(directory) / "output.jsonl"
            records = [self.sample(), self.sample()]
            input_path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
            self.assertEqual(0, sanitize_demo.main([str(input_path), str(output_path), "--salt", self.salt]))
            lines = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(2, len(lines))
            self.assertEqual(lines[0]["hostname"], lines[1]["hostname"])

    def test_fixture_matches_deterministic_expected_output(self) -> None:
        fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic" / "sanitization"
        source = json.loads((fixture_root / "input-event.json").read_text(encoding="utf-8"))
        expected = json.loads((fixture_root / "expected-sanitized-event.json").read_text(encoding="utf-8"))
        self.assertEqual(expected, sanitize_demo.sanitize(source, "phase0-fixture-salt-v1"))


if __name__ == "__main__":
    unittest.main()
