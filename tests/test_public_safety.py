from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check-public-safety.py"
SPEC = importlib.util.spec_from_file_location("public_safety", SCRIPT)
assert SPEC and SPEC.loader
public_safety = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(public_safety)


class PublicSafetyTests(unittest.TestCase):
    def scan_text(self, name: str, text: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            return public_safety.scan_paths([path], root)

    def test_safe_placeholder_and_reserved_domain_pass(self) -> None:
        findings = self.scan_text(".env.example", "PASSWORD=<SET_LOCALLY>\nHOST=bmc-001.example.invalid\n")
        self.assertEqual([], findings)

    def test_private_ip_is_rejected(self) -> None:
        value = "10." + "23.45.67"
        findings = self.scan_text("note.md", f"endpoint={value}\n")
        self.assertTrue(any("non-documentation IP" in item for item in findings))

    def test_real_credential_assignment_is_rejected(self) -> None:
        value = "correct" + "-horse-battery"
        key = "pass" + "word"
        findings = self.scan_text("config.txt", f"{key}={value}\n")
        self.assertTrue(any("non-placeholder password" in item for item in findings))

    def test_private_key_material_is_rejected(self) -> None:
        marker = "-----BEGIN " + "PRIVATE KEY-----"
        findings = self.scan_text("note.txt", marker + "\n")
        self.assertTrue(any("private key material" in item for item in findings))

    def test_forbidden_filename_is_rejected(self) -> None:
        findings = self.scan_text(".env", "SAFE=synthetic\n")
        self.assertTrue(any("forbidden filename" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
