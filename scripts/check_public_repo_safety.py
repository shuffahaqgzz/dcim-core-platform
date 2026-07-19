#!/usr/bin/env python3
"""Scan project files for material prohibited from a public repository."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = ROOT / ".public-safety-allowlist"
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules", "dist", "build"}
FORBIDDEN_DIRS = {"secrets", "credentials", "certs", "private", "runtime", "runtime-data", "state", "data", "volumes", "inventory", "inventories", "source-inventory", "captures", "packet-captures", "dumps", "backups", "exports", "recordings", "logs", ".hermes", "hermes-state", "hermes-memory", "hermes-sessions"}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".crt", ".cer", ".csr", ".pcap", ".pcapng", ".har", ".sql", ".dump", ".sqlite", ".sqlite3", ".db", ".zip", ".tar", ".tgz", ".gz", ".7z", ".rar", ".log"}
FORBIDDEN_NAMES = {".env", "id_rsa", "id_ed25519"}
DOC_NETWORKS = tuple(ipaddress.ip_network(value) for value in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32"))
IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
IPV6_RE = re.compile(r"(?<![\w:])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}(?![\w:])")
CREDENTIAL_RE = re.compile(r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key|community(?:[_-]?string)?)\b\s*[:=]\s*(\$\{\{\s*secrets\.[A-Z0-9_]+\s*\}\}|[^\s#,;]+)")
AUTHORIZATION_RE = re.compile(r"(?i)\bauthorization\s*:\s*([^\s#,;]+)")
URL_CREDENTIAL_RE = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|redis|mongodb(?:\+srv)?)://[^\s/:]+:[^\s/@]+@")
INTERNAL_FQDN_RE = re.compile(r"(?i)\b[a-z0-9][a-z0-9.-]*\.(?:local|lan|corp|internal|office|prod)\b")
FQDN_RE = re.compile(r"(?i)\b(?=[a-z0-9.-]*[a-z])[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+\b")
OPERATIONAL_FQDN_RE = re.compile(r"(?i)\b[a-z0-9-]*(?:bmc|host|server|switch|router|ups|nas|nvr|camera|device)[a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:com|net|org|io|co|id)\b")
ENDPOINT_ASSIGN_RE = re.compile(r"(?i)[\"']?[A-Z0-9_]*(?:endpoint|hostname|fqdn|host|target|base_url|url)[A-Z0-9_]*[\"']?\s*[:=]\s*(?P<quote>[\"']?)(?P<value>[^\s\"'#,;}\]]+)")
DATABASE_DUMP_RE = re.compile(r"(?im)^-- (?:PostgreSQL|MySQL) database dump|^COPY\s+\S+\s+FROM\s+stdin;|^CREATE\s+DATABASE\s+")
SYNTHETIC_ID_FIELDS_RE = re.compile(r'(?i)["\'](?:serial(?:_number)?|asset_tag|rack|site|camera_name)["\']\s*:\s*["\']([^"\']+)["\']')
HIGH_CONFIDENCE_PATTERNS = (
    ("private-key", "private key material", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("certificate", "certificate material", re.compile(r"-----BEGIN " r"CERTIFICATE-----")),
    ("aws-key", "AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", "GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("slack-token", "Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("google-key", "Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
)
PLACEHOLDER_VALUES = {"", "none", "null", "unset", "not-set", "not_set", "redacted", "masked", "example", "dummy", "synthetic", "changeme", "change-me", "change_me", "replace-me", "replace_me", "set-locally", "set_locally"}
ANGLE_PLACEHOLDERS = {"<SET_LOCALLY>", "<REMOVED>", "<REDACTED>", "<MASKED>", "<GENERATE_LOCALLY>", "<PRIVATE-REFERENCE>", "<SECRET-STORE-REFERENCE>"}
# Reserved for future low-risk, fingerprint-bound rules. Sensitive rules are never allowlistable.
ALLOWLISTABLE_RULES: set[str] = set()
APPROVED_PUBLIC_DOMAINS = ("github.com", "openai.com", "json-schema.org")
STRUCTURED_SUFFIXES = {".json", ".jsonl"}


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int | None
    message: str
    detected: str = "<redacted>"


def is_placeholder(value: str) -> bool:
    cleaned = value.strip().strip("'\"").rstrip(",;")
    lowered = cleaned.lower()
    return lowered in PLACEHOLDER_VALUES or cleaned in ANGLE_PLACEHOLDERS or bool(re.fullmatch(r"\$\{[A-Z][A-Z0-9_]*\}", cleaned)) or bool(re.fullmatch(r"\{\{[A-Z][A-Z0-9_]*\}\}", cleaned)) or bool(re.fullmatch(r"\$\{\{\s*secrets\.[A-Z0-9_]+\s*\}\}", cleaned, re.IGNORECASE))


def project_files(root: Path = ROOT) -> list[Path]:
    try:
        result = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"], check=True, capture_output=True)
        paths = [root / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]
        return sorted(path for path in paths if path.is_file() or path.is_symlink())
    except (FileNotFoundError, subprocess.CalledProcessError, UnicodeDecodeError):
        paths: list[Path] = []
        for current, dirs, names in os.walk(root):
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
            paths.extend(Path(current) / name for name in names)
        return sorted(path for path in paths if path.is_file())


def load_allowlist(path: Path) -> list[tuple[str, str, str]]:
    if not path.exists():
        return []
    entries: list[tuple[str, str, str]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|", 2)]
        if len(parts) != 3 or not all(parts):
            raise ValueError(f"invalid allowlist entry at line {line_no}; expected RULE|PATH_GLOB|REASON")
        if parts[0] not in ALLOWLISTABLE_RULES:
            raise ValueError(f"rule is not allowlistable at line {line_no}")
        if any(marker in parts[1] for marker in ("*", "?", "[")):
            raise ValueError(f"allowlist path must be exact at line {line_no}")
        entries.append((parts[0], parts[1], parts[2]))
    return entries


def allowed(finding: Finding, entries: list[tuple[str, str, str]]) -> bool:
    return finding.rule in ALLOWLISTABLE_RULES and any(finding.rule == rule and finding.path == pattern for rule, pattern, _reason in entries)


def path_findings(path: Path, root: Path = ROOT) -> list[Finding]:
    rel = path.relative_to(root).as_posix()
    parts = set(path.relative_to(root).parts[:-1])
    findings: list[Finding] = []
    if path.is_symlink():
        findings.append(Finding("symlink", rel, None, "symlink is prohibited in public-safety scan scope"))
    if parts & FORBIDDEN_DIRS or rel.startswith(("evidence/private/", "screenshots/private/")):
        findings.append(Finding("forbidden-path", rel, None, "private or runtime directory is prohibited"))
    if path.name in FORBIDDEN_NAMES and path.name != ".env.example":
        findings.append(Finding("forbidden-name", rel, None, "sensitive filename is prohibited"))
    if path.name.startswith(".env.") and path.name != ".env.example":
        findings.append(Finding("environment-file", rel, None, "environment file must stay outside Git"))
    lowered = path.name.lower()
    if any(lowered.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
        findings.append(Finding("forbidden-extension", rel, None, "sensitive, dump, log, or archive extension is prohibited"))
    return findings


def _line(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def credential_like_key(value: str) -> bool:
    normalized = normalized_key(value)
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


def structured_credential_findings(text: str, rel: str) -> list[Finding]:
    if Path(rel).suffix.lower() not in STRUCTURED_SUFFIXES:
        return []
    try:
        if rel.lower().endswith(".jsonl"):
            values = [json.loads(line) for line in text.splitlines() if line.strip()]
        else:
            values = [json.loads(text)]
    except json.JSONDecodeError:
        return [
            Finding(
                "structured-data-parse-error",
                rel,
                None,
                "structured data could not be parsed for credential inspection",
            )
        ]

    findings: list[Finding] = []

    def contains_nonplaceholder_scalar(value: object) -> bool:
        if isinstance(value, dict):
            return any(contains_nonplaceholder_scalar(item) for item in value.values())
        if isinstance(value, list):
            return any(contains_nonplaceholder_scalar(item) for item in value)
        rendered = "" if value is None else str(value)
        return not is_placeholder(rendered)

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for name, item in value.items():
                if credential_like_key(str(name)) and contains_nonplaceholder_scalar(item):
                    position = text.find(json.dumps(str(name)))
                    findings.append(
                        Finding(
                            "structured-credential-field",
                            rel,
                            _line(text, max(position, 0)),
                            f"structured credential field #{len(findings) + 1} contains a non-placeholder value",
                        )
                    )
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for value in values:
        visit(value)
    return findings


def text_findings(text: str, rel: str) -> list[Finding]:
    findings: list[Finding] = []
    for rule, label, pattern in HIGH_CONFIDENCE_PATTERNS:
        for match in pattern.finditer(text):
            findings.append(Finding(rule, rel, _line(text, match.start()), label))
    for rule, label, pattern in (("url-credential", "credential embedded in connection URL", URL_CREDENTIAL_RE), ("authorization-header", "Authorization header contains a value", AUTHORIZATION_RE), ("internal-fqdn", "real-looking internal hostname/FQDN", INTERNAL_FQDN_RE), ("operational-fqdn", "real-looking operational hostname/FQDN", OPERATIONAL_FQDN_RE), ("database-dump", "database dump marker", DATABASE_DUMP_RE)):
        for match in pattern.finditer(text):
            value = match.group(1) if match.lastindex else match.group(0)
            if rule == "authorization-header" and is_placeholder(value):
                continue
            if rule == "operational-fqdn" and value.lower().endswith((".example.com", ".example.net", ".example.org", ".example.invalid")):
                continue
            findings.append(Finding(rule, rel, _line(text, match.start()), label))
    for line_no, line_text in enumerate(text.splitlines(), 1):
        for match in CREDENTIAL_RE.finditer(line_text):
            if not is_placeholder(match.group(2)):
                findings.append(Finding("credential-assignment", rel, line_no, f"possible non-placeholder {match.group(1)} assignment"))
        for match in ENDPOINT_ASSIGN_RE.finditer(line_text):
            endpoint_value = match.group("value")
            if rel.endswith(".py") and not match.group("quote") and "://" not in endpoint_value:
                continue
            for hostname in FQDN_RE.findall(endpoint_value):
                lowered_host = hostname.lower()
                if any(lowered_host == domain or lowered_host.endswith("." + domain) for domain in APPROVED_PUBLIC_DOMAINS):
                    continue
                if not lowered_host.endswith((".example.com", ".example.net", ".example.org", ".example.invalid")):
                    findings.append(Finding("endpoint-fqdn", rel, line_no, "endpoint assignment contains non-documentation FQDN"))
        for pattern in (IPV4_RE, IPV6_RE):
            for raw_ip in pattern.findall(line_text):
                try:
                    address = ipaddress.ip_address(raw_ip)
                except ValueError:
                    continue
                if address.is_loopback or address.is_unspecified or any(address in network for network in DOC_NETWORKS):
                    continue
                findings.append(Finding("non-documentation-ip", rel, line_no, "non-documentation IP address"))
        if rel.startswith("fixtures/"):
            for match in SYNTHETIC_ID_FIELDS_RE.finditer(line_text):
                value = match.group(1).lower()
                if not any(marker in value for marker in ("synthetic", "example", "generic")):
                    findings.append(Finding("fixture-identifier", rel, line_no, "fixture identifier lacks explicit synthetic marker"))
    if rel.startswith("fixtures/") and rel.endswith(".json"):
        try:
            fixture = json.loads(text)
        except json.JSONDecodeError:
            fixture = None

        def visit(value: object) -> None:
            if isinstance(value, dict):
                for name, item in value.items():
                    if str(name).lower() in {"hostname", "fqdn", "instance", "url", "endpoint", "base_url"} and isinstance(item, str):
                        for hostname in FQDN_RE.findall(item):
                            if not hostname.lower().endswith((".example.com", ".example.net", ".example.org", ".example.invalid")):
                                findings.append(Finding("fixture-fqdn", rel, _line(text, max(text.find(hostname), 0)), "fixture contains non-documentation FQDN"))
                    normalized_name = re.sub(r"[^a-z0-9]", "", str(name).lower())
                    if isinstance(item, str) and any(marker in normalized_name for marker in ("serial", "assettag", "nativeid", "deviceid", "sourceid", "ciidentity")):
                        if not any(marker in item.lower() for marker in ("synthetic", "example", "generic")):
                            findings.append(Finding("fixture-identifier", rel, _line(text, max(text.find(item), 0)), "fixture identity lacks explicit synthetic marker"))
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(fixture)
    findings.extend(structured_credential_findings(text, rel))
    return findings


def scan_paths(paths: Iterable[Path], root: Path = ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        findings.extend(path_findings(path, root))
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            findings.append(Finding("read-error", rel, None, "unable to read file"))
            continue
        if b"\0" in data[:8192]:
            findings.append(Finding("binary-file", rel, None, "binary file requires explicit public-safe review"))
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(Finding("non-utf8", rel, None, "non-UTF-8 file requires explicit public-safe review"))
            continue
        findings.extend(text_findings(text, rel))
    return sorted(set(findings), key=lambda item: (item.path, item.line or 0, item.rule))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Optional repository-relative paths")
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--output", type=Path, help="Write redacted report to this path")
    args = parser.parse_args(argv)
    paths = [ROOT / item for item in args.paths] if args.paths else project_files(ROOT)
    missing = [path for path in paths if not path.exists()]
    if missing:
        print("ERROR: one or more scan paths do not exist", file=sys.stderr)
        return 2
    try:
        entries = load_allowlist(args.allowlist)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    findings = [finding for finding in scan_paths(paths, ROOT) if not allowed(finding, entries)]
    payload = {"status": "fail" if findings else "pass", "files_scanned": len(paths), "violations": [asdict(item) for item in findings]}
    if args.format == "json":
        report = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    elif findings:
        lines = ["Public-repository safety scan failed:"] + [f"- {item.path}:{item.line or '-'} [{item.rule}] {item.message}; value=<redacted>" for item in findings]
        report = "\n".join(lines) + "\n"
    else:
        report = f"Public-repository safety scan passed ({len(paths)} files).\n"
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        stream = sys.stderr if findings and args.format == "human" else sys.stdout
        stream.write(report)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
