from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class WorkflowSafetyTests(unittest.TestCase):
    def texts(self) -> list[tuple[Path, str]]:
        return [(path, path.read_text(encoding="utf-8")) for path in sorted(WORKFLOWS.glob("*.yml"))]

    def test_no_self_hosted_or_dangerous_trigger(self) -> None:
        for path, text in self.texts():
            self.assertNotIn("self-hosted", text, path)
            self.assertNotIn("pull_request_target", text, path)
            self.assertNotIn("workflow_run:", text, path)

    def test_action_references_use_full_commit_sha(self) -> None:
        uses_re = re.compile(r"^\s*uses:\s*[^@\s]+@([^\s#]+)", re.MULTILINE)
        for path, text in self.texts():
            refs = uses_re.findall(text)
            self.assertTrue(refs, path)
            for ref in refs:
                self.assertRegex(ref, r"^[0-9a-f]{40}$", path)

    def test_default_permissions_are_read_only(self) -> None:
        for path, text in self.texts():
            self.assertNotIn("write-all", text, path)
            self.assertRegex(text, r"permissions:\n(?:\s+[a-z-]+:\s+read\n)+", path)

    def test_ci_uses_phase0_synthetic_gate(self) -> None:
        text = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("make phase0-check", text)
        self.assertNotIn("ssh ", text.lower())

    def test_dependency_review_is_fail_closed(self) -> None:
        text = (WORKFLOWS / "dependency-review.yml").read_text(encoding="utf-8")
        self.assertIn("actions/dependency-review-action@", text)
        self.assertNotIn("if: steps.dependency-graph", text)
        self.assertNotIn("Skipping dependency review", text)


if __name__ == "__main__":
    unittest.main()
