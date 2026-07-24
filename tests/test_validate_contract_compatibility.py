from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_contract_compatibility.py"


class ContractCompatibilityCliTests(unittest.TestCase):
    def run_validator(self, root: Path = ROOT) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root)],
            capture_output=True,
            check=False,
            cwd=ROOT,
            text=True,
        )

    def test_repository_contracts_are_compatible(self) -> None:
        result = self.run_validator()

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Contract compatibility validation passed", result.stdout)

    def test_transport_enum_drift_fails_the_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copied_root = Path(temporary) / "repository"
            shutil.copytree(
                ROOT,
                copied_root,
                ignore=shutil.ignore_patterns(".git", ".omo", "__pycache__"),
            )
            schema_path = copied_root / "schemas" / "event-envelope.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            transports = schema["properties"]["source"]["properties"]["transport"]["enum"]
            transports.remove("stream")
            schema_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")

            result = self.run_validator(copied_root)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("transport enum differs", result.stderr)


if __name__ == "__main__":
    unittest.main()
