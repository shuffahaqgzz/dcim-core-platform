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

    def test_fixture_non_documentation_fqdn_rejected(self) -> None:
        hostname = "device" + ".company.com"
        findings = self.scan("fixtures/synthetic/example.json", f'{{"hostname":"{hostname}"}}'.encode())
        self.assertTrue(any(item.rule == "fixture-fqdn" for item in findings))

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
