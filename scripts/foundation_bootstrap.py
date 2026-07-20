#!/usr/bin/env python3
"""Create synthetic dcim-build runtime material outside the public repository."""

from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
import secrets
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SECRET_NAMES = (
    "postgres-superuser-password",
    "postgres-monitor-password",
    "postgres-smoke-password",
    "grafana-admin-user",
    "grafana-admin-password",
)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def protected_value(name: str) -> str:
    if name == "grafana-admin-user":
        return "dcim_synthetic_admin\n"
    return secrets.token_urlsafe(32) + "\n"


def kafka_cluster_id() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(16)).decode("ascii").rstrip("=")


def write_new(path: Path, value: str, mode: int = 0o600) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(value)
    path.chmod(mode)


def bootstrap(runtime_root: Path) -> None:
    root = runtime_root.expanduser().resolve()
    if is_relative_to(root, REPOSITORY_ROOT):
        raise ValueError("DCIM_RUNTIME_ROOT must resolve outside repository")

    plane = root / "dev-build"
    secret_dir = plane / "secrets"
    targets = [secret_dir / name for name in SECRET_NAMES] + [plane / "runtime.env"]
    existing = [path for path in targets if path.exists()]
    if existing:
        raise FileExistsError("refusing to overwrite existing dcim-build runtime material")

    old_umask = os.umask(0o077)
    try:
        secret_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        root.chmod(0o700)
        plane.chmod(0o700)
        secret_dir.chmod(0o700)
        values = {name: protected_value(name) for name in SECRET_NAMES}
        for name, value in values.items():
            write_new(secret_dir / name, value, 0o444)
        write_new(
            plane / "runtime.env",
            "COMPOSE_PROJECT_NAME=dcim-build\n"
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
