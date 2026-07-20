from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FoundationLifecycleTests(unittest.TestCase):
    def run_make(self, target: str, runtime_root: Path) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["DCIM_RUNTIME_ROOT"] = str(runtime_root)
        for inherited_make_state in ("MAKEFLAGS", "MFLAGS", "MAKEOVERRIDES"):
            environment.pop(inherited_make_state, None)
        return subprocess.run(
            ["make", target],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def test_bootstrap_creates_only_protected_dev_build_material(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"

            result = self.run_make("foundation-bootstrap", runtime_root)

            self.assertEqual(0, result.returncode, result.stderr)
            expected = {
                "dev-build/secrets/postgres-superuser-password",
                "dev-build/secrets/postgres-monitor-password",
                "dev-build/secrets/postgres-smoke-password",
                "dev-build/secrets/grafana-admin-user",
                "dev-build/secrets/grafana-admin-password",
                "dev-build/runtime.env",
            }
            actual = {
                str(path.relative_to(runtime_root))
                for path in runtime_root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(expected, actual)
            self.assertFalse((runtime_root / "integration-ro").exists())
            self.assertFalse((runtime_root / "demo").exists())
            self.assertEqual(0o700, runtime_root.stat().st_mode & 0o777)
            for path in runtime_root.rglob("*"):
                if path.is_dir():
                    expected_mode = 0o700
                elif path.parent.name == "secrets":
                    expected_mode = 0o444
                else:
                    expected_mode = 0o600
                self.assertEqual(expected_mode, path.stat().st_mode & 0o777, path)

    def test_bootstrap_refuses_to_overwrite_existing_material(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"
            first = self.run_make("foundation-bootstrap", runtime_root)
            protected_file = runtime_root / "dev-build/secrets/postgres-smoke-password"
            original = protected_file.read_bytes()

            second = self.run_make("foundation-bootstrap", runtime_root)

            self.assertEqual(0, first.returncode, first.stderr)
            self.assertNotEqual(0, second.returncode)
            self.assertIn("refusing to overwrite", second.stderr.lower())
            self.assertEqual(original, protected_file.read_bytes())

    def test_bootstrap_rejects_runtime_root_inside_repository(self) -> None:
        runtime_root = ROOT / "runtime-test-must-not-exist"

        result = self.run_make("foundation-bootstrap", runtime_root)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("outside repository", result.stderr.lower())
        self.assertFalse(runtime_root.exists())


if __name__ == "__main__":
    unittest.main()
