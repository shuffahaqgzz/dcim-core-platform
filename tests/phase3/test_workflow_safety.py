from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "services/workflow/src/dcim_workflow"
PROHIBITED_IMPORTS = {"subprocess", "pty", "socket", "httpx", "httpx2", "requests", "aiohttp"}


class WorkflowSafetyTests(unittest.TestCase):
    def test_package_has_no_execution_or_network_capabilities(self) -> None:
        violations: list[str] = []
        for path in sorted(PACKAGE.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".", 1)[0] in PROHIBITED_IMPORTS:
                            violations.append(f"{path.name}:{node.lineno}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = (node.module or "").split(".", 1)[0]
                    if module in PROHIBITED_IMPORTS:
                        violations.append(f"{path.name}:{node.lineno}: from {node.module}")
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                        if node.func.attr == "system" or node.func.attr.startswith("exec"):
                            violations.append(f"{path.name}:{node.lineno}: os.{node.func.attr}")
        self.assertEqual([], violations)


if __name__ == "__main__":
    unittest.main()
