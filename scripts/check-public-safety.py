#!/usr/bin/env python3
"""Fail when public-repository files contain high-confidence sensitive material."""
from __future__ import annotations

import argparse
import ipaddress
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules", "dist", "build"}
FORBIDDEN_DIRS = {"secrets", "private", "credentials", "inventory", "inventories", "source-inventory", "captures", "packet-captures", "dumps", "backups", "exports", "recordings", "runtime", "state", "data", "volumes"}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".crt", ".cer", ".csr", ".pcap", ".pcapng", ".har", ".dump", ".sqlite", ".sqlite3", ".db", ".zip"}
FORBIDDEN_NAMES = {".env", "id_rsa", "id_ed25519"}

DOC_NETWORKS = tuple(ipaddress.ip_network(value) for value in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24"))
IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
CREDENTIAL_RE = re.compile(r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key|community(?:[_-]?string)?)\b\s*[:=]\s*([^\s#]+)")
URL_CREDENTIAL_RE = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|redis|mongodb(?:\+srv)?)://[^\s/:]+:[^\s/@]+@")
HIGH_CONFIDENCE_PATTERNS = (
    ("private key material", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
)
PLACEHOLDER_TOKENS = {
    "", "none", "null", "unset", "not-set", "not_set", "redacted", "masked",
    "example", "dummy", "synthetic", "changeme", "change-me", "change_me",
    "replace-me", "replace_me", "set-locally", "set_locally"
}


def repository_files(root: Path = ROOT) -> list[Path]:
    """Return tracked files when possible; otherwise walk the source tree."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
        )
        paths = [root / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]
        if paths:
            return sorted(path for path in paths if path.is_file())
    except (FileNotFoundError, subprocess.CalledProcessError, UnicodeDecodeError):
        pass

    paths: list[Path] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for name in names:
            path = Path(current) / name
            if path.is_file():
                paths.append(path)
    return sorted(paths)


def is_placeholder(value: str) -> bool:
    cleaned = value.strip().strip("'\"").rstrip(",;")
    lowered = cleaned.lower()
    if lowered in PLACEHOLDER_TOKENS:
        return True
    if cleaned.startswith("<") and cleaned.endswith(">"):
        return True
    if cleaned.startswith("${") or cleaned.startswith("$"):
        return True
    if "{{" in cleaned or "}}" in cleaned:
        return True
    return any(token in lowered for token in ("replace", "redact", "synthetic", "example", "set_locally", "set-locally"))


def path_findings(path: Path, root: Path = ROOT) -> list[str]:
    rel = path.relative_to(root)
    findings: list[str] = []
    parts = set(rel.parts[:-1])
    if parts & FORBIDDEN_DIRS:
        findings.append(f"forbidden directory: {rel}")
    if path.name in FORBIDDEN_NAMES and path.name != ".env.example":
        findings.append(f"forbidden filename: {rel}")
    if path.name.startswith(".env.") and path.name != ".env.example":
        findings.append(f"environment file must stay outside Git: {rel}")
    lowered_name = path.name.lower()
    if any(lowered_name.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
        findings.append(f"forbidden sensitive/binary extension: {rel}")
    if lowered_name.endswith((".sql.gz", ".tar.gz")):
        findings.append(f"forbidden archive/dump extension: {rel}")
    return findings


def text_findings(text: str, rel: Path) -> list[str]:
    findings: list[str] = []
    for label, pattern in HIGH_CONFIDENCE_PATTERNS:
        match = pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            findings.append(f"{rel}:{line}: {label}")

    match = URL_CREDENTIAL_RE.search(text)
    if match:
        line = text.count("\n", 0, match.start()) + 1
        findings.append(f"{rel}:{line}: credential embedded in connection URL")

    for line_no, line_text in enumerate(text.splitlines(), start=1):
        credential = CREDENTIAL_RE.search(line_text)
        if credential and not is_placeholder(credential.group(2)):
            findings.append(f"{rel}:{line_no}: possible non-placeholder {credential.group(1)} assignment")

        for raw_ip in IPV4_RE.findall(line_text):
            try:
                address = ipaddress.ip_address(raw_ip)
            except ValueError:
                continue
            if address.is_loopback or address.is_unspecified:
                continue
            if any(address in network for network in DOC_NETWORKS):
                continue
            findings.append(f"{rel}:{line_no}: non-documentation IP address {raw_ip}")
    return findings


def scan_paths(paths: Iterable[Path], root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    for path in paths:
        findings.extend(path_findings(path, root))
        try:
            data = path.read_bytes()
        except OSError as exc:
            findings.append(f"{path}: unable to read: {exc}")
            continue
        if b"\x00" in data[:8192]:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(text_findings(text, path.relative_to(root)))
    return sorted(set(findings))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Optional repository-relative paths to scan")
    args = parser.parse_args(argv)

    paths = [ROOT / item for item in args.paths] if args.paths else repository_files(ROOT)
    missing = [path for path in paths if not path.exists()]
    if missing:
        for path in missing:
            print(f"ERROR: path does not exist: {path}", file=sys.stderr)
        return 2

    findings = scan_paths(paths, ROOT)
    if findings:
        print("Public-repository safety scan failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        print("Remove the material; do not add an ignore for a real secret or live data.", file=sys.stderr)
        return 1

    print(f"Public-repository safety scan passed ({len(paths)} files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
