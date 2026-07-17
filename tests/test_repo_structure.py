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

    def test_phase0_mandatory_files_exist(self) -> None:
        required = [
            "PROJECT-CHARTER.md", "SCOPE-DEV.md", "KNOWN-LIMITATIONS.md", "ROADMAP.md",
            "docs/architecture/runtime-plane-separation.md",
            "docs/security/read-only-connector-policy.md",
            "docs/security/production-source-safety-checklist.md",
            "docs/security/emergency-collector-kill-switch.md",
            "docs/security/demo-sanitization-policy.md",
            "docs/security/threat-model-phase0.md",
            "docs/templates/private-source-authorization-register.template.md",
            "docs/templates/source-inventory.template.md",
            "docs/phase0/repository-preflight-report.md",
            "docs/phase0/phase0-checklist.md", "docs/phase0/dev-entry-gate.md",
            "docs/phase0/evidence-index.md", "docs/phase0/staging-handover-contract.md",
            "scripts/sanitize_demo_data.py", "scripts/check_public_repo_safety.py",
            "tests/test_sanitize_demo_data.py", "tests/test_check_public_repo_safety.py",
            ".github/workflows/ci.yml", ".github/workflows/security-scan.yml",
        ]
        for relative in required:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_each_skill_has_metadata(self) -> None:
        for path in sorted((ROOT / ".agents/skills").glob("*/SKILL.md")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertTrue(text.startswith("---\n"))
                self.assertIn("\nname:", text)
                self.assertIn("\ndescription:", text)


if __name__ == "__main__":
    unittest.main()
