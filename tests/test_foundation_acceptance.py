from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/foundation_acceptance.py"
SPEC = importlib.util.spec_from_file_location("foundation_acceptance", SCRIPT)
assert SPEC and SPEC.loader
FOUNDATION_ACCEPTANCE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FOUNDATION_ACCEPTANCE
SPEC.loader.exec_module(FOUNDATION_ACCEPTANCE)


class FoundationAcceptanceTests(unittest.TestCase):
    def test_clean_acceptance_rejects_preexisting_runtime_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            parent.chmod(0o700)
            runtime_root = parent / "runtime"
            runtime_root.mkdir(mode=0o700)

            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure, "brand new",
            ):
                FOUNDATION_ACCEPTANCE.validate_new_runtime_root(runtime_root)

    def test_clean_acceptance_rejects_unprotected_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            parent.chmod(0o755)
            runtime_root = parent / "runtime"

            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure, "unsafe writable",
            ):
                FOUNDATION_ACCEPTANCE.validate_new_runtime_root(runtime_root)

    def test_clean_acceptance_rejects_unsafe_writable_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "owner-only"
            parent.mkdir(mode=0o700)
            runtime_root = parent / "runtime"

            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure, "unsafe writable",
            ):
                FOUNDATION_ACCEPTANCE.validate_new_runtime_root(runtime_root)

    def test_clean_acceptance_rejects_normal_runtime_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            state_home = temporary / "state"
            state_home.mkdir(mode=0o700)
            runtime_root = state_home / "dcim-core-platform/runtime"
            runtime_root.parent.mkdir(mode=0o700)
            with mock.patch.dict(os.environ, {"XDG_STATE_HOME": str(state_home)}):
                with self.assertRaisesRegex(
                    FOUNDATION_ACCEPTANCE.AcceptanceFailure, "normal runtime root",
                ):
                    FOUNDATION_ACCEPTANCE.validate_new_runtime_root(runtime_root)

    def test_acceptance_project_name_is_strictly_synthetic(self) -> None:
        self.assertEqual(
            "dcim-build-acceptance-abcdef123456",
            FOUNDATION_ACCEPTANCE.validate_project_name(
                "dcim-build-acceptance-abcdef123456",
            ),
        )
        for name in ("dcim-build", "dcim-demo", "dcim-build-acceptance-short"):
            with self.subTest(name=name):
                with self.assertRaises(FOUNDATION_ACCEPTANCE.AcceptanceFailure):
                    FOUNDATION_ACCEPTANCE.validate_project_name(name)

    def test_clean_acceptance_rejects_remote_docker_environment(self) -> None:
        with mock.patch.dict(os.environ, {"DOCKER_HOST": "ssh://synthetic"}, clear=False):
            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure, "Docker remote",
            ):
                FOUNDATION_ACCEPTANCE.acceptance_environment(
                    Path("/synthetic/runtime"),
                    "dcim-build-acceptance-abcdef123456",
                )

    def test_clean_acceptance_requires_local_docker_context(self) -> None:
        remote = subprocess.CompletedProcess(
            ["docker"], 0, '"ssh://synthetic"\n', "",
        )
        local = subprocess.CompletedProcess(
            ["docker"], 0, '"unix:///var/run/docker.sock"\n', "",
        )
        with mock.patch.object(FOUNDATION_ACCEPTANCE.subprocess, "run", return_value=remote):
            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure, "local Unix socket",
            ):
                FOUNDATION_ACCEPTANCE.validate_local_docker_context(os.environ.copy())
        with mock.patch.object(FOUNDATION_ACCEPTANCE.subprocess, "run", return_value=local):
            FOUNDATION_ACCEPTANCE.validate_local_docker_context(os.environ.copy())

    def test_clean_acceptance_requires_commit_bound_worktree(self) -> None:
        dirty = subprocess.CompletedProcess(["git"], 1, "", "")
        clean = subprocess.CompletedProcess(["git"], 0, "", "")
        with mock.patch.object(
            FOUNDATION_ACCEPTANCE.subprocess,
            "run",
            side_effect=[dirty],
        ):
            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure, "commit-bound",
            ):
                FOUNDATION_ACCEPTANCE.assert_commit_bound_tree(os.environ.copy())
        with mock.patch.object(
            FOUNDATION_ACCEPTANCE.subprocess,
            "run",
            side_effect=[clean, clean, clean],
        ) as runner:
            FOUNDATION_ACCEPTANCE.assert_commit_bound_tree(os.environ.copy())

        calls = [call.args[0] for call in runner.call_args_list]
        self.assertEqual(["git", "diff", "--quiet"], calls[0])
        self.assertEqual(["git", "diff", "--cached", "--quiet"], calls[1])
        self.assertIn("docs/phase1", calls[2])
        self.assertIn("scripts", calls[2])
        self.assertIn("tests", calls[2])

    def test_clean_acceptance_ignores_unrelated_untracked_workspace_files(self) -> None:
        clean = subprocess.CompletedProcess(["git"], 0, "", "")
        unrelated_untracked = subprocess.CompletedProcess(["git"], 0, "", "")
        with mock.patch.object(
            FOUNDATION_ACCEPTANCE.subprocess,
            "run",
            side_effect=[clean, clean, unrelated_untracked],
        ):
            FOUNDATION_ACCEPTANCE.assert_commit_bound_tree(os.environ.copy())

    def test_clean_acceptance_rejects_untracked_closure_package_files(self) -> None:
        clean = subprocess.CompletedProcess(["git"], 0, "", "")
        untracked = subprocess.CompletedProcess(
            ["git"], 0, "docs/phase1/synthetic-new-evidence.md\n", "",
        )
        with mock.patch.object(
            FOUNDATION_ACCEPTANCE.subprocess,
            "run",
            side_effect=[clean, clean, untracked],
        ):
            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure,
                "commit-bound",
            ):
                FOUNDATION_ACCEPTANCE.assert_commit_bound_tree(os.environ.copy())

    def test_preexisting_acceptance_namespace_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            fake_docker = fake_bin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/sh
                    case "$1 $2" in
                      "ps -a") printf '%s\\n' synthetic-container ;;
                      "network ls") ;;
                      "volume ls") printf '%s\\n' synthetic-volume ;;
                      "image ls") ;;
                    esac
                    """
                ),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"

            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure,
                "pre-existing acceptance Compose namespace",
            ):
                FOUNDATION_ACCEPTANCE.assert_no_existing_project_resources(
                    "dcim-build-acceptance-abcdef123456", environment,
                )

    def test_preexisting_acceptance_image_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            fake_docker = fake_bin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/sh
                    case "$1 $2" in
                      "ps -a") ;;
                      "network ls") ;;
                      "volume ls") ;;
                      "image ls") printf '%s\\n' synthetic-image ;;
                    esac
                    """
                ),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"

            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure,
                "pre-existing acceptance Compose namespace",
            ):
                FOUNDATION_ACCEPTANCE.assert_no_existing_project_resources(
                    "dcim-build-acceptance-abcdef123456", environment,
                )

    def test_preexisting_acceptance_named_image_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            fake_docker = fake_bin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/sh
                    project=dcim-build-acceptance-abcdef123456
                    case "$1 $2" in
                      "ps -a") ;;
                      "network ls") ;;
                      "volume ls") ;;
                      "image ls")
                        case "$*" in
                          *"--filter label=com.docker.compose.project="*) ;;
                          *) printf '%s\\t%s\\n' "$project/stale:synthetic" synthetic-image ;;
                        esac
                        ;;
                    esac
                    """
                ),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"

            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure,
                "pre-existing acceptance Compose namespace",
            ):
                FOUNDATION_ACCEPTANCE.assert_no_existing_project_resources(
                    "dcim-build-acceptance-abcdef123456", environment,
                )

    def test_preexisting_unlabeled_acceptance_network_and_volume_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            fake_docker = fake_bin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/sh
                    project=dcim-build-acceptance-abcdef123456
                    case "$1 $2" in
                      "ps -a") ;;
                      "network ls")
                        case "$*" in
                          *"--filter label=com.docker.compose.project="*) ;;
                          *) printf '%s\\t%s\\n' "$project-data" synthetic-network ;;
                        esac
                        ;;
                      "volume ls")
                        case "$*" in
                          *"--filter label=com.docker.compose.project="*) ;;
                          *) printf '%s\\t%s\\n' "$project-postgres-data" "$project-postgres-data" ;;
                        esac
                        ;;
                      "image ls") ;;
                    esac
                    """
                ),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"

            counts = FOUNDATION_ACCEPTANCE.project_resource_counts(
                "dcim-build-acceptance-abcdef123456", environment,
            )

            self.assertEqual(1, counts["networks"])
            self.assertEqual(1, counts["volumes"])
            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure,
                "pre-existing acceptance Compose namespace",
            ):
                FOUNDATION_ACCEPTANCE.assert_no_existing_project_resources(
                    "dcim-build-acceptance-abcdef123456", environment,
                )

    def test_preexisting_normal_runtime_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            fake_docker = fake_bin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/sh
                    project=dcim-build
                    case "$1 $2" in
                      "ps -a")
                        case "$*" in
                          *"--filter label=com.docker.compose.project=$project"*) printf '%s\\n' normal-container ;;
                          *) printf '%s\\t%s\\n' "$project-postgres-1" normal-container ;;
                        esac
                        ;;
                      "network ls")
                        case "$*" in
                          *"--filter label=com.docker.compose.project=$project"*) printf '%s\\n' normal-network ;;
                          *) printf '%s\\t%s\\n' "$project-data" normal-network ;;
                        esac
                        ;;
                      "volume ls")
                        case "$*" in
                          *"--filter label=com.docker.compose.project=$project"*) printf '%s\\n' "$project-postgres-data" ;;
                          *) printf '%s\\t%s\\n' "$project-postgres-data" "$project-postgres-data" ;;
                        esac
                        ;;
                      "image ls")
                        case "$*" in
                          *"--filter label=com.docker.compose.project=$project"*) printf '%s\\n' normal-image ;;
                          *) printf '%s\\t%s\\n' "$project/postgres:synthetic" normal-image ;;
                        esac
                        ;;
                    esac
                    """
                ),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"

            counts = FOUNDATION_ACCEPTANCE.project_resource_counts(
                "dcim-build", environment,
            )

            self.assertEqual(1, counts["containers"])
            self.assertEqual(1, counts["networks"])
            self.assertEqual(1, counts["volumes"])
            self.assertEqual(1, counts["images"])
            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure,
                "pre-existing normal dcim-build runtime state",
            ):
                FOUNDATION_ACCEPTANCE.assert_no_normal_runtime_state(environment)

    def test_run_acceptance_checks_normal_runtime_state_before_acceptance_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"

            with (
                mock.patch.object(FOUNDATION_ACCEPTANCE, "git_commit", return_value="abc123"),
                mock.patch.object(
                    FOUNDATION_ACCEPTANCE,
                    "validate_new_runtime_root",
                    return_value=runtime_root,
                ),
                mock.patch.object(FOUNDATION_ACCEPTANCE, "assert_commit_bound_tree"),
                mock.patch.object(FOUNDATION_ACCEPTANCE, "validate_local_docker_context"),
                mock.patch.object(
                    FOUNDATION_ACCEPTANCE,
                    "assert_no_normal_runtime_state",
                    side_effect=FOUNDATION_ACCEPTANCE.AcceptanceFailure(
                        "pre-existing normal dcim-build runtime state detected "
                        "(containers=1, networks=0, volumes=0), images=0",
                    ),
                ),
                mock.patch.object(FOUNDATION_ACCEPTANCE, "assert_no_existing_project_resources") as acceptance_check,
                mock.patch("sys.stdout", new_callable=io.StringIO),
                mock.patch("sys.stderr", new_callable=io.StringIO),
            ):
                result = FOUNDATION_ACCEPTANCE.run_acceptance(
                    runtime_root,
                    "dcim-build-acceptance-abcdef123456",
                )

            report = json.loads(
                (runtime_root / "dev-build/evidence/clean-runtime-acceptance.json").read_text(
                    encoding="utf-8",
                ),
            )

            self.assertEqual(1, result)
            self.assertEqual("fail", report["result"])
            self.assertIn("normal dcim-build runtime state", report["failure_reason"])
            acceptance_check.assert_not_called()

    def test_normal_runtime_state_detection_does_not_count_acceptance_names(self) -> None:
        self.assertTrue(
            FOUNDATION_ACCEPTANCE.project_resource_name_matches(
                "dcim-build-postgres-1",
                "dcim-build",
            ),
        )
        self.assertFalse(
            FOUNDATION_ACCEPTANCE.project_resource_name_matches(
                "dcim-build-acceptance-abcdef123456-postgres-1",
                "dcim-build",
            ),
        )
        self.assertTrue(
            FOUNDATION_ACCEPTANCE.project_resource_name_matches(
                "dcim-build-acceptance-abcdef123456-postgres-1",
                "dcim-build-acceptance-abcdef123456",
            ),
        )

    def test_acceptance_inventory_requires_exact_project_resources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            fake_docker = fake_bin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/sh
                    project=dcim-build-acceptance-abcdef123456
                    case "$1 $2" in
                      "ps -a")
                        printf '%s\\n' postgres kafka postgres-exporter kafka-jmx-exporter prometheus grafana
                        ;;
                      "network ls")
                        printf '%s\\n' "$project-data" "$project-observability"
                        ;;
                      "volume ls")
                        printf '%s\\n' "$project-postgres-data" "$project-kafka-data" "$project-prometheus-data"
                        ;;
                      "image ls")
                        ;;
                    esac
                    """
                ),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"

            FOUNDATION_ACCEPTANCE.assert_expected_project_inventory(
                "dcim-build-acceptance-abcdef123456", environment,
            )

    def test_acceptance_override_is_external_and_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"

            override = FOUNDATION_ACCEPTANCE.write_acceptance_compose_override(
                runtime_root,
                "dcim-build-acceptance-abcdef123456",
            )

            self.assertEqual(runtime_root / "dev-build/acceptance-compose.override.yaml", override)
            self.assertNotEqual(ROOT, override)
            content = override.read_text(encoding="utf-8")
            self.assertIn("dcim-build-acceptance-abcdef123456-data", content)
            with self.assertRaises(FOUNDATION_ACCEPTANCE.AcceptanceFailure):
                FOUNDATION_ACCEPTANCE.write_acceptance_compose_override(
                    runtime_root,
                    "dcim-build-prod",
                )

    def test_acceptance_smoke_environment_includes_external_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"
            override = runtime_root / "dev-build/acceptance-compose.override.yaml"
            base_environment = {
                "DCIM_RUNTIME_ROOT": str(runtime_root),
                "COMPOSE_PROJECT_NAME": "dcim-build-acceptance-abcdef123456",
            }

            environment = FOUNDATION_ACCEPTANCE.smoke_environment(
                base_environment,
                override,
            )

            self.assertEqual(str(override), environment["DCIM_COMPOSE_OVERRIDE"])
            self.assertNotIn("DCIM_COMPOSE_OVERRIDE", base_environment)

    def test_acceptance_environment_clears_inherited_compose_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"
            with mock.patch.dict(
                os.environ,
                {"DCIM_COMPOSE_OVERRIDE": str(runtime_root / "stale.yaml")},
                clear=True,
            ):
                environment = FOUNDATION_ACCEPTANCE.acceptance_environment(
                    runtime_root,
                    "dcim-build-acceptance-abcdef123456",
                )

        self.assertNotIn("DCIM_COMPOSE_OVERRIDE", environment)
        self.assertEqual(
            "dcim-build-acceptance-abcdef123456",
            environment["COMPOSE_PROJECT_NAME"],
        )

    def test_acceptance_inventory_rejects_project_labeled_images(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            fake_docker = fake_bin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/sh
                    project=dcim-build-acceptance-abcdef123456
                    case "$1 $2" in
                      "ps -a")
                        printf '%s\\n' postgres kafka postgres-exporter kafka-jmx-exporter prometheus grafana
                        ;;
                      "network ls")
                        printf '%s\\n' "$project-data" "$project-observability"
                        ;;
                      "volume ls")
                        printf '%s\\n' "$project-postgres-data" "$project-kafka-data" "$project-prometheus-data"
                        ;;
                      "image ls")
                        printf '%s\\n' synthetic-image
                        ;;
                    esac
                    """
                ),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"

            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure,
                "unexpected acceptance image inventory",
            ):
                FOUNDATION_ACCEPTANCE.assert_expected_project_inventory(
                    "dcim-build-acceptance-abcdef123456", environment,
                )

    def test_acceptance_report_records_public_safe_failure_reason(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"
            FOUNDATION_ACCEPTANCE.write_acceptance_report(
                runtime_root,
                commit="abc123",
                started_utc="2026-07-21T10:00:00Z",
                finished_utc="2026-07-21T10:00:03Z",
                result="fail",
                records=[{
                    "step": "foundation-policy",
                    "exit_code": 1,
                    "duration_seconds": 0.2,
                }],
                failure_reason="foundation-policy failed with exit code 1",
            )

            report = json.loads(
                (runtime_root / "dev-build/evidence/clean-runtime-acceptance.json").read_text(
                    encoding="utf-8",
                ),
            )

            self.assertEqual("fail", report["result"])
            self.assertEqual(
                "foundation-policy failed with exit code 1",
                report["failure_reason"],
            )
            serialized = json.dumps(report)
            for prohibited in ("hostname", "runtime_root", "environment", "credential", "secret"):
                self.assertNotIn(prohibited, serialized.lower())

    def test_run_acceptance_stops_partial_services_when_startup_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"
            executed_steps: list[str] = []

            def run_step(
                label: str,
                _command: list[str],
                **_kwargs: object,
            ) -> str:
                executed_steps.append(label)
                if label == "foundation-up":
                    raise FOUNDATION_ACCEPTANCE.AcceptanceFailure(
                        "foundation-up failed with exit code 1",
                    )
                return "{}" if label == "compose-config" else ""

            with (
                mock.patch.object(FOUNDATION_ACCEPTANCE, "git_commit", return_value="abc123"),
                mock.patch.object(
                    FOUNDATION_ACCEPTANCE,
                    "validate_new_runtime_root",
                    return_value=runtime_root,
                ),
                mock.patch.object(FOUNDATION_ACCEPTANCE, "assert_commit_bound_tree"),
                mock.patch.object(FOUNDATION_ACCEPTANCE, "validate_local_docker_context"),
                mock.patch.object(FOUNDATION_ACCEPTANCE, "assert_no_normal_runtime_state"),
                mock.patch.object(FOUNDATION_ACCEPTANCE, "assert_no_existing_project_resources"),
                mock.patch.object(FOUNDATION_ACCEPTANCE, "run_step", side_effect=run_step),
                mock.patch("sys.stdout", new_callable=io.StringIO),
                mock.patch("sys.stderr", new_callable=io.StringIO),
            ):
                result = FOUNDATION_ACCEPTANCE.run_acceptance(
                    runtime_root,
                    "dcim-build-acceptance-abcdef123456",
                )

            self.assertEqual(1, result)
            self.assertIn("foundation-up", executed_steps)
            self.assertIn("foundation-stop-after-failure", executed_steps)

    def test_run_acceptance_records_early_validated_root_failure_reason(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"

            with (
                mock.patch.object(
                    FOUNDATION_ACCEPTANCE,
                    "validate_new_runtime_root",
                    return_value=runtime_root,
                ),
                mock.patch.object(
                    FOUNDATION_ACCEPTANCE,
                    "assert_commit_bound_tree",
                    side_effect=FOUNDATION_ACCEPTANCE.AcceptanceFailure(
                        "clean acceptance requires a clean commit-bound worktree",
                    ),
                ),
                mock.patch("sys.stdout", new_callable=io.StringIO),
                mock.patch("sys.stderr", new_callable=io.StringIO),
            ):
                result = FOUNDATION_ACCEPTANCE.run_acceptance(
                    runtime_root,
                    "dcim-build-acceptance-abcdef123456",
                )

            report = json.loads(
                (runtime_root / "dev-build/evidence/clean-runtime-acceptance.json").read_text(
                    encoding="utf-8",
                ),
            )

            self.assertEqual(1, result)
            self.assertEqual("fail", report["result"])
            self.assertEqual(
                "clean acceptance requires a clean commit-bound worktree",
                report["failure_reason"],
            )

    def test_preflight_target_is_not_clean_acceptance_proof(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        preflight_line = next(
            line for line in makefile.splitlines() if line.startswith("preflight:")
        )

        self.assertNotIn("foundation-clean-acceptance", preflight_line)

    def test_preflight_evidence_summary_requires_current_passing_recovery(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        recipe = makefile.split("foundation-evidence-summary:\n", maxsplit=1)[1]
        recipe = recipe.split("\n\nfoundation-clean-acceptance:", maxsplit=1)[0]

        self.assertIn("--require-modes 'recovery'", recipe)
        self.assertIn("--require-pass", recipe)
        self.assertIn("--strict-commit", recipe)

    def test_clean_acceptance_make_target_defers_runtime_validation_to_python(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        recipe = makefile.split("foundation-clean-acceptance:\n", maxsplit=1)[1]
        recipe = recipe.split("\n\ncompile:", maxsplit=1)[0]

        self.assertIn("export DCIM_RUNTIME_ROOT", makefile)
        self.assertNotIn("FOUNDATION_ACCEPTANCE_PROJECT", makefile)
        self.assertEqual("\t$(PYTHON) scripts/foundation_acceptance.py", recipe)

    def test_make_lifecycle_does_not_render_runtime_root_override_as_shell_syntax(self) -> None:
        payload = "/tmp/dcim'; printf MAKE_INJECTION_MARKER >&2; :'"
        for target in (
            "foundation-bootstrap",
            "foundation-recovery",
            "foundation-evidence-summary",
            "foundation-clean-acceptance",
        ):
            with self.subTest(target=target):
                result = subprocess.run(
                    ["make", "-n", target, f"DCIM_RUNTIME_ROOT={payload}"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                self.assertEqual(0, result.returncode, result.stderr)
                rendered = result.stdout + result.stderr
                self.assertNotIn("MAKE_INJECTION_MARKER", rendered)
                self.assertNotIn(payload, rendered)

    def test_clean_acceptance_runtime_root_can_come_from_environment(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"DCIM_RUNTIME_ROOT": "/tmp/dcim-clean-acceptance/synthetic"},
            clear=True,
        ):
            self.assertEqual(
                Path("/tmp/dcim-clean-acceptance/synthetic"),
                FOUNDATION_ACCEPTANCE.requested_runtime_root(None),
            )

        self.assertEqual(
            Path("/explicit/runtime"),
            FOUNDATION_ACCEPTANCE.requested_runtime_root(Path("/explicit/runtime")),
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                FOUNDATION_ACCEPTANCE.AcceptanceFailure,
                "DCIM_RUNTIME_ROOT or --runtime-root",
            ):
                FOUNDATION_ACCEPTANCE.requested_runtime_root(None)

    def test_normal_make_lifecycle_does_not_expose_acceptance_namespace_override(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

        self.assertNotIn("FOUNDATION_PROJECT_NAME", makefile)
        self.assertNotIn("'$(DCIM_RUNTIME_ROOT)'", makefile)
        self.assertIn("COMPOSE_PROJECT_NAME='dcim-build'", makefile)
        self.assertIn(
            "FOUNDATION_SMOKE_CMD := env -u DCIM_COMPOSE_OVERRIDE "
            "COMPOSE_PROJECT_NAME='dcim-build' "
            "$(PYTHON) scripts/foundation_smoke.py",
            makefile,
        )
        self.assertIn(
            "foundation-grafana-url:\n\t$(FOUNDATION_SMOKE_CMD) grafana-url",
            makefile,
        )
        self.assertIn(
            "foundation-smoke: foundation-up\n\t$(FOUNDATION_SMOKE_CMD) fast",
            makefile,
        )
        self.assertIn(
            "foundation-recovery: foundation-up\n\t$(FOUNDATION_SMOKE_CMD) recovery",
            makefile,
        )


if __name__ == "__main__":
    unittest.main()
