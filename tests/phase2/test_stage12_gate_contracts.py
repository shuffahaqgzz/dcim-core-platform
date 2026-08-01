from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class Stage12GateContractTests(unittest.TestCase):
    def test_phase2_deps_creates_venv_and_uses_its_python_for_pydantic(self) -> None:
        # Given: a fake externally-managed system Python that rejects pip and can
        # create an isolated venv whose interpreter records its invocations.
        with tempfile.TemporaryDirectory(prefix="task12-phase2-deps-") as temporary:
            scratch = Path(temporary)
            system_log = scratch / "system-python.log"
            venv_log = scratch / "venv-python.log"
            phase2_venv = scratch / "phase2-venv"
            fake_system_python = scratch / "python3"
            fake_system_python.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$*\" >> \"$PHASE2_SYSTEM_PYTHON_LOG\"\n"
                "if [ \"$1\" = '-m' ] && [ \"$2\" = 'pip' ]; then\n"
                "  echo 'system pip must not be invoked' >&2\n"
                "  exit 73\n"
                "fi\n"
                "if [ \"$1\" = '-m' ] && [ \"$2\" = 'venv' ]; then\n"
                "  mkdir -p \"$3/bin\"\n"
                "  printf '%s\\n' '#!/bin/sh' 'printf \"%s\\\\n\" \"$*\" >> \"$PHASE2_VENV_PYTHON_LOG\"' 'exit 0' > \"$3/bin/python\"\n"
                "  chmod +x \"$3/bin/python\"\n"
                "  exit 0\n"
                "fi\n"
                "exit 72\n",
                encoding="utf-8",
            )
            fake_system_python.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{scratch}{os.pathsep}{environment['PATH']}"
            environment["PYTHON"] = str(fake_system_python)
            environment["PHASE2_VENV"] = str(phase2_venv)
            environment["PHASE2_SYSTEM_PYTHON_LOG"] = str(system_log)
            environment["PHASE2_VENV_PYTHON_LOG"] = str(venv_log)

            # When: the dependency target prepares the configured isolated venv.
            result = subprocess.run(
                ["make", "phase2-deps"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

            # Then: only venv creation uses the system interpreter; Pydantic is
            # installed with the created venv interpreter at the exact pin.
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((phase2_venv / "bin" / "python").is_file())
            self.assertEqual(
                system_log.read_text(encoding="utf-8").splitlines(),
                [f"-m venv {phase2_venv}"],
            )
            self.assertEqual(
                venv_log.read_text(encoding="utf-8").splitlines(),
                ["-m pip install pydantic==2.9.2"],
            )

    def test_phase2_test_fails_cleanly_when_venv_is_absent(self) -> None:
        # Given: the configured Phase 2 interpreter does not exist.
        with tempfile.TemporaryDirectory(prefix="task12-missing-venv-") as temporary:
            missing_python = Path(temporary) / "missing-venv" / "bin" / "python"
            environment = os.environ.copy()
            environment["PHASE2_PYTHON"] = str(missing_python)

            # When: a new checkout invokes the public Phase 2 test target.
            result = subprocess.run(
                ["make", "phase2-test"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

            # Then: Make gives the bootstrap action without a shell traceback.
            combined = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("run make phase2-deps", combined)
            self.assertNotIn("No such file or directory", combined)
            self.assertNotIn("Traceback", combined)

    def test_phase2_test_fails_cleanly_when_pydantic_is_unavailable(self) -> None:
        # Given: an isolated python3 shim that records every interpreter invocation
        # and suppresses site-packages to make Pydantic unavailable deterministically.
        with tempfile.TemporaryDirectory(prefix="task12-python-guard-") as temporary:
            scratch = Path(temporary)
            record = scratch / "python-args.log"
            fake_python = scratch / "python3"
            fake_python.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$*\" >> \"$PYTHON_ARGS_LOG\"\n"
                "if [ \"$1\" = '-m' ] && [ \"$2\" = 'unittest' ]; then exit 77; fi\n"
                "exec \"$REAL_PYTHON\" -S \"$@\"\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{scratch}{os.pathsep}{environment['PATH']}"
            environment["PYTHON_ARGS_LOG"] = str(record)
            environment["REAL_PYTHON"] = sys.executable
            environment["PHASE2_PYTHON"] = str(fake_python)

            # When: the real Makefile target runs through the missing-dependency shim.
            result = subprocess.run(
                ["make", "phase2-test"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

            # Then: the guard gives actionable guidance and unittest never starts.
            combined = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("run make phase2-deps", combined)
            self.assertNotIn("Traceback", combined)
            self.assertNotIn("ModuleNotFoundError", combined)
            invocations = record.read_text(encoding="utf-8").splitlines()
            self.assertTrue(invocations)
            self.assertFalse(any("-m unittest" in invocation for invocation in invocations))

    def test_phase2_test_dry_run_retains_required_discovery_command(self) -> None:
        # Given: the Makefile recipe rendered from the recursive Make environment
        # used by phase2-check's unit-test stage.
        environment = os.environ.copy()
        environment["MAKELEVEL"] = "1"
        environment["MAKEFLAGS"] = "w"
        result = subprocess.run(
            ["make", "-n", "phase2-test"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        # Then: the mandated unittest discovery command remains the next recipe line.
        self.assertEqual(result.returncode, 0)
        lines = [line for line in result.stdout.splitlines() if not line.startswith("make[")]
        self.assertGreaterEqual(len(lines), 3)
        self.assertEqual(lines[2], ".venv/bin/python -m unittest discover -s tests/phase2 -p 'test_*.py' -v")

    def test_makefile_exposes_exact_phase2_gate_contract(self) -> None:
        # Given: the repository Makefile as the local gate interface.
        text = (ROOT / "Makefile").read_text(encoding="utf-8")

        # When: Phase 2 targets and the compile boundary are selected.
        expected = (
            "PHASE2_VENV ?= .venv",
            "PHASE2_PYTHON ?= $(PHASE2_VENV)/bin/python",
            'phase2-deps:\n\t@test -x "$(PHASE2_PYTHON)" || $(PYTHON) -m venv "$(PHASE2_VENV)"\n\t$(PHASE2_PYTHON) -m pip install "pydantic==2.9.2"',
            "phase2-test:\n\t@test -x \"$(PHASE2_PYTHON)\" || { printf '%s\\n' 'Phase 2 environment unavailable; run make phase2-deps' >&2; exit 1; }\n\t@$(PHASE2_PYTHON) -c 'import importlib.util,sys; sys.exit(0) if importlib.util.find_spec(\"pydantic\") else (print(\"Pydantic unavailable; run make phase2-deps\", file=sys.stderr), sys.exit(1))'\n\t$(PHASE2_PYTHON) -m unittest discover -s tests/phase2 -p 'test_*.py' -v",
            "phase2-check: foundation-up phase2-deps\n\t$(PHASE2_PYTHON) scripts/phase2/check.py",
            "compile:\n\t$(PYTHON) -m compileall -q scripts tests contracts connectors",
        )

        # Then: recipes are exact and Phase 0/preflight dependency shape is unchanged.
        for contract in expected:
            self.assertIn(contract, text)
        self.assertIn(
            "phase0-check: compile public-safety validate-json validate-fixtures markdown-links test",
            text,
        )
        self.assertIn(
            "preflight: phase0-check foundation-supply-chain foundation-recovery foundation-evidence-summary",
            text,
        )

    def test_ci_phase2_job_retains_synthetic_hosted_runner_boundary(self) -> None:
        # Given: the CI workflow after the existing foundation-fast job.
        text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        # When: the Phase 2 job block is selected.
        match = re.search(r"^  phase2:\n(?P<job>.*)\Z", text, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(match)
        job = "" if match is None else match.group("job")

        # Then: it mirrors the pinned, bounded synthetic foundation lifecycle.
        required = (
            "    runs-on: ubuntu-24.04",
            "    timeout-minutes: 60",
            "uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0",
            "persist-credentials: false",
            "uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
            "python-version: '3.12'",
            "docker buildx create --driver docker-container --use --name dcim-ci-builder",
            "docker buildx inspect --bootstrap",
            "DCIM_RUNTIME_ROOT: ${{ runner.temp }}/dcim-runtime",
            "run: make foundation-bootstrap",
            "run: make phase2-deps",
            "run: make phase2-check",
            "if: always()",
            'if [[ -f "${DCIM_RUNTIME_ROOT}/dev-build/images.env" ]]; then',
            "make foundation-stop",
        )
        for contract in required:
            self.assertIn(contract, job)
        self.assertEqual(job.count("make phase2-check"), 1)


if __name__ == "__main__":
    unittest.main()
