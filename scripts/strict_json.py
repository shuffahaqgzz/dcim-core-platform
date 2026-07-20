"""Fail-closed JSON object loading for governed repository/runtime contracts."""

from __future__ import annotations

import json
from pathlib import Path


class DuplicateKeyError(ValueError):
    """Raised when JSON contains duplicate object members."""


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def loads_object(raw: str, source: str) -> dict[str, object]:
    value = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise ValueError(f"{source} must contain a JSON object")
    return value


def load_object(path: Path) -> dict[str, object]:
    return loads_object(path.read_text(encoding="utf-8"), path.name)
