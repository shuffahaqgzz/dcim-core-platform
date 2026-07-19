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

    def test_non_string_sensitive_identifier_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "sensitive identifier must be a string"):
            sanitize_demo.sanitize({"serial_number": 123456789}, self.salt)

    def test_sensitive_object_key_fails_closed(self) -> None:
        sensitive_key = "office-node" + ".internal"
        with self.assertRaisesRegex(ValueError, "object key contains sensitive network identity"):
            sanitize_demo.sanitize({sensitive_key: "alarm"}, self.salt)

    def test_dynamic_topology_object_key_fails_closed(self) -> None:
        sensitive_key = "core-" + "switch-review-9001"
        with self.assertRaisesRegex(ValueError, "object key is not approved"):
            sanitize_demo.sanitize({sensitive_key: "alarm"}, self.salt)

    def test_unmarked_dynamic_object_key_fails_closed(self) -> None:
        sensitive_key = "ci-" + "review-9001"
        with self.assertRaisesRegex(ValueError, "object key is not approved"):
            sanitize_demo.sanitize({sensitive_key: "alarm"}, self.salt)

    def test_fqdn_shaped_event_type_fails_closed(self) -> None:
        sensitive_event_type = "server" + ".review-domain.com"
        with self.assertRaisesRegex(ValueError, "event_type is not approved"):
            sanitize_demo.sanitize({"event_type": sensitive_event_type}, self.salt)

    def test_fqdn_shaped_schema_version_fails_closed(self) -> None:
        sensitive_version = "release" + ".review-domain.com"
        with self.assertRaisesRegex(ValueError, "schema_version is not approved"):
            sanitize_demo.sanitize({"schema_version": sensitive_version}, self.salt)

    def test_safe_count_and_confidence_fields_remain_legitimate(self) -> None:
        source = {"token_count": 3, "identity_confidence": 0.9}
        self.assertEqual(source, sanitize_demo.sanitize(source, self.salt))

    def test_credential_container_is_removed_before_recursion(self) -> None:
        key = "authoriz" + "ation"
        source = {key: {"value": "synthetic-review-value", "enabled": True}}
        output = sanitize_demo.sanitize(source, self.salt)
        self.assertEqual("<REMOVED>", output[key])
        self.assertEqual([], sanitize_demo.residual_findings(output))

    def test_sensitive_identifier_container_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "sensitive identifier must be a string"):
            sanitize_demo.sanitize({"serial_number": {"value": 9001}}, self.salt)

    def test_residual_check_rejects_unsanitized_credential_container(self) -> None:
        key = "authoriz" + "ation"
        findings = sanitize_demo.residual_findings({key: {"value": "synthetic-review"}})
        self.assertIn("credential-like field remains", findings)

    def test_preserved_fields_receive_residual_validation(self) -> None:
        private_address = "10." + "1.2.3"
        private_host = "device" + ".corp"
        output = sanitize_demo.sanitize(
            {
                "event_type": "server.health.degraded",
                "status": f"degraded at {private_host} from {private_address}",
            },
            self.salt,
        )
        findings = sanitize_demo.residual_findings(output)
        self.assertIn("non-documentation IP remains", findings)
        self.assertIn("non-documentation FQDN remains", findings)

    def test_cli_does_not_write_output_when_preserved_field_is_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.json"
            output_path = Path(directory) / "output.json"
            private_address = "10." + "1.2.3"
            input_path.write_text(json.dumps({"status": private_address}), encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                result = sanitize_demo.main(
                    [str(input_path), str(output_path), "--salt", self.salt]
                )
            self.assertEqual(1, result)
            self.assertFalse(output_path.exists())

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

    def test_invalid_fixture_keys_are_approved_for_sanitization(self) -> None:
        fixture = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "synthetic"
            / "invalid"
            / "invalid-event.json"
        )
        source = json.loads(fixture.read_text(encoding="utf-8"))

        output = sanitize_demo.sanitize(source, self.salt)

        self.assertNotEqual(source["expected_disposition"], output["expected_disposition"])
        self.assertNotEqual(source["expected_reason"], output["expected_reason"])
        self.assertEqual([], sanitize_demo.residual_findings(output))


if __name__ == "__main__":
    unittest.main()
