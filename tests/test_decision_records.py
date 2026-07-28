from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADR_DIR = ROOT / "docs/adr"
VALID_STATUSES = {"Proposed", "Accepted", "Rejected", "Superseded"}
REQUIRED_ADRS = (
    "docs/adr/0024-python-fastapi-service-language-baseline.md",
    "docs/adr/0025-automation-execution-preconditions.md",
    "docs/adr/0026-program-technology-version-baseline.md",
    "docs/adr/0027-private-llm-serving-baseline.md",
)


class DecisionRecordTests(unittest.TestCase):
    def test_every_adr_has_valid_status_header(self) -> None:
        for path in sorted(ADR_DIR.glob("0*.md")):
            with self.subTest(path=path.relative_to(ROOT)):
                text = path.read_text(encoding="utf-8")
                match = re.search(
                    r"^- Status: (Proposed|Accepted|Rejected|Superseded)(?:\s|$)",
                    text,
                    re.MULTILINE,
                )
                self.assertIsNotNone(
                    match,
                    f"missing - Status: header in {path.relative_to(ROOT)}",
                )
                status = match.group(1) if match else ""
                self.assertIn(status, VALID_STATUSES, f"invalid status {status!r} in {path.relative_to(ROOT)}")

    def test_adr_0007_is_accepted(self) -> None:
        path = ADR_DIR / "0007-cmdb-implementation-for-development.md"
        text = path.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^- Status: Accepted$", f"ADR-0007 not Accepted: {path}")

    def test_new_adrs_exist_and_are_accepted(self) -> None:
        for relative in REQUIRED_ADRS:
            path = ROOT / relative
            with self.subTest(path=relative):
                self.assertTrue(path.is_file(), f"missing ADR artifact: {relative}")
                if path.is_file():
                    text = path.read_text(encoding="utf-8")
                    self.assertRegex(text, r"(?m)^- Status: Accepted$", f"ADR not Accepted: {relative}")

    def test_adr_index_references_every_adr_filename(self) -> None:
        index = (ADR_DIR / "README.md").read_text(encoding="utf-8")
        for path in sorted(ADR_DIR.glob("0*.md")):
            with self.subTest(path=path.name):
                self.assertIn(path.name, index, f"ADR index missing crosswalk row: {path.name}")

    def test_reserved_adr_0022_is_declared_and_unused(self) -> None:
        reserved = sorted(ADR_DIR.glob("0022*.md"))
        self.assertEqual([], reserved, f"reserved ADR-0022 file exists: {reserved}")
        index = (ADR_DIR / "README.md").read_text(encoding="utf-8")
        self.assertRegex(
            index,
            r"(?i)ADR[- ]?0022.*(?:reserved|dicadangkan)",
            "ADR-0022 not declared reserved in docs/adr/README.md",
        )

    def test_od_01_and_od_07_are_accepted_with_existing_adr_links(self) -> None:
        path = ROOT / "docs/governance/OPEN-DECISIONS.md"
        text = path.read_text(encoding="utf-8")
        for decision in ("OD-01", "OD-07"):
            with self.subTest(decision=decision):
                row = next((line for line in text.splitlines() if line.startswith(f"| {decision} |")), "")
                self.assertTrue(row, f"missing governance row: {decision}")
                self.assertIn("ACCEPTED", row, f"{decision} is not ACCEPTED")
                links = re.findall(r"\[[^]]+\]\(([^)]+)\)", row)
                adr_links = [link for link in links if "adr/" in link]
                self.assertTrue(adr_links, f"{decision} missing ADR link")
                for link in adr_links:
                    target = (path.parent / link).resolve()
                    self.assertTrue(target.is_file(), f"{decision} ADR link missing target: {link}")


if __name__ == "__main__":
    unittest.main()
