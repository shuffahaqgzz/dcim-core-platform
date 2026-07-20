from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/foundation_smoke.py"


class FoundationSmokeContractTests(unittest.TestCase):
    def test_capacity_refuses_writes_at_ninety_percent(self) -> None:
        result = subprocess.run(
            ["python3", str(SCRIPT), "capacity", "--ratio", "0.90"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(0, result.returncode)
        disposition = json.loads(result.stdout)
        self.assertEqual("refused-capacity-critical", disposition["disposition"])
        self.assertFalse(disposition["writes_allowed"])

    def test_capacity_allows_writes_below_ninety_percent(self) -> None:
        result = subprocess.run(
            ["python3", str(SCRIPT), "capacity", "--ratio", "0.899"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)["writes_allowed"])

    def test_evidence_contains_only_public_safe_allowlisted_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence.json"
            result = subprocess.run(
                [
                    "python3", str(SCRIPT), "evidence", "--output", str(output),
                    "--mode", "fast", "--run-id", "synthetic-0123456789abcdef",
                    "--duration", "1.25", "--result", "pass",
                ],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            evidence = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                {"schema_version", "commit", "capability_profiles", "utc_timestamp",
                 "duration_seconds", "assertion_result", "synthetic_run_id", "mode"},
                set(evidence),
            )
            serialized = output.read_text(encoding="utf-8")
            for prohibited in ("hostname", "runtime_root", "environment", "credential", "container"):
                self.assertNotIn(prohibited, serialized.lower())


if __name__ == "__main__":
    unittest.main()
