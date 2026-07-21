#!/usr/bin/env python3
"""Create synthetic dcim-build runtime material outside the public repository."""

from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
import secrets
import stat
import sys

try:
    from scripts.protected_runtime import ensure_protected_directory, protected_runtime_path
except ModuleNotFoundError:
    from protected_runtime import ensure_protected_directory, protected_runtime_path


SECRET_NAMES = (
    "postgres-superuser-password",
    "postgres-monitor-password",
    "postgres-smoke-password",
    "grafana-admin-user",
    "grafana-admin-password",
)


def protected_value(name: str) -> str:
    if name == "grafana-admin-user":
        return "dcim_synthetic_admin\n"
    return secrets.token_urlsafe(32) + "\n"


def kafka_cluster_id() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(16)).decode("ascii").rstrip("=")


def write_new(directory: Path, name: str, value: str, mode: int = 0o600) -> None:
    if Path(name).name != name:
        raise ValueError("invalid protected runtime filename")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    directory_descriptor = os.open(directory, directory_flags)
    metadata = os.fstat(directory_descriptor)
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        os.close(directory_descriptor)
        raise ValueError("protected runtime directory must be owner-only and owner-controlled")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, mode, dir_fd=directory_descriptor)
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
    finally:
        os.close(directory_descriptor)


def bootstrap(runtime_root: Path) -> None:
    secret_dir = ensure_protected_directory(runtime_root, "dev-build", "secrets")
    plane = secret_dir.parent
    root = protected_runtime_path(runtime_root)
    targets = [secret_dir / name for name in SECRET_NAMES] + [plane / "runtime.env"]
    existing = [path for path in targets if path.exists() or path.is_symlink()]
    if existing:
        raise FileExistsError("refusing to overwrite existing dcim-build runtime material")

    old_umask = os.umask(0o077)
    try:
        values = {name: protected_value(name) for name in SECRET_NAMES}
        for name, value in values.items():
            write_new(secret_dir, name, value, 0o444)
        write_new(
            plane,
            "runtime.env",
            "COMPOSE_PROJECT_NAME=dcim-build\n"
            f"DCIM_RUNTIME_ROOT={root}\n"
            f"KAFKA_CLUSTER_ID={kafka_cluster_id()}\n",
        )
    finally:
        os.umask(old_umask)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        bootstrap(arguments.runtime_root)
    except (FileExistsError, OSError, ValueError) as error:
        print(f"foundation-bootstrap: {error}", file=sys.stderr)
        return 1
    print("foundation-bootstrap: created protected synthetic dcim-build material")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
