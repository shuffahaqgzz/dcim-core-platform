#!/usr/bin/env python3
"""Parse repository JSON and validate synthetic event fixtures without network dependencies."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
EVENT_DIR = ROOT / "fixtures" / "synthetic" / "events"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def is_uuid(value: object) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def is_utc_datetime(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0


def load_json(path: Path, errors: list[str]) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
        return None


def validate_event(data: object, path: Path, required: set[str], errors: list[str]) -> None:
    rel = path.relative_to(ROOT)
    require(isinstance(data, dict), f"{rel}: root must be an object", errors)
    if not isinstance(data, dict):
        return

    missing = sorted(required - set(data))
    require(not missing, f"{rel}: missing required keys: {missing}", errors)
    require(data.get("schema_version") == "0.1.0", f"{rel}: unsupported schema_version", errors)
    require(is_uuid(data.get("event_id")), f"{rel}: event_id must be a UUID", errors)
    require(is_uuid(data.get("correlation_id")), f"{rel}: correlation_id must be a UUID", errors)
    require(is_utc_datetime(data.get("occurred_at")), f"{rel}: occurred_at must be UTC date-time ending Z", errors)
    require(is_utc_datetime(data.get("observed_at")), f"{rel}: observed_at must be UTC date-time ending Z", errors)
    require(data.get("priority") in {"P1", "P2", "P3"}, f"{rel}: invalid priority", errors)
    require(isinstance(data.get("event_type"), str) and bool(data.get("event_type")), f"{rel}: event_type required", errors)
    require(isinstance(data.get("payload"), dict), f"{rel}: payload must be an object", errors)

    source = data.get("source")
    require(isinstance(source, dict), f"{rel}: source must be an object", errors)
    if isinstance(source, dict):
        for key in ("system", "instance", "connector", "transport"):
            require(isinstance(source.get(key), str) and bool(source.get(key)), f"{rel}: source.{key} required", errors)
        require(source.get("transport") in {"fixture", "redfish", "snmpv3", "syslog", "rest", "stream"}, f"{rel}: unsupported source.transport", errors)

    enrichment = data.get("enrichment")
    require(isinstance(enrichment, dict), f"{rel}: enrichment must be an object", errors)
    if isinstance(enrichment, dict):
        require(enrichment.get("validation_status") in {"accepted", "quarantined"}, f"{rel}: invalid validation_status", errors)
        lineage = enrichment.get("lineage")
        require(isinstance(lineage, list) and len(lineage) > 0, f"{rel}: lineage must be non-empty", errors)
        if isinstance(lineage, list):
            for index, item in enumerate(lineage):
                require(isinstance(item, dict), f"{rel}: lineage[{index}] must be an object", errors)
                if isinstance(item, dict):
                    require(isinstance(item.get("step"), str) and bool(item.get("step")), f"{rel}: lineage[{index}].step required", errors)
                    require(is_utc_datetime(item.get("at")), f"{rel}: lineage[{index}].at must be UTC", errors)


def main() -> int:
    errors: list[str] = []
    json_paths = sorted(ROOT.rglob("*.json"))
    loaded: dict[Path, object] = {}
    for path in json_paths:
        data = load_json(path, errors)
        if data is not None:
            loaded[path] = data

    event_schema_path = SCHEMA_DIR / "event-envelope.schema.json"
    event_schema = loaded.get(event_schema_path)
    require(isinstance(event_schema, dict), "event schema missing or invalid", errors)
    required: set[str] = set()
    if isinstance(event_schema, dict):
        require(event_schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "event schema must use JSON Schema 2020-12", errors)
        require(event_schema.get("type") == "object", "event schema root type must be object", errors)
        required = set(event_schema.get("required", []))

    for path in sorted(EVENT_DIR.glob("*.json")):
        validate_event(loaded.get(path), path, required, errors)

    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = loaded.get(schema_path)
        require(isinstance(schema, dict), f"{schema_path.relative_to(ROOT)}: schema root must be object", errors)
        if isinstance(schema, dict):
            require("$id" in schema and "$schema" in schema and "type" in schema, f"{schema_path.relative_to(ROOT)}: missing schema metadata", errors)

    if errors:
        print("JSON validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"JSON validation passed ({len(json_paths)} files; {len(list(EVENT_DIR.glob('*.json')))} event fixtures).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
