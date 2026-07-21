#!/usr/bin/env python3
"""Run isolated clean-runtime acceptance for the synthetic foundation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
import time

try:
    from scripts.protected_runtime import (
        ensure_protected_directory, external_runtime_root, validate_compose_project_name,
        write_protected_text,
    )
except ModuleNotFoundError:
    from protected_runtime import (
        ensure_protected_directory, external_runtime_root, validate_compose_project_name,
        write_protected_text,
    )


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "deploy/compose/dev-build/compose.yaml"
IMAGE_RECIPES = ROOT / "deploy/compose/derived-images/recipes.json"
LICENSE_DISPOSITIONS = ROOT / "deploy/compose/derived-images/license-dispositions.json"
PROFILES = ("data", "observability", "smoke")
FOUNDATION_SERVICES = (
    "postgres", "kafka", "postgres-exporter", "kafka-jmx-exporter",
    "prometheus", "grafana",
)
EXPECTED_CONTAINERS = set(FOUNDATION_SERVICES)
EXPECTED_NETWORK_SUFFIXES = {"data", "observability"}
EXPECTED_VOLUME_SUFFIXES = {"postgres-data", "kafka-data", "prometheus-data"}
ACCEPTANCE_OVERRIDE = ("dev-build", "acceptance-compose.override.yaml")
COMMIT_BOUND_PATHS = (
    "Makefile",
    "README.md",
    "deploy/compose",
    "docs/phase1",
    "docs/runbooks",
    "scripts",
    "tests",
)
DOCKER_REMOTE_ENVIRONMENT = {
    "DOCKER_HOST",
    "DOCKER_CONTEXT",
    "DOCKER_CONFIG",
    "DOCKER_TLS",
    "DOCKER_TLS_VERIFY",
    "DOCKER_CERT_PATH",
    "DOCKER_MACHINE_NAME",
}


class AcceptanceFailure(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_runtime_root() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    root = Path(state_home) if state_home else Path.home() / ".local/state"
    return root / "dcim-core-platform/runtime"


def existing_path_components(path: Path) -> list[Path]:
    components: list[Path] = []
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.exists() or current.is_symlink():
            components.append(current)
        else:
            break
    return components


def validate_protected_existing_components(path: Path) -> None:
    for component in existing_path_components(path):
        metadata = component.stat()
        mode = stat.S_IMODE(metadata.st_mode)
        if mode & 0o022:
            raise AcceptanceFailure("acceptance runtime path contains an unsafe writable component")
        if metadata.st_uid not in (0, os.getuid()):
            raise AcceptanceFailure("acceptance runtime path contains an uncontrolled component")


def validate_new_runtime_root(path: Path) -> Path:
    try:
        root = external_runtime_root(path)
    except ValueError as error:
        raise AcceptanceFailure(str(error)) from error
    if root == default_runtime_root().expanduser().absolute():
        raise AcceptanceFailure("acceptance runtime root must not reuse the normal runtime root")
    if root.exists() or root.is_symlink():
        raise AcceptanceFailure("acceptance runtime root must be brand new")
    validate_protected_existing_components(root.parent)
    parent = root.parent
    if not parent.is_dir() or parent.is_symlink():
        raise AcceptanceFailure("acceptance runtime parent must be an existing protected directory")
    metadata = parent.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise AcceptanceFailure("acceptance runtime parent must be owner-only and owner-controlled")
    return root


def validate_project_name(value: str | None) -> str:
    project = value or f"dcim-build-acceptance-{secrets.token_hex(6)}"
    try:
        return validate_compose_project_name(project, acceptance_only=True)
    except ValueError as error:
        raise AcceptanceFailure(str(error)) from error


def requested_runtime_root(value: Path | None) -> Path:
    raw = os.fspath(value) if value is not None else os.environ.get("DCIM_RUNTIME_ROOT")
    if not raw:
        raise AcceptanceFailure("DCIM_RUNTIME_ROOT or --runtime-root is required")
    return Path(raw)


def validate_local_docker_environment(environment: dict[str, str]) -> None:
    inherited = sorted(
        name for name in DOCKER_REMOTE_ENVIRONMENT if environment.get(name)
    )
    if inherited:
        raise AcceptanceFailure("Docker remote/context environment is prohibited for clean acceptance")


def validate_local_docker_context(environment: dict[str, str]) -> None:
    result = subprocess.run(
        ["docker", "context", "inspect", "--format", "{{json .Endpoints.docker.Host}}"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode:
        raise AcceptanceFailure("unable to verify local Docker context")
    endpoint = result.stdout.strip().strip('"')
    if not endpoint.startswith("unix://"):
        raise AcceptanceFailure("Docker context must be an explicit local Unix socket")


def acceptance_environment(runtime_root: Path, project: str) -> dict[str, str]:
    environment = os.environ.copy()
    validate_local_docker_environment(environment)
    environment["DCIM_RUNTIME_ROOT"] = str(runtime_root)
    environment["COMPOSE_PROJECT_NAME"] = project
    environment.pop("DCIM_COMPOSE_OVERRIDE", None)
    for inherited_make_state in ("MAKEFLAGS", "MFLAGS", "MAKEOVERRIDES"):
        environment.pop(inherited_make_state, None)
    return environment


def write_acceptance_compose_override(runtime_root: Path, project: str) -> Path:
    """Write the acceptance-only Compose resource-name override outside Git."""

    project = validate_project_name(project)
    override = (
        "networks:\n"
        "  data:\n"
        f"    name: {project}-data\n"
        "  observability:\n"
        f"    name: {project}-observability\n"
        "volumes:\n"
        "  postgres-data:\n"
        f"    name: {project}-postgres-data\n"
        "  kafka-data:\n"
        f"    name: {project}-kafka-data\n"
        "  prometheus-data:\n"
        f"    name: {project}-prometheus-data\n"
    )
    ensure_protected_directory(runtime_root, "dev-build")
    return write_protected_text(runtime_root, ACCEPTANCE_OVERRIDE, override)


def smoke_environment(
    environment: dict[str, str],
    acceptance_override: Path | None,
) -> dict[str, str]:
    if acceptance_override is None:
        return environment
    return {**environment, "DCIM_COMPOSE_OVERRIDE": str(acceptance_override)}


def compose_prefix(runtime_root: Path, override_file: Path | None = None) -> list[str]:
    command = [
        "docker", "compose",
        "--env-file", str(runtime_root / "dev-build/runtime.env"),
        "--env-file", str(runtime_root / "dev-build/images.env"),
        "-f", str(COMPOSE_FILE),
    ]
    if override_file is not None:
        command.extend(("-f", str(override_file)))
    for profile in PROFILES:
        command.extend(("--profile", profile))
    return command


def run_step(
    label: str,
    command: list[str],
    *,
    environment: dict[str, str],
    timeout: int,
    records: list[dict[str, object]],
    input_text: str | None = None,
) -> str:
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    duration = time.monotonic() - started
    records.append({
        "step": label,
        "exit_code": result.returncode,
        "duration_seconds": round(duration, 3),
    })
    if result.returncode:
        raise AcceptanceFailure(f"{label} failed with exit code {result.returncode}")
    return result.stdout


def docker_lines(arguments: list[str], environment: dict[str, str]) -> list[str]:
    result = subprocess.run(
        ["docker", *arguments],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode:
        raise AcceptanceFailure("unable to inspect Docker acceptance namespace")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def project_named_lines(lines: list[str], project: str) -> set[str]:
    matches: set[str] = set()
    for line in lines:
        name, separator, identifier = line.partition("\t")
        if project_resource_name_matches(name, project):
            matches.add(identifier if separator and identifier else name)
    return matches


def project_resource_name_matches(name: str, project: str) -> bool:
    separators = ("-", "_", "/", ":")
    if name == project or any(name.startswith(f"{project}{separator}") for separator in separators):
        return project != "dcim-build" or not name.startswith("dcim-build-acceptance-")
    return False


def project_containers(project: str, environment: dict[str, str]) -> set[str]:
    label = f"label=com.docker.compose.project={project}"
    resources = set(docker_lines(
        ["ps", "-a", "--filter", label, "--format", "{{.ID}}"],
        environment,
    ))
    resources.update(project_named_lines(docker_lines(
        ["ps", "-a", "--format", "{{.Names}}\t{{.ID}}"],
        environment,
    ), project))
    return resources


def project_networks(project: str, environment: dict[str, str]) -> set[str]:
    label = f"label=com.docker.compose.project={project}"
    resources = set(docker_lines(
        ["network", "ls", "--filter", label, "--format", "{{.ID}}"],
        environment,
    ))
    resources.update(project_named_lines(docker_lines(
        ["network", "ls", "--format", "{{.Name}}\t{{.ID}}"],
        environment,
    ), project))
    return resources


def project_volumes(project: str, environment: dict[str, str]) -> set[str]:
    label = f"label=com.docker.compose.project={project}"
    resources = set(docker_lines(
        ["volume", "ls", "--filter", label, "--format", "{{.Name}}"],
        environment,
    ))
    resources.update(project_named_lines(docker_lines(
        ["volume", "ls", "--format", "{{.Name}}\t{{.Name}}"],
        environment,
    ), project))
    return resources


def project_images(project: str, environment: dict[str, str]) -> set[str]:
    label = f"label=com.docker.compose.project={project}"
    images = set(docker_lines(
        ["image", "ls", "--filter", label, "--format", "{{.ID}}"], environment,
    ))
    for line in docker_lines(
        ["image", "ls", "--format", "{{.Repository}}:{{.Tag}}\t{{.ID}}"],
        environment,
    ):
        images.update(project_named_lines([line], project))
    return images


def project_resource_counts(project: str, environment: dict[str, str]) -> dict[str, int]:
    return {
        "containers": len(project_containers(project, environment)),
        "networks": len(project_networks(project, environment)),
        "volumes": len(project_volumes(project, environment)),
        "images": len(project_images(project, environment)),
    }


def assert_no_existing_project_resources(project: str, environment: dict[str, str]) -> None:
    counts = project_resource_counts(project, environment)
    if any(counts.values()):
        raise AcceptanceFailure(
            "pre-existing acceptance Compose namespace detected "
            f"(containers={counts['containers']}, networks={counts['networks']}, volumes={counts['volumes']})"
            f", images={counts['images']}"
        )


def assert_no_normal_runtime_state(environment: dict[str, str]) -> None:
    counts = project_resource_counts("dcim-build", environment)
    if any(counts.values()):
        raise AcceptanceFailure(
            "pre-existing normal dcim-build runtime state detected "
            f"(containers={counts['containers']}, networks={counts['networks']}, volumes={counts['volumes']})"
            f", images={counts['images']}"
        )


def assert_expected_project_inventory(project: str, environment: dict[str, str]) -> None:
    label = f"label=com.docker.compose.project={project}"
    services = set(docker_lines([
        "ps", "-a", "--filter", label, "--format",
        "{{.Label \"com.docker.compose.service\"}}",
    ], environment))
    if services != EXPECTED_CONTAINERS:
        raise AcceptanceFailure("unexpected acceptance container inventory")
    networks = set(docker_lines(["network", "ls", "--filter", label, "--format", "{{.Name}}"], environment))
    expected_networks = {f"{project}-{suffix}" for suffix in EXPECTED_NETWORK_SUFFIXES}
    if networks != expected_networks:
        raise AcceptanceFailure("unexpected acceptance network inventory")
    volumes = set(docker_lines(["volume", "ls", "--filter", label, "--format", "{{.Name}}"], environment))
    expected_volumes = {f"{project}-{suffix}" for suffix in EXPECTED_VOLUME_SUFFIXES}
    if volumes != expected_volumes:
        raise AcceptanceFailure("unexpected acceptance volume inventory")
    images = project_images(project, environment)
    if images:
        raise AcceptanceFailure("unexpected acceptance image inventory")


def git_commit(environment: dict[str, str]) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode:
        raise AcceptanceFailure("unable to resolve git commit")
    return result.stdout.strip()


def assert_commit_bound_tree(environment: dict[str, str]) -> None:
    checks = (
        ["git", "diff", "--quiet"],
        ["git", "diff", "--cached", "--quiet"],
    )
    for command in checks:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode not in (0, 1):
            raise AcceptanceFailure("unable to verify commit-bound worktree")
        if result.returncode == 1:
            raise AcceptanceFailure("clean acceptance requires a clean commit-bound worktree")
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *COMMIT_BOUND_PATHS],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if untracked.returncode or untracked.stdout.strip():
        raise AcceptanceFailure("clean acceptance requires a clean commit-bound worktree")


def write_acceptance_report(
    runtime_root: Path,
    *,
    commit: str,
    started_utc: str,
    finished_utc: str,
    result: str,
    records: list[dict[str, object]],
    failure_reason: str | None = None,
) -> None:
    report = {
        "schema_version": 1,
        "commit": commit,
        "project_scope": "isolated synthetic dcim-build acceptance namespace",
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "result": result,
        "steps": records,
    }
    if failure_reason:
        report["failure_reason"] = failure_reason
    ensure_protected_directory(runtime_root, "dev-build", "evidence")
    write_protected_text(
        runtime_root,
        ("dev-build", "evidence", "clean-runtime-acceptance.json"),
        json.dumps(report, indent=2, sort_keys=True) + "\n",
    )


def run_acceptance(runtime_root: Path, project: str) -> int:
    records: list[dict[str, object]] = []
    started_utc = utc_now()
    environment = os.environ.copy()
    commit = "unknown"
    root: Path | None = None
    services_started = False
    result = "fail"
    failure_reason: str | None = None
    acceptance_override: Path | None = None
    try:
        commit = git_commit(environment)
        root = validate_new_runtime_root(runtime_root)
        environment = acceptance_environment(root, project)
        assert_commit_bound_tree(environment)
        validate_local_docker_context(environment)
        assert_no_normal_runtime_state(environment)
        assert_no_existing_project_resources(project, environment)
        run_step(
            "foundation-bootstrap",
            [sys.executable, "scripts/foundation_bootstrap.py", "--runtime-root", str(root)],
            environment=environment,
            timeout=30,
            records=records,
        )
        acceptance_override = write_acceptance_compose_override(root, project)
        run_step(
            "foundation-images-qualify",
            [
                sys.executable, "scripts/foundation_images.py",
                "--manifest", str(IMAGE_RECIPES),
                "--license-dispositions", str(LICENSE_DISPOSITIONS),
                "--runtime-root", str(root),
                "--force",
            ],
            environment=environment,
            timeout=14_400,
            records=records,
        )
        run_step(
            "foundation-artifacts",
            [sys.executable, "scripts/foundation_artifacts.py", "--runtime-root", str(root)],
            environment=environment,
            timeout=180,
            records=records,
        )
        normalized = run_step(
            "compose-config",
            [*compose_prefix(root, acceptance_override), "config", "--format", "json"],
            environment=environment,
            timeout=60,
            records=records,
        )
        run_step(
            "foundation-policy",
            [
                sys.executable, "scripts/foundation_policy.py",
                "--input", "-",
                "--runtime-root", str(root),
                "--derived-lock", str(root / "dev-build/derived-images-lock.json"),
                "--license-dispositions", str(LICENSE_DISPOSITIONS),
                "--project-name", project,
            ],
            environment=environment,
            timeout=30,
            records=records,
            input_text=normalized,
        )
        run_step(
            "foundation-supply-chain",
            [
                sys.executable, "scripts/foundation_supply_chain.py",
                "--runtime-root", str(root),
                "--derived-lock", str(root / "dev-build/derived-images-lock.json"),
                "--license-dispositions", str(LICENSE_DISPOSITIONS),
            ],
            environment=environment,
            timeout=7_200,
            records=records,
        )
        run_step(
            "foundation-up",
            [
                *compose_prefix(root, acceptance_override),
                "up", "-d", "--wait", "--wait-timeout", "180", *FOUNDATION_SERVICES,
            ],
            environment=environment,
            timeout=300,
            records=records,
        )
        services_started = True
        assert_expected_project_inventory(project, environment)
        run_step(
            "foundation-smoke-fast",
            [sys.executable, "scripts/foundation_smoke.py", "fast"],
            environment=smoke_environment(environment, acceptance_override),
            timeout=360,
            records=records,
        )
        run_step(
            "foundation-smoke-recovery",
            [sys.executable, "scripts/foundation_smoke.py", "recovery"],
            environment=smoke_environment(environment, acceptance_override),
            timeout=960,
            records=records,
        )
        run_step(
            "foundation-stop",
            [*compose_prefix(root, acceptance_override), "stop", "--timeout", "60"],
            environment=environment,
            timeout=90,
            records=records,
        )
        services_started = False
        run_step(
            "foundation-evidence-summary",
            [
                sys.executable, "scripts/foundation_evidence_summary.py",
                "--evidence-dir", str(root / "dev-build/evidence"),
                "--commit", commit,
                "--output", str(root / "dev-build/evidence/phase1-clean-acceptance-summary.json"),
                "--require-modes", "fast,recovery",
                "--require-pass",
                "--strict-commit",
            ],
            environment=environment,
            timeout=30,
            records=records,
        )
        result = "pass"
        return_code = 0
    except AcceptanceFailure as error:
        failure_reason = str(error)
        print(f"foundation-clean-acceptance: {failure_reason}", file=sys.stderr)
        return_code = 1
    except subprocess.TimeoutExpired:
        failure_reason = "acceptance step timed out"
        print(f"foundation-clean-acceptance: {failure_reason}", file=sys.stderr)
        return_code = 1
    finally:
        if services_started and root is not None:
            try:
                run_step(
                    "foundation-stop-after-failure",
                    [*compose_prefix(root, acceptance_override), "stop", "--timeout", "60"],
                    environment=environment,
                    timeout=90,
                    records=records,
                )
            except (AcceptanceFailure, subprocess.TimeoutExpired):
                pass
        if root is not None:
            write_acceptance_report(
                root,
                commit=commit,
                started_utc=started_utc,
                finished_utc=utc_now(),
                result=result,
                records=records,
                failure_reason=failure_reason,
            )
    print(f"foundation-clean-acceptance: {result.upper()}")
    return return_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", default=None, type=Path)
    parser.add_argument("--project-name", default=None)
    arguments = parser.parse_args()
    try:
        runtime_root = requested_runtime_root(arguments.runtime_root)
        project = validate_project_name(arguments.project_name)
        return run_acceptance(runtime_root, project)
    except AcceptanceFailure as error:
        print(f"foundation-clean-acceptance: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
