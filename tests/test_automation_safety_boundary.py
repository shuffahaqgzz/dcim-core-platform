"""Red/guard test for docs/security/automation-safety-boundary.md.

This module is expected to FAIL until Task 9 (Wave 2) delivers the doc.
After the doc lands the same test must go GREEN without modification.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "security" / "automation-safety-boundary.md"


class AutomationSafetyBoundaryTests(unittest.TestCase):
    """Assert the safety-boundary policy doc exists and covers every
    required section from Task 3 of PHASE0-PLAN.md."""

    def test_doc_exists(self) -> None:
        with self.subTest(check="file exists"):
            self.assertTrue(
                DOC.is_file(),
                f"Missing required file: {DOC.relative_to(ROOT)}",
            )

    def _read_text(self) -> str:
        """Return doc text, or skip remaining assertions when absent."""
        if not DOC.is_file():
            self.skipTest(
                f"{DOC.relative_to(ROOT)} does not exist yet (Task 9 pending)"
            )
        return DOC.read_text(encoding="utf-8").lower()

    # -- five execution preconditions ------------------------------------

    def test_five_execution_preconditions(self) -> None:
        text = self._read_text()
        preconditions = [
            ("explicit human approval", "human approval"),
            ("maintenance window", "maintenance window"),
            ("blast-radius", "blast-radius"),
            ("rollback", "rollback"),
            ("audit record", "audit record"),
        ]
        for phrase, label in preconditions:
            with self.subTest(precondition=label):
                self.assertIn(
                    phrase,
                    text,
                    f"Doc must state the '{label}' execution precondition",
                )

    # -- default mode ----------------------------------------------------

    def test_default_mode_is_dry_run(self) -> None:
        text = self._read_text()
        with self.subTest(check="default mode"):
            self.assertTrue(
                "dry-run" in text or "dry run" in text or "recommendation" in text,
                "Doc must state dry-run/recommendation as the default mode",
            )

    # -- prohibited operation classes ------------------------------------

    def test_prohibited_operation_classes(self) -> None:
        text = self._read_text()
        prohibited = [
            ("snmp set", "SNMP SET"),
            ("redfish", "Redfish write/action"),
            ("isapi", "ISAPI write/action"),
            ("power/reset", "power/reset"),
            ("firmware", "firmware"),
            ("ptz", "PTZ"),
            ("network configuration", "network configuration"),
            ("raw shell", "raw shell"),
            ("privileged sql", "privileged SQL"),
        ]
        for phrase, label in prohibited:
            with self.subTest(prohibited_class=label):
                self.assertIn(
                    phrase,
                    text,
                    f"Doc must name '{label}' as a prohibited operation class",
                )

    # -- ADR links -------------------------------------------------------

    def test_links_to_adr_0005_and_0025(self) -> None:
        text = self._read_text()
        with self.subTest(link="ADR-0005"):
            self.assertIn(
                "adr/0005",
                text,
                "Doc must link ../adr/0005-dry-run-automation.md",
            )
        with self.subTest(link="ADR-0025"):
            self.assertIn(
                "adr/0025",
                text,
                "Doc must link ../adr/0025-automation-execution-preconditions.md",
            )

    # -- Phase 6 safety layer --------------------------------------------

    def test_no_execution_before_phase_6(self) -> None:
        text = self._read_text()
        with self.subTest(check="Phase 6"):
            self.assertIn(
                "phase 6",
                text,
                "Doc must state no execution capability exists before Phase 6 safety layer",
            )


if __name__ == "__main__":
    unittest.main()
