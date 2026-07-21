"""Protected external runtime path handling for synthetic foundation tools."""

from __future__ import annotations

import os
from pathlib import Path
import re
import secrets
import stat


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PROJECT = re.compile(r"dcim-build(?:-acceptance-[a-z0-9]{12,32})?\Z")
ACCEPTANCE_COMPOSE_PROJECT = re.compile(r"dcim-build-acceptance-[a-z0-9]{12,32}\Z")


def validate_compose_project_name(value: str, *, acceptance_only: bool = False) -> str:
    """Validate the narrow synthetic Compose project namespace contract."""

    pattern = ACCEPTANCE_COMPOSE_PROJECT if acceptance_only else COMPOSE_PROJECT
    if not pattern.fullmatch(value):
        if acceptance_only:
            raise ValueError("acceptance Compose project name is not allowlisted")
        raise ValueError("Compose project name is not allowlisted")
    return value


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def _reject_symbolic_links(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError("protected runtime path contains a symbolic link")


def external_runtime_root(path: Path) -> Path:
    """Return an absolute, non-symlinked runtime root outside this repository."""

    root = _absolute(path)
    _reject_symbolic_links(root)
    resolved = root.resolve(strict=False)
    repository = REPOSITORY_ROOT.resolve()
    if resolved == Path(resolved.anchor) or resolved == Path.home().resolve():
        raise ValueError("DCIM_RUNTIME_ROOT must be a dedicated directory")
    if resolved == repository or repository in resolved.parents:
        raise ValueError("DCIM_RUNTIME_ROOT must resolve outside repository")
    return root


def _validate_child_parts(parts: tuple[str, ...]) -> None:
    for raw in parts:
        child = Path(raw)
        if not raw or child.is_absolute() or len(child.parts) != 1 or ".." in child.parts:
            raise ValueError("invalid protected runtime path")


def ensure_protected_directory(runtime_root: Path, *parts: str) -> Path:
    """Create one owner-only runtime directory chain without following symlinks."""

    _validate_child_parts(parts)
    root = external_runtime_root(runtime_root)
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        pass
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(root, flags)
    current = root
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("protected runtime path component is not a directory")
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise ValueError("protected runtime directory must be owner-only and owner-controlled")
        for part in parts:
            try:
                os.mkdir(part, mode=0o700, dir_fd=descriptor)
            except FileExistsError:
                pass
            link_metadata = os.stat(part, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISLNK(link_metadata.st_mode):
                raise ValueError("protected runtime path contains a symbolic link")
            child_descriptor = os.open(part, flags, dir_fd=descriptor)
            child_metadata = os.fstat(child_descriptor)
            if (
                not stat.S_ISDIR(child_metadata.st_mode)
                or child_metadata.st_uid != os.getuid()
                or stat.S_IMODE(child_metadata.st_mode) != 0o700
            ):
                os.close(child_descriptor)
                raise ValueError(
                    "protected runtime directory must be owner-only and owner-controlled"
                )
            os.close(descriptor)
            descriptor = child_descriptor
            current /= part
    finally:
        os.close(descriptor)
    external_runtime_root(current)
    return current


def protected_runtime_path(runtime_root: Path, *parts: str) -> Path:
    """Resolve a runtime child after validating its existing path components."""

    root = external_runtime_root(runtime_root)
    _validate_child_parts(parts)
    target = root.joinpath(*parts)
    _reject_symbolic_links(target)
    resolved = target.resolve(strict=False)
    try:
        resolved.relative_to(root.resolve(strict=False))
    except ValueError as error:
        raise ValueError("protected runtime path escaped runtime root") from error
    repository = REPOSITORY_ROOT.resolve()
    if resolved == repository or repository in resolved.parents:
        raise ValueError("protected runtime path must remain outside repository")
    return target


def write_protected_text(
    runtime_root: Path,
    parts: tuple[str, ...],
    value: str,
    *,
    mode: int = 0o600,
) -> Path:
    """Atomically replace one protected runtime text file without following links."""

    target = protected_runtime_path(runtime_root, *parts)
    parent = target.parent
    parent_flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    parent_descriptor = os.open(parent, parent_flags)
    parent_metadata = os.fstat(parent_descriptor)
    if (
        parent_metadata.st_uid != os.getuid()
        or stat.S_IMODE(parent_metadata.st_mode) != 0o700
    ):
        os.close(parent_descriptor)
        raise ValueError(
            "protected runtime directory must be owner-only and owner-controlled"
        )
    temporary_name = f".{target.name}.{secrets.token_hex(12)}"
    descriptor = os.open(
        temporary_name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        mode,
        dir_fd=parent_descriptor,
    )
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(
            temporary_name,
            target.name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary_name, dir_fd=parent_descriptor)
        except FileNotFoundError:
            pass
        os.close(parent_descriptor)
    return target
