#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVENT_DIR = Path("fixtures/synthetic/events")
SCHEMA_PATH = Path("schemas/event-envelope.schema.json")


def load_module(name: str, path: Path, errors: list[str]) -> ModuleType | None:
    if not path.is_file():
        errors.append(f"missing validator script: {path}")
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        errors.append(f"unable to import validator script: {path}")
        return None
    module = importlib.util.module_from_spec(spec)
    script_dir = str(path.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    try:
        spec.loader.exec_module(module)
    except (ImportError, OSError, RuntimeError, SyntaxError) as exc:
        errors.append(f"unable to import {path.name}: {exc}")
        return None
    return module


def string_values(node: ast.AST) -> frozenset[str] | None:
    if not isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        return None
    values = [item.value for item in node.elts if isinstance(item, ast.Constant) and isinstance(item.value, str)]
    return frozenset(values) if len(values) == len(node.elts) else None


def is_transport_get(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "transport"
    )


def parse_validate_json_transports(path: Path, errors: list[str]) -> frozenset[str] | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        errors.append(f"unable to parse {path.name}: {exc}")
        return None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.In)
            and is_transport_get(node.left)
        ):
            values = string_values(node.comparators[0])
            if values is not None:
                return values
    errors.append("validate-json.py has no parseable source.transport allowlist")
    return None


def parse_sanitizer_transports(path: Path, errors: list[str]) -> frozenset[str] | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        errors.append(f"unable to parse {path.name}: {exc}")
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "APPROVED_PRESERVED_VALUES" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            break
        for key, value in zip(node.value.keys, node.value.values, strict=True):
            if isinstance(key, ast.Constant) and key.value == "transport":
                values = string_values(value)
                if values is not None:
                    return values
    errors.append("sanitize_demo_data.py has no parseable transport allowlist")
    return None


def load_schema_transports(root: Path, errors: list[str]) -> tuple[frozenset[str], set[str]] | None:
    try:
        schema = json.loads((root / SCHEMA_PATH).read_text(encoding="utf-8"))
        transports = schema["properties"]["source"]["properties"]["transport"]["enum"]
    except (KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
        errors.append(f"unable to load event transport enum: {exc}")
        return None
    if not isinstance(transports, list) or not all(isinstance(item, str) for item in transports):
        errors.append("event transport enum must be an array of strings")
        return None
    values = frozenset(transports)
    if len(values) != len(transports):
        errors.append("event transport enum contains duplicates")
        return None
    required = schema.get("required", [])
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        errors.append("event schema required fields must be an array of strings")
        return None
    return values, set(required)


def validate_event_fixtures(
    root: Path, validate_json: ModuleType, required: set[str], errors: list[str]
) -> None:
    event_root = root / EVENT_DIR
    paths = sorted(event_root.glob("*.json"))
    if not paths:
        errors.append("no synthetic event fixtures found")
        return
    priorities: set[str] = set()
    validate_event = getattr(validate_json, "validate_event", None)
    if not callable(validate_event):
        errors.append("validate-json.py does not expose validate_event")
        return
    for path in paths:
        try:
            event: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(root)}: invalid JSON: {exc}")
            continue
        validate_event(event, path, required, errors)
        if isinstance(event, dict) and isinstance(event.get("priority"), str):
            priorities.add(event["priority"])
    missing_priorities = {"P1", "P2", "P3"} - priorities
    if missing_priorities:
        errors.append(f"event fixtures missing priorities: {sorted(missing_priorities)}")


def validate_required_fixtures(root: Path, fixture_validator: ModuleType, errors: list[str]) -> None:
    required = getattr(fixture_validator, "REQUIRED", None)
    if not isinstance(required, tuple) or not all(isinstance(item, str) for item in required):
        errors.append("validate_synthetic_fixtures.py does not expose REQUIRED fixture paths")
        return
    fixture_root = root / "fixtures" / "synthetic"
    for relative_path in required:
        if not (fixture_root / relative_path).is_file():
            errors.append(f"missing required fixture: {relative_path}")


def main(root: Path = ROOT) -> int:
    root = root.resolve()
    errors: list[str] = []
    schema_result = load_schema_transports(root, errors)
    validate_json_path = root / "scripts" / "validate-json.py"
    sanitizer_path = root / "scripts" / "sanitize_demo_data.py"
    fixture_validator_path = root / "scripts" / "validate_synthetic_fixtures.py"

    validate_json = load_module("contract_validate_json", validate_json_path, errors)
    fixture_validator = load_module("contract_fixture_validator", fixture_validator_path, errors)
    validate_json_transports = parse_validate_json_transports(validate_json_path, errors)
    sanitizer_transports = parse_sanitizer_transports(sanitizer_path, errors)

    if schema_result is not None:
        schema_transports, required = schema_result
        for name, transports in (
            ("validate-json.py", validate_json_transports),
            ("sanitize_demo_data.py", sanitizer_transports),
        ):
            if transports is not None and transports != schema_transports:
                errors.append(
                    f"transport enum differs between event schema and {name}: "
                    f"schema={sorted(schema_transports)}, {name}={sorted(transports)}"
                )
        if validate_json is not None:
            validate_event_fixtures(root, validate_json, required, errors)
    if fixture_validator is not None:
        validate_required_fixtures(root, fixture_validator, errors)

    if errors:
        print("Contract compatibility validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Contract compatibility validation passed.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: script parent)")
    arguments = parser.parse_args()
    raise SystemExit(main(arguments.root))
