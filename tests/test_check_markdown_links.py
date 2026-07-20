from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_markdown_links.py"


class MarkdownLinkCheckerTests(unittest.TestCase):
    def run_checker(self, markdown: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy2(SCRIPT, scripts / SCRIPT.name)
            (root / "example.md").write_text(markdown, encoding="utf-8")
            environment = os.environ.copy()
            for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
                environment.pop(name, None)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, env=environment)

            return subprocess.run(
                [sys.executable, str(scripts / SCRIPT.name)],
                cwd=root,
                capture_output=True,
                env=environment,
                text=True,
            )

    def test_missing_links_inside_fenced_code_are_ignored(self) -> None:
        result = self.run_checker(
            """# Template

```md
- [Ordering](./src/ordering/CONTEXT.md)
- [<closed ticket title>](link)
```
"""
        )

        self.assertEqual(0, result.returncode, result.stderr)

    def test_tab_indented_pseudo_fence_does_not_hide_missing_link(self) -> None:
        result = self.run_checker("\t```md\n[Broken](missing.md)\n")

        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("missing target: missing.md", result.stderr)

    def test_backtick_in_fence_info_does_not_hide_missing_link(self) -> None:
        result = self.run_checker("```invalid`info\n[Broken](missing.md)\n")

        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("missing target: missing.md", result.stderr)


if __name__ == "__main__":
    unittest.main()
