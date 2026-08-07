#!/usr/bin/env python3
"""Phase 2 evidence receipt generator and validator.

Product-side mirror of the plan-owned trusted launcher.  Produces strict
closed-schema JSON receipts for AUTHORITY_BOOTSTRAP and other requirement IDs.
The trusted launcher recomputes every qualifying fact from raw process/Git/
runtime data; this module provides the executable surface that the launcher
invokes under a scrubbed environment.
"""
from __future__ import annotations

import argparse
import errno
import fcntl
import hashlib
import hmac
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from stat import S_ISREG
from typing import Any, Literal


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1] if len(SCRIPT_PATH.parents) > 1 else Path.cwd()
RECEIPT_SCHEMA_PATH = ROOT / "schemas" / "phase2-evidence-receipt.schema.json"

MARKER_RE = re.compile(r"^`(?P<kind>BEGIN|END) (?P<name>[A-Z_0-9]+)`$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
RUNTIME_BINDING_DIGEST_MARKER_RE = re.compile(r"^runtime_binding_digest=([0-9a-f]{64})$")

EXPECTED_FIXED_VOLUMES = frozenset({
    "dcim-build-kafka-data",
    "dcim-build-postgres-data",
    "dcim-build-prometheus-data",
})
PROTECTED_SECRET_NAMES = (
    "postgres-superuser-password",
    "postgres-monitor-password",
    "postgres-smoke-password",
    "grafana-admin-user",
    "grafana-admin-password",
    "assets-db-password",
    "cmdb-db-password",
    "api-db-password",
    "analytics-db-password",
    "workflow-db-password",
    "internal-api-token",
)

REQUIRED_BLOCKS = (
    "AUTHORITY_ROOTS_V1",
    "ORIGINAL_PATCH_INVENTORY_V1",
    "PHASE2_TODO_PATH_AUTHORITY_V1",
    "LEGACY_FAILURE_INVENTORY_V1",
    "ORACLE_CONTRACT_V1",
    "REMEDIATION_ALLOWLIST_V1",
)

PASS_MARKERS = {
    "heredoc_integrity=PASS",
    "authority_blocks=PASS",
    "runtime_preflight=PASS",
    "runtime_binding=PASS",
}


class ReceiptError(Exception):
    pass


class PlanAuthorityError(ReceiptError):
    pass


class DuplicateKeyError(ReceiptError):
    pass


class ToolchainIdentityError(ReceiptError):
    pass


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_text(text: str) -> str:
    return _hash_bytes(text.encode("utf-8"))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _require(condition: bool, message: str, disposition: str = "NO-GO_PLAN_AUTHORITY") -> None:
    if not condition:
        raise PlanAuthorityError(message, disposition)


def load_json_with_duplicate_rejection(data: bytes | str) -> Any:
    text = data.decode("utf-8") if isinstance(data, bytes) else data

    def _check_duplicate(obj: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: set[str] = set()
        for key, _ in obj:
            if key in seen:
                raise DuplicateKeyError(f"duplicate JSON key: {key}")
            seen.add(key)
        return dict(obj)

    try:
        return json.loads(text, object_pairs_hook=_check_duplicate)
    except json.JSONDecodeError as exc:
        raise ReceiptError(f"invalid JSON: {exc}") from exc


def extract_blocks(plan_bytes: bytes) -> dict[str, str]:
    try:
        text = plan_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PlanAuthorityError("plan is not valid UTF-8", "NO-GO_PLAN_AUTHORITY") from exc
    if not text.endswith("\n"):
        raise PlanAuthorityError("plan does not end with LF", "NO-GO_PLAN_AUTHORITY")

    blocks: dict[str, str] = {}
    seen_order: list[str] = []
    open_name: str | None = None
    body_lines: list[str] = []
    for line in text.splitlines():
        marker = MARKER_RE.fullmatch(line)
        if marker is None:
            if open_name is not None:
                body_lines.append(line)
            continue

        kind = marker.group("kind")
        name = marker.group("name")
        if kind == "BEGIN":
            if open_name is not None:
                raise PlanAuthorityError("nested or duplicate BEGIN marker", "NO-GO_PLAN_AUTHORITY")
            if name in blocks:
                raise PlanAuthorityError(f"duplicate block: {name}", "NO-GO_PLAN_AUTHORITY")
            open_name = name
            body_lines = []
            continue

        if open_name is None:
            raise PlanAuthorityError("END marker without BEGIN", "NO-GO_PLAN_AUTHORITY")
        if name != open_name:
            raise PlanAuthorityError("out-of-order END marker", "NO-GO_PLAN_AUTHORITY")
        blocks[name] = "\n".join(body_lines) + "\n"
        seen_order.append(name)
        open_name = None
        body_lines = []

    if open_name is not None:
        raise PlanAuthorityError(f"missing END marker: {open_name}", "NO-GO_PLAN_AUTHORITY")
    required_seen = [name for name in seen_order if name in REQUIRED_BLOCKS]
    if required_seen != [name for name in REQUIRED_BLOCKS if name in blocks]:
        raise PlanAuthorityError("required blocks are not in plan order", "NO-GO_PLAN_AUTHORITY")
    return blocks


def validate_plan_authority(
    *,
    plan_path: Path,
    expected_sha256: str,
    required_blocks: tuple[str, ...] = REQUIRED_BLOCKS,
) -> tuple[bytes, dict[str, str], dict[str, str]]:
    expected_sha256 = expected_sha256.lower().strip()
    _require(HEX64_RE.match(expected_sha256) is not None, "expected SHA-256 must be 64 lowercase hex chars")

    try:
        fd = os.open(str(plan_path), os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise PlanAuthorityError(f"cannot open plan: {exc}") from exc

    try:
        stat_before = os.fstat(fd)
        _require(S_ISREG(stat_before.st_mode), "plan is not a regular file", "NO-GO_TOCTOU")
        _require(stat_before.st_size < 10_000_000, "plan file unreasonably large")

        raw = b""
        while len(raw) < stat_before.st_size:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            raw += chunk

        stat_after = os.fstat(fd)
        stable_keys = (
            stat_before.st_dev,
            stat_before.st_ino,
            stat_before.st_mode,
            stat_before.st_uid,
            stat_before.st_gid,
            stat_before.st_size,
            stat_before.st_mtime_ns,
        )
        stable_after = (
            stat_after.st_dev,
            stat_after.st_ino,
            stat_after.st_mode,
            stat_after.st_uid,
            stat_after.st_gid,
            stat_after.st_size,
            stat_after.st_mtime_ns,
        )
        _require(stable_keys == stable_after, "plan file changed during read", "NO-GO_TOCTOU")
        _require(len(raw) == stat_before.st_size, "plan read size mismatch", "NO-GO_TOCTOU")
    finally:
        os.close(fd)

    observed_sha256 = _hash_bytes(raw)
    _require(
        observed_sha256 == expected_sha256,
        "plan SHA-256 mismatch",
        "NO-GO_PLAN_AUTHORITY",
    )

    blocks = extract_blocks(raw)
    missing = sorted(set(required_blocks) - set(blocks))
    _require(not missing, f"missing required blocks: {missing}", "NO-GO_PLAN_AUTHORITY")

    block_digests = {name: _hash_text(body) for name, body in blocks.items()}
    return raw, blocks, block_digests


@dataclass(frozen=True)
class ToolchainIdentity:
    python_version: str
    python_executable_digest: str
    git_version: str
    make_version: str
    docker_version: str
    compose_version: str

    def digest(self) -> str:
        return _hash_text(_canonical_json(asdict(self)))

    @classmethod
    def capture(cls) -> "ToolchainIdentity":
        def _run(argv: list[str]) -> tuple[str, int]:
            try:
                result = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)
                return result.stdout.strip().splitlines()[0] if result.stdout.strip() else "unknown", result.returncode
            except (OSError, subprocess.TimeoutExpired):
                return "unknown", -1

        python_exe = sys.executable
        try:
            python_digest = _hash_bytes(Path(python_exe).read_bytes())
        except OSError:
            python_digest = _hash_text("unknown")

        git_version, git_code = _run(["git", "--version"])
        make_version, make_code = _run(["make", "--version"])
        docker_version, docker_code = _run(["docker", "info", "--format", "server={{.ServerVersion}}"])
        compose_version, compose_code = _run(["docker", "compose", "version"])

        if any(code != 0 for code in (git_code, make_code, docker_code, compose_code)):
            raise ToolchainIdentityError("toolchain identity probe failed", "NO-GO_TOOLCHAIN_IDENTITY")

        return cls(
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            python_executable_digest=python_digest,
            git_version=git_version,
            make_version=make_version,
            docker_version=docker_version,
            compose_version=compose_version,
        )


@dataclass(frozen=True)
class Receipt:
    schema_version: str = "1.0.0"
    requirement_id: str = "AUTHORITY_BOOTSTRAP"
    launcher_nonce: str = ""
    receipt_id: str = ""
    attempt_epoch_id: str = ""
    base_sha: str = ""
    subject_commit_sha: str = ""
    subject_tree_sha: str = ""
    subject_parent_shas: list[str] = field(default_factory=list)
    plan_sha256: str = ""
    authority_block_sha256: str = ""
    oracle_contract_sha256: str = ""
    executor_material_sha256: str = ""
    toolchain_identity_sha256: str = ""
    argv: list[str] = field(default_factory=list)
    argv_sha256: str = ""
    environment_allowlist_sha256: str = ""
    started_at_utc: str = ""
    finished_at_utc: str = ""
    duration_monotonic_ms: int = 0
    timeout_ms: int = 300_000
    process_outcome: str = "exited"
    exit_code: int = 0
    signal: int | None = None
    spawn_error_class: str | None = None
    stdout_bytes: int = 0
    stdout_sha256: str = ""
    stderr_bytes: int = 0
    stderr_sha256: str = ""
    runtime_binding_digest: str | None = None
    pass_marker_observations: list[dict[str, Any]] = field(default_factory=list)
    no_go_marker_observations: list[dict[str, Any]] = field(default_factory=list)
    artifact_sha256: str = ""
    computed_disposition: str = "NO-GO_PLAN_AUTHORITY"
    branch_ref_before: str | None = None
    branch_ref_after: str | None = None
    dirty_state_before_sha256: str = ""
    dirty_state_after_sha256: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_json(self) -> str:
        return _canonical_json(self.as_dict()) + "\n"

    def digest(self) -> str:
        return _hash_text(self.canonical_json())


ProcessOutcome = Literal["exited", "signaled", "timed_out", "spawn_error"]


@dataclass(frozen=True, slots=True)
class ProcessResult:
    stdout: str
    stderr: str
    exit_code: int
    signal: int | None
    outcome: ProcessOutcome
    spawn_error_class: str | None


def compute_process_disposition(
    result: ProcessResult,
    no_go_observations: list[dict[str, Any]],
) -> str:
    if no_go_observations:
        marker = str(no_go_observations[0]["marker"])
        match = re.search(r"NO-GO_[A-Z0-9_]+", marker)
        return match.group(0) if match is not None else "NO-GO_PROCESS_OUTCOME"
    if result.outcome == "spawn_error":
        return "NO-GO_TOOLCHAIN_IDENTITY"
    if result.outcome != "exited" or result.exit_code != 0:
        return "NO-GO_PROCESS_OUTCOME"
    return "LOCAL_PASS"


@dataclass(frozen=True, slots=True)
class SubjectState:
    branch_ref: str | None
    commit_sha: str
    tree_sha: str
    parent_shas: tuple[str, ...]
    index_status_sha256: str
    worktree_status_sha256: str

    def dirty_state_sha256(self) -> str:
        return _hash_text(
            _canonical_json(
                {
                    "index": self.index_status_sha256,
                    "worktree": self.worktree_status_sha256,
                }
            )
        )


def _git_output(subject_dir: Path, arguments: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(subject_dir), f"--work-tree={subject_dir}", *arguments],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PlanAuthorityError("cannot capture Git subject state", "NO-GO_HEAD_DRIFT") from exc
    if result.returncode != 0:
        raise PlanAuthorityError("cannot capture Git subject state", "NO-GO_HEAD_DRIFT")
    return result.stdout


def capture_subject_state(subject_dir: Path) -> SubjectState:
    branch_result = subprocess.run(
        ["git", "-C", str(subject_dir), "symbolic-ref", "--short", "HEAD"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    branch_ref = branch_result.stdout.strip() if branch_result.returncode == 0 else None
    commit_sha = _git_output(subject_dir, ["rev-parse", "HEAD"]).strip()
    tree_sha = _git_output(subject_dir, ["rev-parse", "HEAD^{tree}"]).strip()
    parent_tokens = _git_output(
        subject_dir,
        ["rev-list", "--parents", "-n", "1", "HEAD"],
    ).strip().split()
    parent_shas = tuple(parent_tokens[1:])

    _require(HEX40_RE.match(commit_sha) is not None, "invalid subject commit SHA")
    _require(HEX40_RE.match(tree_sha) is not None, "invalid subject tree SHA")
    for parent in parent_shas:
        _require(HEX40_RE.match(parent) is not None, "invalid parent SHA")

    index_status = _git_output(subject_dir, ["diff", "--cached", "--binary", "--no-ext-diff"])
    tracked_worktree = _git_output(subject_dir, ["diff", "--binary", "--no-ext-diff"])
    untracked = _git_output(subject_dir, ["ls-files", "--others", "--exclude-standard", "-z"])
    public_untracked = sorted(
        path
        for path in untracked.split("\0")
        if path and not path.startswith(".omo/")
    )
    worktree_status = _canonical_json(
        {"tracked_diff": tracked_worktree, "untracked_paths": public_untracked}
    )
    return SubjectState(
        branch_ref=branch_ref,
        commit_sha=commit_sha,
        tree_sha=tree_sha,
        parent_shas=parent_shas,
        index_status_sha256=_hash_text(index_status),
        worktree_status_sha256=_hash_text(worktree_status),
    )


def apply_subject_drift_precedence(
    before: SubjectState,
    after: SubjectState,
    disposition: str,
) -> str:
    return "NO-GO_HEAD_DRIFT" if before != after else disposition


def _observe_markers(text: str, channel: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pass_obs: list[dict[str, Any]] = []
    no_go_obs: list[dict[str, Any]] = []
    for index, line in enumerate(text.splitlines(), start=1):
        if any(marker in line for marker in PASS_MARKERS):
            pass_obs.append({"marker": line, "channel": channel, "line": index})
        if "NO-GO_" in line:
            no_go_obs.append({"marker": line, "channel": channel, "line": index})
    return pass_obs, no_go_obs


def _parse_runtime_binding_digest(stdout: str) -> str | None:
    digests = [
        match.group(1)
        for line in stdout.splitlines()
        if (match := RUNTIME_BINDING_DIGEST_MARKER_RE.fullmatch(line)) is not None
    ]
    return digests[0] if len(digests) == 1 else None


def _run(argv: list[str], timeout: float = 30.0) -> tuple[str, int]:
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
        return result.stdout.strip(), result.returncode
    except (OSError, subprocess.TimeoutExpired):
        return "", -1


@dataclass(frozen=True, slots=True)
class RuntimeBindingObservation:
    binding_sha256: str


def compute_runtime_binding_sha256(
    *,
    runtime_env_sha256: str,
    images_env_sha256: str,
    kafka_identity_sha256: str,
    fixed_volumes: frozenset[str],
) -> str:
    return _hash_text(
        _canonical_json(
            {
                "fixed_volumes": sorted(fixed_volumes),
                "images_env_sha256": images_env_sha256,
                "kafka_identity_sha256": kafka_identity_sha256,
                "runtime_env_sha256": runtime_env_sha256,
            }
        )
    )


def _protected_directory_is_valid(path: Path) -> bool:
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError:
        return False
    return (
        path.is_dir()
        and metadata.st_uid == os.getuid()
        and metadata.st_mode & 0o777 == 0o700
    )


def _read_protected_file(path: Path) -> bytes | None:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        metadata = os.fstat(descriptor)
        if (
            not S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o022
            or metadata.st_size > 10_000_000
        ):
            return None
        chunks: list[bytes] = []
        remaining = metadata.st_size
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                return None
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _environment_value(raw: bytes, name: str) -> str | None:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    prefix = f"{name}="
    values = [line[len(prefix):] for line in text.splitlines() if line.startswith(prefix)]
    if len(values) != 1 or not values[0]:
        return None
    return values[0]


def _docker_runtime_identity() -> tuple[frozenset[str], str] | None:
    volumes_text, volumes_code = _run(
        ["docker", "volume", "ls", "--format", "{{.Name}}"]
    )
    if volumes_code != 0:
        return None
    named_volumes = frozenset(
        name for name in volumes_text.splitlines() if name and HEX64_RE.fullmatch(name) is None
    )
    if named_volumes != EXPECTED_FIXED_VOLUMES:
        return None

    containers_text, containers_code = _run(
        ["docker", "ps", "--format", "{{.Names}}"]
    )
    if containers_code != 0 or "dcim-build-kafka-1" not in containers_text.splitlines():
        return None

    mount_name, mount_code = _run(
        [
            "docker",
            "inspect",
            "--format",
            '{{range .Mounts}}{{if eq .Destination "/var/lib/kafka/data"}}{{.Name}}{{end}}{{end}}',
            "dcim-build-kafka-1",
        ]
    )
    if mount_code != 0 or mount_name != "dcim-build-kafka-data":
        return None

    metadata, metadata_code = _run(
        [
            "docker",
            "exec",
            "dcim-build-kafka-1",
            "cat",
            "/var/lib/kafka/data/meta.properties",
        ]
    )
    if metadata_code != 0:
        return None
    cluster_id = _environment_value(metadata.encode("utf-8"), "cluster.id")
    if cluster_id is None:
        return None
    return named_volumes, cluster_id


def collect_runtime_binding(runtime_root: Path) -> RuntimeBindingObservation | None:
    plane = runtime_root / "dev-build"
    secret_directory = plane / "secrets"
    if not all(
        _protected_directory_is_valid(path)
        for path in (runtime_root, plane, secret_directory)
    ):
        return None

    runtime_environment = _read_protected_file(plane / "runtime.env")
    images_environment = _read_protected_file(plane / "images.env")
    if runtime_environment is None or images_environment is None:
        return None
    kafka_cluster_id = _environment_value(runtime_environment, "KAFKA_CLUSTER_ID")
    if kafka_cluster_id is None:
        return None

    try:
        secret_names = frozenset(path.name for path in secret_directory.iterdir())
    except OSError:
        return None
    if secret_names != frozenset(PROTECTED_SECRET_NAMES):
        return None
    secret_digests: dict[str, str] = {}
    for name in PROTECTED_SECRET_NAMES:
        protected_bytes = _read_protected_file(secret_directory / name)
        if protected_bytes is None:
            return None
        secret_digests[name] = _hash_bytes(protected_bytes)

    docker_identity = _docker_runtime_identity()
    if docker_identity is None:
        return None
    volumes, volume_cluster_id = docker_identity
    runtime_cluster_id_sha256 = _hash_text(kafka_cluster_id)
    volume_cluster_id_sha256 = _hash_text(volume_cluster_id)
    if not hmac.compare_digest(
        runtime_cluster_id_sha256,
        volume_cluster_id_sha256,
    ):
        return None

    binding_sha256 = _hash_text(
        _canonical_json(
            {
                "fixed_volumes": sorted(volumes),
                "images_env_sha256": _hash_bytes(images_environment),
                "kafka_identity_sha256": volume_cluster_id_sha256,
                "protected_secret_bundle_sha256": _hash_text(
                    _canonical_json(secret_digests)
                ),
                "runtime_env_sha256": _hash_bytes(runtime_environment),
            }
        )
    )
    return RuntimeBindingObservation(binding_sha256)


def _oracle_child_main() -> int:
    plan_path = os.environ.get("DCIM_ORACLE_PLAN_PATH")
    expected_sha256 = os.environ.get("DCIM_ORACLE_EXPECTED_SHA256")
    if plan_path is None or expected_sha256 is None:
        print("NO-GO_PLAN_AUTHORITY")
        return 97
    try:
        validate_plan_authority(
            plan_path=Path(plan_path),
            expected_sha256=expected_sha256,
        )
    except PlanAuthorityError as exc:
        disposition = exc.args[1] if len(exc.args) > 1 else "NO-GO_PLAN_AUTHORITY"
        print(disposition)
        return 97

    print("heredoc_integrity=PASS")
    print("authority_blocks=PASS")
    runtime_root = os.environ.get("DCIM_RUNTIME_ROOT")
    if runtime_root is None:
        print("NO-GO_DOCKER_REQUIRED_FOR_HANDOFF")
        return 97
    observation = collect_runtime_binding(Path(runtime_root))
    if observation is None:
        print("NO-GO_DOCKER_REQUIRED_FOR_HANDOFF")
        return 97

    print("runtime_preflight=PASS")
    print("runtime_binding=PASS")
    print(f"runtime_binding_digest={observation.binding_sha256}")
    return 0


@dataclass(frozen=True, slots=True)
class ExecutorMaterial:
    fd: int
    size: int
    digest: str
    executable_path: Path
    storage_dir: Path | None


def _write_all(fd: int, source: bytes) -> None:
    offset = 0
    while offset < len(source):
        offset += os.write(fd, source[offset:])


def _read_executor_material(material: ExecutorMaterial) -> bytes:
    chunks: list[bytes] = []
    offset = 0
    while offset < material.size:
        chunk = os.pread(material.fd, min(65_536, material.size - offset), offset)
        if not chunk:
            break
        chunks.append(chunk)
        offset += len(chunk)
    return b"".join(chunks)


def _prepare_executor_material(
    source: bytes | None = None,
    *,
    use_memfd: bool | None = None,
) -> ExecutorMaterial:
    payload = Path(__file__).read_bytes() if source is None else source
    memfd_available = hasattr(os, "memfd_create")
    should_use_memfd = memfd_available if use_memfd is None else use_memfd and memfd_available
    storage_dir: Path | None = None

    if should_use_memfd:
        fd = os.memfd_create(
            "dcim-phase2-oracle",
            os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
        )
        _write_all(fd, payload)
        os.fchmod(fd, 0o600)
        fcntl.fcntl(
            fd,
            fcntl.F_ADD_SEALS,
            fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE,
        )
    else:
        storage_dir = Path(tempfile.mkdtemp(prefix="dcim-oracle-", dir=tempfile.gettempdir()))
        os.chmod(storage_dir, 0o700)
        backing_path = storage_dir / "oracle.py"
        writer_fd = os.open(
            backing_path,
            os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
        )
        try:
            _write_all(writer_fd, payload)
            os.fsync(writer_fd)
            fd = os.open(backing_path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
            backing_path.unlink()
        finally:
            os.close(writer_fd)

    material = ExecutorMaterial(
        fd=fd,
        size=len(payload),
        digest=_hash_bytes(payload),
        executable_path=Path(f"/proc/self/fd/{fd}"),
        storage_dir=storage_dir,
    )
    if _hash_bytes(_read_executor_material(material)) != material.digest:
        _cleanup_executor_material(material)
        raise ReceiptError("executor material verification failed", "NO-GO_TOCTOU")
    return material


def _cleanup_executor_material(material: ExecutorMaterial) -> None:
    try:
        os.close(material.fd)
    except OSError:
        pass
    if material.storage_dir is not None:
        try:
            shutil.rmtree(material.storage_dir)
        except OSError:
            pass


def _spawn_oracle(
    *,
    executor: ExecutorMaterial,
    env: dict[str, str],
    timeout_ms: int,
    subject_dir: Path,
) -> ProcessResult:
    if _hash_bytes(_read_executor_material(executor)) != executor.digest:
        raise ReceiptError("executor material drift before spawn", "NO-GO_TOCTOU")
    argv = [sys.executable, str(executor.executable_path), "oracle-child"]
    scrubbed_env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        **env,
    }

    proc: subprocess.Popen[str] | None = None
    start = time.monotonic()
    try:
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(subject_dir),
            env=scrubbed_env,
            close_fds=True,
            pass_fds=(executor.fd,),
            start_new_session=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_ms / 1000.0)
        except subprocess.TimeoutExpired:
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            stdout, stderr = proc.communicate(timeout=5)
            return ProcessResult(stdout, stderr, -1, None, "timed_out", None)

        exit_code = proc.returncode
        if exit_code < 0:
            signo = -exit_code
            return ProcessResult(stdout, stderr, exit_code, signo, "signaled", None)
        return ProcessResult(stdout, stderr, exit_code, None, "exited", None)
    except OSError as exc:
        return ProcessResult("", str(exc), -1, None, "spawn_error", type(exc).__name__)
    finally:
        duration_ms = int((time.monotonic() - start) * 1000)


def compute_authority_block_sha256(block_digests: dict[str, str]) -> str:
    canonical = _canonical_json({name: block_digests[name] for name in sorted(block_digests)})
    return _hash_text(canonical)


def generate_authority_bootstrap_receipt(
    *,
    plan_path: Path,
    expected_plan_sha256: str,
    subject_dir: Path,
    base_sha: str,
    attempt_epoch_id: str,
    timeout_ms: int = 300_000,
    expected_toolchain_sha256: str | None = None,
    toolchain_identity: ToolchainIdentity | None = None,
) -> Receipt:
    nonce = hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:32]
    receipt_id = hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:32]
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    start_mono = time.monotonic()

    subject_before = capture_subject_state(subject_dir)

    toolchain = (
        ToolchainIdentity.capture()
        if toolchain_identity is None
        else toolchain_identity
    )
    if expected_toolchain_sha256:
        expected_toolchain_sha256 = expected_toolchain_sha256.lower().strip()
        if toolchain.digest() != expected_toolchain_sha256:
            raise ToolchainIdentityError("toolchain identity drift", "NO-GO_TOOLCHAIN_IDENTITY")

    env: dict[str, str] = {
        "DCIM_EPOCH_ID": attempt_epoch_id,
        "DCIM_RECEIPT_ID": receipt_id,
        "DCIM_LAUNCHER_NONCE": nonce,
        "DCIM_ORACLE_PLAN_PATH": str(plan_path),
        "DCIM_ORACLE_EXPECTED_SHA256": expected_plan_sha256.lower().strip(),
    }
    runtime_root = os.environ.get("DCIM_RUNTIME_ROOT")
    if runtime_root is not None:
        env["DCIM_RUNTIME_ROOT"] = runtime_root

    executor_material = _prepare_executor_material()
    executor_material_sha256 = executor_material.digest
    argv = [
        sys.executable,
        str(executor_material.executable_path),
        "oracle-child",
    ]
    argv_sha256 = _hash_text(_canonical_json(argv))
    env_allowlist_sha256 = _hash_text(_canonical_json(dict(sorted(env.items()))))

    stdout = ""
    stderr = ""
    exit_code = 0
    outcome = "exited"
    signo: int | None = None
    authority_block_sha256 = "0" * 64
    oracle_contract_sha256 = "0" * 64
    computed = "NO-GO_PLAN_AUTHORITY"
    runtime_binding_digest: str | None = None
    pass_obs: list[dict[str, Any]] = []
    no_go_obs: list[dict[str, Any]] = []

    try:
        raw, blocks, block_digests = validate_plan_authority(
            plan_path=plan_path,
            expected_sha256=expected_plan_sha256,
        )
        authority_block_sha256 = compute_authority_block_sha256(block_digests)
        oracle_contract_sha256 = block_digests["ORACLE_CONTRACT_V1"]

        pre_digest = _hash_bytes(_read_executor_material(executor_material))
        if pre_digest != executor_material_sha256:
            raise ReceiptError("executor material drift before spawn", "NO-GO_TOCTOU")

        process_result = _spawn_oracle(
            executor=executor_material,
            env=env,
            timeout_ms=timeout_ms,
            subject_dir=subject_dir,
        )
        stdout = process_result.stdout
        stderr = process_result.stderr
        exit_code = process_result.exit_code
        signo = process_result.signal
        outcome = process_result.outcome

        post_digest = _hash_bytes(_read_executor_material(executor_material))
        if post_digest != executor_material_sha256:
            raise ReceiptError("executor material drift after spawn", "NO-GO_TOCTOU")

        pass_obs, no_go_obs = _observe_markers(stdout, "stdout")
        stderr_pass, stderr_no_go = _observe_markers(stderr, "stderr")
        pass_obs.extend(stderr_pass)
        no_go_obs.extend(stderr_no_go)

        computed = compute_process_disposition(process_result, no_go_obs)
        runtime_binding_passed = "runtime_binding=PASS" in stdout.splitlines()
        if runtime_binding_passed:
            runtime_binding_digest = _parse_runtime_binding_digest(stdout)
        if computed == "LOCAL_PASS" and (
            not runtime_binding_passed or runtime_binding_digest is None
        ):
            computed = "NO-GO_F3_INCOMPLETE_BINDING"

    except PlanAuthorityError as exc:
        args = exc.args
        computed = args[1] if len(args) > 1 else "NO-GO_PLAN_AUTHORITY"
        stdout = ""
        stderr = str(exc)
        exit_code = 1
        outcome = "exited"
        pass_obs = []
        no_go_obs = [{"marker": computed, "channel": "stderr", "line": 1}]
    except ToolchainIdentityError as exc:
        args = exc.args
        computed = args[1] if len(args) > 1 else "NO-GO_TOOLCHAIN_IDENTITY"
        stdout = ""
        stderr = str(exc)
        exit_code = 1
        outcome = "exited"
        pass_obs = []
        no_go_obs = [{"marker": computed, "channel": "stderr", "line": 1}]
    finally:
        _cleanup_executor_material(executor_material)

    finished_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    subject_after = capture_subject_state(subject_dir)
    computed = apply_subject_drift_precedence(subject_before, subject_after, computed)

    receipt = Receipt(
        requirement_id="AUTHORITY_BOOTSTRAP",
        launcher_nonce=nonce,
        receipt_id=receipt_id,
        attempt_epoch_id=attempt_epoch_id,
        base_sha=base_sha,
        subject_commit_sha=subject_before.commit_sha,
        subject_tree_sha=subject_before.tree_sha,
        subject_parent_shas=list(subject_before.parent_shas),
        plan_sha256=expected_plan_sha256.lower().strip(),
        authority_block_sha256=authority_block_sha256,
        oracle_contract_sha256=oracle_contract_sha256,
        executor_material_sha256=executor_material_sha256,
        toolchain_identity_sha256=toolchain.digest(),
        argv=argv,
        argv_sha256=argv_sha256,
        environment_allowlist_sha256=env_allowlist_sha256,
        started_at_utc=started_at,
        finished_at_utc=finished_at,
        duration_monotonic_ms=int((time.monotonic() - start_mono) * 1000),
        timeout_ms=timeout_ms,
        process_outcome=outcome,
        exit_code=exit_code,
        signal=signo,
        spawn_error_class=(
            process_result.spawn_error_class
            if "process_result" in locals()
            else None
        ),
        stdout_bytes=len(stdout.encode("utf-8")),
        stdout_sha256=_hash_text(stdout),
        stderr_bytes=len(stderr.encode("utf-8")),
        stderr_sha256=_hash_text(stderr),
        runtime_binding_digest=runtime_binding_digest,
        pass_marker_observations=pass_obs,
        no_go_marker_observations=no_go_obs,
        artifact_sha256="0" * 64,
        computed_disposition=computed,
        branch_ref_before=subject_before.branch_ref,
        branch_ref_after=subject_after.branch_ref,
        dirty_state_before_sha256=subject_before.dirty_state_sha256(),
        dirty_state_after_sha256=subject_after.dirty_state_sha256(),
    )
    artifact_sha256 = receipt.digest()
    return Receipt(**{**receipt.as_dict(), "artifact_sha256": artifact_sha256})


def publish_receipt(output_path: Path, receipt: Receipt) -> None:
    payload = receipt.canonical_json().encode("utf-8")
    temp_path = output_path.parent / f".{output_path.name}.{uuid.uuid4().hex}.tmp"
    fd = -1
    try:
        fd = os.open(
            temp_path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
        )
        _write_all(fd, payload)
        os.fsync(fd)
        os.close(fd)
        fd = -1
        try:
            os.link(temp_path, output_path, follow_symlinks=False)
        except FileExistsError as exc:
            raise ReceiptError(
                "receipt target already exists",
                "NO-GO_RECEIPT_PROVENANCE",
            ) from exc
        temp_path.unlink()
        directory_fd = os.open(output_path.parent, os.O_RDONLY | os.O_CLOEXEC)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def cli() -> int:
    if sys.argv[1:] == ["oracle-child"]:
        return _oracle_child_main()

    parser = argparse.ArgumentParser(description="Phase 2 evidence receipt generator")
    subparsers = parser.add_subparsers(dest="command")

    gen = subparsers.add_parser("generate", help="Generate an AUTHORITY_BOOTSTRAP receipt")
    gen.add_argument("--plan", required=True, type=Path, help="Path to the owner-approved plan")
    gen.add_argument("--expected-sha256", required=True, help="Expected SHA-256 of the plan")
    gen.add_argument("--subject-dir", required=True, type=Path, help="Git worktree of the subject")
    gen.add_argument("--base-sha", required=True, help="Base commit SHA")
    gen.add_argument("--epoch", required=True, help="Attempt epoch ID")
    gen.add_argument("--timeout-ms", type=int, default=300_000, help="Timeout in milliseconds")
    gen.add_argument("--expected-toolchain-sha256", default=None, help="Expected toolchain identity SHA-256")
    gen.add_argument("--output", type=Path, default=None, help="Optional output path")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 2

    if args.command == "generate":
        try:
            receipt = generate_authority_bootstrap_receipt(
                plan_path=args.plan,
                expected_plan_sha256=args.expected_sha256,
                subject_dir=args.subject_dir,
                base_sha=args.base_sha,
                attempt_epoch_id=args.epoch,
                timeout_ms=args.timeout_ms,
                expected_toolchain_sha256=args.expected_toolchain_sha256,
            )
        except ReceiptError as exc:
            args_err = exc.args
            disposition = args_err[1] if len(args_err) > 1 else "NO-GO_RECEIPT_PROVENANCE"
            print(disposition, file=sys.stderr)
            print(f"{disposition}: {exc}", file=sys.stderr)
            return 97

        json_text = receipt.canonical_json()
        if args.output:
            try:
                publish_receipt(args.output, receipt)
            except ReceiptError as exc:
                print("NO-GO_RECEIPT_PROVENANCE", file=sys.stderr)
                print(str(exc), file=sys.stderr)
                return 97
        else:
            sys.stdout.write(json_text)
        return 0 if receipt.computed_disposition == "LOCAL_PASS" else 97

    return 2


if __name__ == "__main__":
    raise SystemExit(cli())
