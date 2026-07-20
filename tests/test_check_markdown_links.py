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
    def test_missing_links_inside_fenced_code_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy2(SCRIPT, scripts / SCRIPT.name)
            (root / "example.md").write_text(
                """# Template

```md
- [Ordering](./src/ordering/CONTEXT.md)
- [<closed ticket title>](link)
```
""",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
                environment.pop(name, None)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, env=environment)

            result = subprocess.run(
                [sys.executable, str(scripts / SCRIPT.name)],
                cwd=root,
                capture_output=True,
                env=environment,
                text=True,
            )

            self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
