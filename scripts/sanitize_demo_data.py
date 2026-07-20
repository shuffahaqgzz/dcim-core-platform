#!/usr/bin/env python3
"""Deterministically sanitize JSON or JSONL demo data without network access."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timedelta
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

IP_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
IPV6_RE = re.compile(r"(?<![\w:])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}(?![\w:])")
FQDN_RE = re.compile(r"(?i)\b(?=[a-z0-9.-]*[a-z])[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+\b")
INTERNAL_FQDN_RE = re.compile(r"(?i)\b[a-z0-9][a-z0-9.-]*\.(?:local|lan|corp|internal|office|prod)\b")
CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(?:password|passwd|pwd|token|secret|api[_-]?key|community(?:[_-]?string)?)\b\s*[:=]\s*\S+"
)
AUTHORIZATION_VALUE_RE = re.compile(r"(?i)\bauthorization\s*:\s*\S+")
URL_CREDENTIAL_RE = re.compile(
    r"(?i)\b(?:postgres(?:ql)?|mysql|redis|mongodb(?:\+srv)?)://[^\s/:]+:[^\s/@]+@"
)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
HOST_KEYS = {"hostname", "host", "fqdn", "device_name", "instance", "source_instance", "device", "node", "target"}
IP_KEYS = {"ip", "ip_address", "address", "target_ip"}
SERIAL_KEYS = {"serial", "serial_number", "asset_tag"}
LOCATION_KEYS = {"site", "building", "room", "rack", "location"}
CAMERA_KEYS = {"camera", "camera_name", "nvr", "nvr_name"}
ACCOUNT_KEYS = {"account", "user", "username"}
TIMESTAMP_KEYS = {"timestamp", "event_timestamp", "observed_at", "created_at", "updated_at"}
MESSAGE_KEYS = {"message", "raw_message", "description", "detail"}
URL_KEYS = {"url", "uri", "endpoint", "base_url"}
CREDENTIAL_KEYS = {
    "access_key",
    "api_key",
    "authorization",
    "client_secret",
    "community",
    "credential",
    "credential_ref",
    "credential_reference",
    "credentials",
    "password",
    "private_key",
    "secret",
    "secret_key",
    "signing_key",
    "token",
}
PRESERVE_KEYS = {"event_type", "schema_version", "priority", "connector", "transport", "metric", "status", "validation_status", "step", "result", "unit"}
UUID_KEYS = {"event_id", "correlation_id"}
PRESERVED_DOTTED_IDENTIFIERS = {"event_type", "schema_version"}
APPROVED_EVENT_TYPES = {
    "network.interface.utilization",
    "nvr.camera.health",
    "server.capacity.sample",
    "server.health.degraded",
    "storage.capacity.utilization",
    "synthetic.invalid",
    "ups.battery.alarm",
}
APPROVED_PRESERVED_VALUES = {
    "connector": {
        "isapi-fixture",
        "metrics-fixture",
        "redfish-fixture",
        "snmpv3-fixture",
    },
    "metric": {"battery_charge_percent"},
    "priority": {"P1", "P2", "P3"},
    "result": {"accepted", "ok"},
    "status": {"degraded"},
    "step": {"fixture-load", "schema-validate"},
    "transport": {"fixture", "redfish", "snmpv3", "syslog", "rest", "stream"},
    "unit": {"percent"},
    "validation_status": {"accepted", "quarantined"},
}
APPROVED_OBJECT_KEYS = {
    "account",
    "asset_identity",
    "at",
    "building",
    "camera_name",
    "capacity_gib",
    "ci_identity",
    "component",
    "connector",
    "correlation_id",
    "cpu_used_percent",
    "credential_ref",
    "description",
    "detail",
    "device_name",
    "enrichment",
    "event_id",
    "event_timestamp",
    "event_type",
    "expected_disposition",
    "expected_reason",
    "fqdn",
    "health",
    "host",
    "hostname",
    "identity_confidence",
    "instance",
    "interface_alias",
    "ip_address",
    "lineage",
    "location",
    "memory_used_percent",
    "message",
    "metadata_only",
    "metric",
    "native_event_id",
    "node",
    "nvr_name",
    "observed_at",
    "occurred_at",
    "payload",
    "pool",
    "priority",
    "quality_flags",
    "rack",
    "raw_message",
    "result",
    "room",
    "sample_window_seconds",
    "schema_version",
    "serial_number",
    "site",
    "source",
    "source_instance",
    "status",
    "step",
    "system",
    "target",
    "target_ip",
    "timestamp",
    "transport",
    "unit",
    "updated_at",
    "uri",
    "url",
    "used_percent",
    "user",
    "username",
    "utilization_percent",
    "validation_status",
    "value",
}
APPROVED_OBJECT_KEYS |= (
    HOST_KEYS
    | IP_KEYS
    | SERIAL_KEYS
    | LOCATION_KEYS
    | CAMERA_KEYS
    | ACCOUNT_KEYS
    | TIMESTAMP_KEYS
    | MESSAGE_KEYS
    | URL_KEYS
    | CREDENTIAL_KEYS
    | PRESERVE_KEYS
    | UUID_KEYS
)
DOC_NETWORKS = tuple(ipaddress.ip_network(item) for item in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32"))


def digest(salt: str, kind: str, value: str) -> str:
    return hmac.new(salt.encode("utf-8"), f"{kind}\0{value}".encode("utf-8"), hashlib.sha256).hexdigest()


def pseudonym(salt: str, kind: str, value: str, prefix: str) -> str:
    return f"{prefix}-{digest(salt, kind, value)[:12].upper()}"


def pseudonymous_uuid(salt: str, value: str) -> str:
    raw = bytearray(bytes.fromhex(digest(salt, "uuid", value)[:32]))
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(UUID(bytes=bytes(raw)))


def documentation_ip(salt: str, value: str) -> str:
    raw = int(digest(salt, "ip", value)[:8], 16)
    networks = ("192.0.2", "198.51.100", "203.0.113")
    return f"{networks[raw % len(networks)]}.{1 + ((raw // len(networks)) % 254)}"


def shifted_timestamp(salt: str, value: str) -> str:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return pseudonym(salt, "timestamp", value, "SYNTHETIC-TIME")
    days = 30 + int(digest(salt, "time-offset", "dataset")[:4], 16) % 335
    shifted = parsed + timedelta(days=days)
    result = shifted.isoformat()
    return result.replace("+00:00", "Z")


def sanitize_url(salt: str, value: str) -> str:
    parsed = urlsplit(value)
    scheme = parsed.scheme if parsed.scheme in {"http", "https"} else "https"
    host = pseudonym(salt, "hostname", parsed.hostname or value, "host").lower()
    return f"{scheme}://{host}.example.com/synthetic"


def sanitize_embedded(salt: str, value: str) -> str:
    def replace_ip(match: re.Match[str]) -> str:
        raw = match.group(0)
        try:
            ipaddress.ip_address(raw)
        except ValueError:
            return raw
        return documentation_ip(salt, raw)

    value = IP_RE.sub(replace_ip, value)
    value = IPV6_RE.sub(replace_ip, value)
    value = FQDN_RE.sub(lambda match: f"{pseudonym(salt, 'hostname', match.group(0), 'host').lower()}.example.com", value)
    return pseudonym(salt, "text", value, "SYNTHETIC-TEXT")


def normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def credential_like_key(key: str) -> bool:
    normalized = normalized_key(key)
    exact = {
        "apikey",
        "accesskey",
        "auth",
        "authorization",
        "community",
        "communitystring",
        "credential",
        "credentials",
        "credentialref",
        "credentialreference",
        "password",
        "privatekey",
        "passwd",
        "pwd",
        "secret",
        "secretkey",
        "signingkey",
        "token",
    }
    suffixes = (
        "accesstoken",
        "accesskey",
        "apikey",
        "authtoken",
        "authorization",
        "clientsecret",
        "communitystring",
        "credentialref",
        "credentialreference",
        "idtoken",
        "password",
        "passwordvalue",
        "privatekey",
        "refreshtoken",
        "secretvalue",
        "secretkey",
        "signingkey",
        "tokenvalue",
    )
    return normalized in exact or normalized.endswith(suffixes)


def sensitive_string_key(key: str) -> bool:
    lowered = key.lower()
    normalized = normalized_key(key)
    return (
        lowered in UUID_KEYS
        or lowered in HOST_KEYS
        or lowered in IP_KEYS
        or lowered in SERIAL_KEYS
        or lowered in LOCATION_KEYS
        or lowered in CAMERA_KEYS
        or lowered in ACCOUNT_KEYS
        or lowered in TIMESTAMP_KEYS
        or lowered in MESSAGE_KEYS
        or lowered in URL_KEYS
        or lowered in {"system", "native_event_id", "interface_alias", "pool", "component"}
        or normalized.endswith(
            (
                "identity",
                "nativeid",
                "deviceid",
                "sourceid",
                "assetid",
                "hostname",
                "fqdn",
                "sourceinstance",
                "devicename",
                "serial",
                "serialcode",
                "serialnumber",
                "assettag",
            )
        )
    )


def network_identity_findings(value: str, *, allow_dotted_identifier: bool = False) -> list[str]:
    findings: list[str] = []
    for pattern in (IP_RE, IPV6_RE):
        for candidate in pattern.findall(value):
            try:
                address = ipaddress.ip_address(candidate)
            except ValueError:
                continue
            if not any(address in network for network in DOC_NETWORKS):
                findings.append("non-documentation IP remains")
    if INTERNAL_FQDN_RE.search(value):
        findings.append("non-documentation FQDN remains")
    elif not allow_dotted_identifier:
        for hostname in FQDN_RE.findall(value):
            if not hostname.lower().endswith((".example.com", ".example.net", ".example.org", ".example.invalid")):
                findings.append("non-documentation FQDN remains")
    return findings


def credential_content_findings(value: str) -> list[str]:
    patterns = (
        CREDENTIAL_VALUE_RE,
        AUTHORIZATION_VALUE_RE,
        URL_CREDENTIAL_RE,
        PRIVATE_KEY_RE,
    )
    return ["credential material remains"] if any(pattern.search(value) for pattern in patterns) else []


def validate_object_key(key: object) -> str:
    if not isinstance(key, str):
        raise ValueError("object key must be a string")
    if network_identity_findings(key):
        raise ValueError("object key contains sensitive network identity")
    if key not in APPROVED_OBJECT_KEYS:
        raise ValueError("object key is not approved for sanitized output")
    return key


def validate_preserved_value(key: str, value: str) -> None:
    lowered = key.lower()
    if credential_content_findings(value):
        raise ValueError("preserved semantic field contains credential material")
    if lowered == "event_type" and value not in APPROVED_EVENT_TYPES:
        raise ValueError("event_type is not approved for sanitized output")
    if lowered == "schema_version" and value != "0.1.0":
        raise ValueError("schema_version is not approved for sanitized output")
    approved = APPROVED_PRESERVED_VALUES.get(lowered)
    if approved is not None and value not in approved:
        raise ValueError(f"{lowered} is not approved for sanitized output")


def sanitize_scalar(key: str, value: Any, salt: str) -> Any:
    lowered = key.lower()
    normalized = normalized_key(key)
    if lowered in CREDENTIAL_KEYS or credential_like_key(key):
        return "<REMOVED>"
    if not isinstance(value, str):
        if lowered in PRESERVE_KEYS:
            raise ValueError("preserved semantic field must be a string")
        if sensitive_string_key(key):
            raise ValueError("sensitive identifier must be a string")
        return value
    if lowered in UUID_KEYS:
        return pseudonymous_uuid(salt, value)
    if lowered in {"system", "native_event_id", "interface_alias", "pool", "component"} or any(marker in normalized for marker in ("identity", "nativeid", "deviceid", "sourceid", "assetid")):
        return pseudonym(salt, "identity", value, "SYNTHETIC-ID")
    if lowered in HOST_KEYS or any(marker in normalized for marker in ("hostname", "fqdn", "sourceinstance", "devicename")):
        return f"{pseudonym(salt, 'hostname', value, 'host').lower()}.example.com"
    if lowered in IP_KEYS:
        return documentation_ip(salt, value)
    if lowered in SERIAL_KEYS or "serial" in normalized or "assettag" in normalized:
        return pseudonym(salt, "serial", value, "SYNTHETIC-SERIAL")
    if lowered in LOCATION_KEYS:
        return pseudonym(salt, "location", value, "GENERIC-LOCATION")
    if lowered in CAMERA_KEYS:
        return pseudonym(salt, "camera", value, "GENERIC-CAMERA")
    if lowered in ACCOUNT_KEYS:
        return pseudonym(salt, "account", value, "SYNTHETIC-USER")
    if lowered in TIMESTAMP_KEYS:
        return shifted_timestamp(salt, value)
    if lowered in MESSAGE_KEYS or lowered.endswith(("_message", "_description", "_detail", "_reason")):
        return pseudonym(salt, "message", value, "REGENERATED-MESSAGE")
    if lowered in URL_KEYS:
        return sanitize_url(salt, value)
    if lowered in PRESERVE_KEYS:
        validate_preserved_value(lowered, value)
        return value
    return sanitize_embedded(salt, value)


def residual_findings(value: Any, key: str = "") -> list[str]:
    findings: list[str] = []
    if key and credential_like_key(key) and value != "<REMOVED>":
        findings.append("credential-like field remains")
    if key and sensitive_string_key(key) and not isinstance(value, str):
        findings.append("sensitive identifier has an unsafe non-string type")
    if isinstance(value, dict):
        for name, item in value.items():
            findings.extend(network_identity_findings(str(name)))
            findings.extend(residual_findings(item, str(name)))
        return findings
    if isinstance(value, list):
        for item in value:
            findings.extend(residual_findings(item, key))
        return findings
    if not isinstance(value, str):
        return findings
    normalized = normalized_key(key)
    if credential_like_key(key) and value != "<REMOVED>":
        findings.append("credential-like field remains")
    allow_dotted_identifier = False
    if key.lower() in PRESERVED_DOTTED_IDENTIFIERS:
        try:
            validate_preserved_value(key, value)
        except ValueError:
            findings.append("preserved semantic field is not approved")
        else:
            allow_dotted_identifier = True
    findings.extend(
        network_identity_findings(
            value,
            allow_dotted_identifier=allow_dotted_identifier,
        )
    )
    findings.extend(credential_content_findings(value))
    return findings


def sanitize(value: Any, salt: str, key: str = "") -> Any:
    if key and credential_like_key(key):
        return "<REMOVED>"
    if key and sensitive_string_key(key) and not isinstance(value, str):
        raise ValueError("sensitive identifier must be a string")
    if isinstance(value, dict):
        return {
            validate_object_key(name): sanitize(item, salt, str(name))
            for name, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize(item, salt, key) for item in value]
    return sanitize_scalar(key, value, salt)


def load_input(path: Path) -> tuple[list[Any], bool]:
    text = path.read_text(encoding="utf-8")
    try:
        value = json.loads(text)
        return [value], False
    except json.JSONDecodeError:
        records: list[Any] = []
        for line_no, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at line {line_no}: {exc.msg}") from exc
        if not records:
            raise ValueError("input contains no JSON records")
        return records, True


def write_output(path: Path, records: list[Any], jsonl: bool) -> None:
    if jsonl:
        text = "".join(json.dumps(record, sort_keys=True) + "\n" for record in records)
    else:
        text = json.dumps(records[0], indent=2, sort_keys=True) + "\n"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(text)
            temporary.flush()
            os.fsync(temporary.fileno())
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--salt", help="Caller-supplied salt; never hardcoded or logged")
    args = parser.parse_args(argv)
    if not args.salt:
        print("ERROR: --salt is required", file=sys.stderr)
        return 2
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError("output path must differ from input path")
        records, jsonl = load_input(args.input)
        sanitized = [sanitize(copy.deepcopy(record), args.salt) for record in records]
        residual = [item for record in sanitized for item in residual_findings(record)]
        if residual:
            raise ValueError(f"sanitization failed closed: {len(residual)} residual sensitive value(s)")
        write_output(args.output, sanitized, jsonl)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
