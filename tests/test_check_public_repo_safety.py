from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_public_repo_safety.py"
SPEC = importlib.util.spec_from_file_location("repo_safety", SCRIPT)
assert SPEC and SPEC.loader
repo_safety = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = repo_safety
SPEC.loader.exec_module(repo_safety)


class RepositorySafetyTests(unittest.TestCase):
    def test_approved_public_download_url_ignores_archive_path_suffix(self) -> None:
        findings = repo_safety.text_findings(
            '"url": "https://codeload.github.com/example/project/tar.gz/revision"',
            "manifest.json",
        )
        self.assertFalse(any(item.rule == "endpoint-fqdn" for item in findings))

    def test_public_maven_download_is_approved(self) -> None:
        findings = repo_safety.text_findings(
            '"url": "https://repo.maven.apache.org/maven2/example/artifact.jar"',
            "manifest.json",
        )
        self.assertFalse(any(item.rule == "endpoint-fqdn" for item in findings))

    def test_malformed_url_fails_scan_without_crashing(self) -> None:
        findings = repo_safety.text_findings(
            'endpoint="https://[malformed' + '.company.com/path"',
            "config.json",
        )
        self.assertTrue(any(item.rule == "endpoint-fqdn" for item in findings))

    def test_absolute_mount_target_is_not_treated_as_network_endpoint(self) -> None:
        findings = repo_safety.text_findings(
            '"target": "/opt/example/artifact-1.0.jar"', "compose.json"
        )
        self.assertFalse(any(item.rule == "endpoint-fqdn" for item in findings))

    def scan(self, name: str, data: bytes) -> list[object]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return repo_safety.scan_paths([path], root)

    def test_report_never_contains_detected_ip(self) -> None:
        private_ip = "10." + "44.55.66"
        findings = self.scan("note.txt", f"endpoint={private_ip}\n".encode())
        payload = json.dumps([repo_safety.asdict(item) for item in findings])
        self.assertTrue(any(item.rule == "non-documentation-ip" for item in findings))
        self.assertNotIn(private_ip, payload)

    def test_authorization_header_rejected_and_redacted(self) -> None:
        value = "Bearer" + " synthetic-looking-but-not-placeholder"
        findings = self.scan("note.txt", f"Authoriz" f"ation: {value}\n".encode())
        self.assertTrue(any(item.rule == "authorization-header" for item in findings))
        self.assertTrue(all(item.detected == "<redacted>" for item in findings))

    def test_binary_and_non_utf8_fail_closed(self) -> None:
        self.assertTrue(any(item.rule == "binary-file" for item in self.scan("blob.bin", b"a\0b")))
        self.assertTrue(any(item.rule == "non-utf8" for item in self.scan("blob.txt", b"\xff\xfe")))

    def test_archive_and_private_evidence_path_rejected(self) -> None:
        self.assertTrue(any(item.rule == "forbidden-extension" for item in self.scan("artifact.zip", b"text")))
        self.assertTrue(any(item.rule == "forbidden-path" for item in self.scan("evidence/private/report.txt", b"text")))

    def test_internal_fqdn_rejected(self) -> None:
        hostname = "device" + ".corp"
        findings = self.scan("note.txt", hostname.encode())
        self.assertTrue(any(item.rule == "internal-fqdn" for item in findings))

    def test_operational_public_domain_fqdn_rejected(self) -> None:
        hostname = "private-host" + ".company.com"
        findings = self.scan("docs/note.md", hostname.encode())
        self.assertTrue(any(item.rule == "operational-fqdn" for item in findings))

    def test_generic_endpoint_assignment_fqdn_rejected(self) -> None:
        hostname = "prod01" + ".company.com"
        findings = self.scan("config.txt", f"endpoint=https://{hostname}/health".encode())
        self.assertTrue(any(item.rule == "endpoint-fqdn" for item in findings))

    def test_endpoint_assignment_variants_rejected(self) -> None:
        hosts = ("prod01" + ".company.com", "prod02" + ".company.net", "prod03" + ".company.technology")
        cases = (
            ("config.json", f'{{"endpoint":"https://{hosts[0]}/health"}}'),
            ("config.env", f"REDFISH_ENDPOINT=https://{hosts[1]}/health"),
            ("config.yaml", f"target_url: https://{hosts[2]}/health"),
        )
        for name, value in cases:
            findings = self.scan(name, value.encode())
            self.assertTrue(any(item.rule == "endpoint-fqdn" for item in findings), name)

    def test_placeholder_substring_does_not_bypass(self) -> None:
        value = "prefix-example-suffix"
        key = "to" + "ken"
        findings = self.scan("config.txt", f"{key}={value}\n".encode())
        self.assertTrue(any(item.rule == "credential-assignment" for item in findings))

    def test_quoted_nested_json_credentials_are_rejected_and_redacted(self) -> None:
        first_key = "pass" + "word"
        second_key = "client" + "_secret"
        first_value = "synthetic-review-value-one"
        second_value = "synthetic-review-value-two"
        payload = json.dumps({first_key: first_value, "nested": {second_key: second_value}})

        findings = self.scan("fixtures/synthetic/probe.json", payload.encode())
        structured = [item for item in findings if item.rule == "structured-credential-field"]

        self.assertEqual(2, len(structured))
        rendered = json.dumps([repo_safety.asdict(item) for item in structured])
        self.assertNotIn(first_value, rendered)
        self.assertNotIn(second_value, rendered)

    def test_quoted_json_credential_placeholder_is_allowed(self) -> None:
        key = "pass" + "word"
        payload = json.dumps({key: "<SET_LOCALLY>"})
        findings = self.scan("fixtures/synthetic/probe.json", payload.encode())
        self.assertFalse(any(item.rule == "structured-credential-field" for item in findings))

    def test_duplicate_json_credential_keys_cannot_hide_value(self) -> None:
        key = "pass" + "word"
        value = "synthetic-review-nonplaceholder"
        payload = f'{{"{key}":"{value}","{key}":"<REMOVED>"}}'

        findings = self.scan("fixtures/synthetic/probe.json", payload.encode())
        structured = [
            item for item in findings if item.rule == "structured-credential-field"
        ]

        self.assertEqual(1, len(structured))
        self.assertNotIn(
            value, json.dumps([repo_safety.asdict(item) for item in structured])
        )

    def test_malformed_structured_data_fails_closed(self) -> None:
        findings = self.scan("fixtures/synthetic/probe.json", b'{"nested":')
        self.assertTrue(any(item.rule == "structured-data-parse-error" for item in findings))

    def test_credential_container_with_nonplaceholder_leaf_is_rejected(self) -> None:
        key = "authoriz" + "ation"
        value = "synthetic-review-nonplaceholder"
        payload = json.dumps({key: {"scheme": "Bearer", "value": value}})
        findings = self.scan("fixtures/synthetic/probe.json", payload.encode())
        structured = [item for item in findings if item.rule == "structured-credential-field"]
        self.assertEqual(1, len(structured))
        self.assertNotIn(value, json.dumps([repo_safety.asdict(item) for item in structured]))

    def test_safe_counter_and_policy_fields_do_not_match_credentials(self) -> None:
        payload = json.dumps({"token_count": 3, "password_policy": "strong"})
        findings = self.scan("fixtures/synthetic/probe.json", payload.encode())
        self.assertFalse(any(item.rule == "structured-credential-field" for item in findings))

    def test_common_key_material_fields_are_rejected_and_redacted(self) -> None:
        keys = ("private_key", "secret_key", "access_key", "signing_key")
        values = {key: f"synthetic-review-{key}" for key in keys}
        findings = self.scan(
            "fixtures/synthetic/probe.json", json.dumps(values).encode()
        )
        structured = [item for item in findings if item.rule == "structured-credential-field"]

        self.assertEqual(len(keys), len(structured))
        rendered = json.dumps([repo_safety.asdict(item) for item in structured])
        for value in values.values():
            self.assertNotIn(value, rendered)

    def test_fixture_non_documentation_fqdn_rejected(self) -> None:
        hostname = "device" + ".company.com"
        findings = self.scan("fixtures/synthetic/example.json", f'{{"hostname":"{hostname}"}}'.encode())
        self.assertTrue(any(item.rule == "fixture-fqdn" for item in findings))

    def test_fixture_location_and_manufacturer_require_public_markers(self) -> None:
        payload = json.dumps(
            {"location": "Building 1", "manufacturer": "Vendor"}
        ).encode()

        findings = self.scan("fixtures/synthetic/example.json", payload)

        self.assertEqual(
            2, len([item for item in findings if item.rule == "fixture-identifier"])
        )

    def test_duplicate_fixture_keys_fail_closed_before_provenance_collapse(self) -> None:
        payload = (
            '{"location":"Building 1","location":"GENERIC-LAB",'
            '"manufacturer":"Vendor","manufacturer":"ExampleVendor"}'
        ).encode()

        findings = self.scan("fixtures/synthetic/example.json", payload)

        self.assertTrue(
            any(item.rule == "duplicate-object-key" for item in findings)
        )

    def test_sensitive_findings_are_never_allowlistable(self) -> None:
        finding = repo_safety.Finding("internal-fqdn", "docs/example.md", 1, "test")
        self.assertFalse(repo_safety.allowed(finding, [("internal-fqdn", "docs/example.md", "not permitted")]))
        critical = repo_safety.Finding("private-key", "docs/example.md", 1, "test")
        self.assertFalse(repo_safety.allowed(critical, [("private-key", "docs/example.md", "not permitted")]))

    def test_sensitive_directories_and_compressed_ipv6_rejected(self) -> None:
        for directory in ("inventory", "source-inventory", "state", "data", "volumes", "recordings", "exports", "packet-captures", ".hermes"):
            findings = self.scan(f"{directory}/example.txt", b"synthetic")
            self.assertTrue(any(item.rule == "forbidden-path" for item in findings), directory)
        address = "fd00" + "::" + "1234"
        findings = self.scan("note.txt", address.encode())
        self.assertTrue(any(item.rule == "non-documentation-ip" for item in findings))


if __name__ == "__main__":
    unittest.main()
