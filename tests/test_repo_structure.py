from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RepositoryStructureTests(unittest.TestCase):
    def test_required_governance_files_exist(self) -> None:
        required = [
            "AGENTS.md",
            "DATA-HANDLING.md",
            "SECURITY.md",
            "docs/baseline/DEVELOPMENT-BASELINE.md",
            "docs/governance/CONDITIONS-REGISTER.md",
            "docs/governance/OPEN-DECISIONS.md",
            "docs/plan/DEV-BOOTSTRAP-V0.1.md",
            ".codex/config.toml",
        ]
        for relative in required:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_codex_toml_files_parse(self) -> None:
        for path in sorted((ROOT / ".codex").rglob("*.toml")):
            with self.subTest(path=path.relative_to(ROOT)):
                tomllib.loads(path.read_text(encoding="utf-8"))

    def test_each_skill_has_metadata(self) -> None:
        for path in sorted((ROOT / ".agents/skills").glob("*/SKILL.md")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertTrue(text.startswith("---\n"))
                self.assertIn("\nname:", text)
                self.assertIn("\ndescription:", text)


if __name__ == "__main__":
    unittest.main()
