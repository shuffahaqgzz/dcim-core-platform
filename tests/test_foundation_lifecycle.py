from __future__ import annotations

import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest

from scripts.protected_runtime import ensure_protected_directory, external_runtime_root, protected_runtime_path


ROOT = Path(__file__).resolve().parents[1]
POSTGRES_INIT = ROOT / "deploy/compose/dev-build/config/postgres/init-roles.sh"
COMPOSE = ROOT / "deploy/compose/dev-build/compose.yaml"
PSQL_ARGV_SECRET = re.compile(
    r"(?:(?:--set|--variable)(?:\s+|=)|-v(?:\s+|=)?)"
    r"\s*[^\s=]+\s*=\s*[\"']?\$"
)


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

    def test_workspace_and_make_defaults_share_xdg_runtime_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            state_home = temporary / "state"
            expected = state_home / "dcim-core-platform/runtime"
            environment = os.environ.copy()
            environment.pop("DCIM_RUNTIME_ROOT", None)
            environment["HOME"] = str(temporary / "home")
            environment["XDG_STATE_HOME"] = str(state_home)
            for inherited_make_state in ("MAKEFLAGS", "MFLAGS", "MAKEOVERRIDES"):
                environment.pop(inherited_make_state, None)

            workspace = subprocess.run(
                [str(ROOT / "scripts/bootstrap-dev.sh")],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            make_default = subprocess.run(
                [
                    "make", "--no-print-directory", "-s",
                    "--eval=print-runtime:;@printf '%s\\n' '$(DCIM_RUNTIME_ROOT)'",
                    "print-runtime",
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )

            self.assertEqual(0, workspace.returncode, workspace.stderr)
            self.assertEqual(0, make_default.returncode, make_default.stderr)
            self.assertEqual(str(expected), make_default.stdout.strip())
            self.assertTrue((expected / "dev-build").is_dir())

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

    def test_bootstrap_rejects_symlinked_runtime_plane(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            runtime_root = base / "runtime"
            redirect = base / "redirect"
            runtime_root.mkdir()
            runtime_root.chmod(0o700)
            redirect.mkdir()
            (runtime_root / "dev-build").symlink_to(redirect, target_is_directory=True)

            result = self.run_make("foundation-bootstrap", runtime_root)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("symbolic link", result.stderr.lower())
            self.assertEqual([], list(redirect.iterdir()))

    def test_postgres_init_never_places_secret_values_in_process_arguments(self) -> None:
        script = POSTGRES_INIT.read_text(encoding="utf-8")

        self.assertIsNone(
            PSQL_ARGV_SECRET.search(script),
            "PostgreSQL role secrets must not enter psql argv",
        )

    def test_postgres_secret_argv_guard_covers_psql_option_forms(self) -> None:
        for arguments in (
            'psql --set=role_password="$value"',
            "psql --set role_password=$value",
            "psql --variable=role_password=$value",
            "psql --variable role_password=$value",
            "psql -v role_password=$value",
            "psql -vrole_password=$value",
        ):
            with self.subTest(arguments=arguments):
                self.assertIsNotNone(PSQL_ARGV_SECRET.search(arguments))

    def test_protected_runtime_child_rejects_escape_components(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"
            runtime_root.mkdir()

            for parts in (("..", "escape"), ("dev-build/../escape",), ("/tmp/escape",)):
                with self.subTest(parts=parts), self.assertRaises(ValueError):
                    protected_runtime_path(runtime_root, *parts)

    def test_protected_runtime_rejects_home_and_does_not_chmod_existing_root(self) -> None:
        with self.assertRaises(ValueError):
            external_runtime_root(Path.home())
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "shared"
            runtime_root.mkdir(mode=0o755)
            runtime_root.chmod(0o755)

            with self.assertRaises(ValueError):
                ensure_protected_directory(runtime_root, "dev-build")

            self.assertEqual(0o755, runtime_root.stat().st_mode & 0o777)

    def test_artifact_fetch_rejects_symlinked_external_directory_before_network(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            runtime_root = base / "runtime"
            plane = runtime_root / "dev-build"
            redirect = base / "redirect"
            plane.mkdir(parents=True)
            runtime_root.chmod(0o700)
            plane.chmod(0o700)
            redirect.mkdir()
            (plane / "artifacts").symlink_to(redirect, target_is_directory=True)

            result = self.run_make("foundation-artifacts", runtime_root)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("symbolic link", result.stderr.lower())
            self.assertEqual([], list(redirect.iterdir()))

    def test_plain_compose_without_profiles_selects_no_services(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"
            bootstrap = self.run_make("foundation-bootstrap", runtime_root)
            self.assertEqual(0, bootstrap.returncode, bootstrap.stderr)
            image_id = "sha256:" + "a" * 64
            image_environment = runtime_root / "dev-build/images.env"
            image_environment.write_text(
                "\n".join([
                    f"DCIM_POSTGRES_IMAGE={image_id}",
                    f"DCIM_KAFKA_IMAGE={image_id}",
                    f"DCIM_GRAFANA_IMAGE={image_id}",
                    f"DCIM_PROMETHEUS_IMAGE={image_id}",
                    f"DCIM_POSTGRES_EXPORTER_IMAGE={image_id}",
                ]) + "\n",
                encoding="utf-8",
            )
            runtime_environment = runtime_root / "dev-build/runtime.env"
            runtime_environment.write_text(
                "\n".join(
                    line for line in runtime_environment.read_text(encoding="utf-8").splitlines()
                    if not line.startswith("DCIM_RUNTIME_ROOT=")
                ) + "\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["DCIM_RUNTIME_ROOT"] = str(runtime_root)

            result = subprocess.run(
                [
                    "docker", "compose",
                    "--env-file", str(runtime_root / "dev-build/runtime.env"),
                    "--env-file", str(image_environment),
                    "-f", str(COMPOSE),
                    "config", "--services",
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("", result.stdout.strip())

    def test_reset_is_unavailable_in_ci(self) -> None:
        environment = os.environ.copy()
        environment["CI"] = "true"

        result = subprocess.run(
            ["python3", str(ROOT / "scripts/foundation_reset.py")],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("unavailable in CI", result.stderr)

    def test_reset_rejects_unexpected_labeled_volume_before_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake_bin = Path(directory) / "bin"
            fake_bin.mkdir()
            fake_docker = fake_bin / "docker"
            fake_docker.write_text(
                "#!/bin/sh\nprintf '%s\\n' dcim-build-postgres-data dcim-build-unexpected\n",
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            command = (
                f"PATH={shlex.quote(str(fake_bin))}:$PATH "
                f"python3 {shlex.quote(str(ROOT / 'scripts/foundation_reset.py'))}"
            )
            environment = os.environ.copy()
            environment.pop("CI", None)

            result = subprocess.run(
                ["script", "-qec", command, "/dev/null"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("unexpected labeled volume", result.stdout.lower())
            self.assertNotIn("type 'reset dcim-build'", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
