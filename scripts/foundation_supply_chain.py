#!/usr/bin/env python3
"""Generate external SBOM/license/vulnerability evidence for pinned images."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "deploy/compose/images.json"
SCANNER = "aquasec/trivy:0.72.0@sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f"
DERIVED_COMPONENTS = {
    "PostgreSQL": "postgres",
    "Apache Kafka": "kafka",
    "Grafana OSS": "grafana",
    "PostgreSQL exporter": "postgres-exporter",
}
IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")


def blocking_counts(report: dict[str, object]) -> tuple[int, int, int]:
    results = report.get("Results")
    if not isinstance(results, list) or not results:
        raise ValueError("scanner report requires nonempty Results")
    critical = 0
    fixable_high = 0
    unfixable_high = 0
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("scanner Results entries must be objects")
        findings = result.get("Vulnerabilities", [])
        if findings is None:
            findings = []
        if not isinstance(findings, list):
            raise ValueError("scanner Vulnerabilities must be an array")
        for finding in findings:
            if not isinstance(finding, dict):
                raise ValueError("scanner vulnerability entries must be objects")
            severity = str(finding.get("Severity", "")).upper()
            if severity == "CRITICAL":
                critical += 1
            elif severity == "HIGH" and str(finding.get("FixedVersion", "")).strip():
                fixable_high += 1
            elif severity == "HIGH":
                unfixable_high += 1
    return critical, fixable_high, unfixable_high


def external_root(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        return resolved
    raise ValueError("DCIM_RUNTIME_ROOT must resolve outside repository")


def safe_name(component: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", component.lower()).strip("-")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_license_report(report: dict[str, object]) -> dict[str, int]:
    results = report.get("Results")
    if not isinstance(results, list) or not results:
        raise ValueError("license report requires nonempty Results")
    licenses: list[dict[str, object]] = []
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("license Results entries must be objects")
        found = result.get("Licenses", [])
        if found is None:
            found = []
        if not isinstance(found, list) or any(not isinstance(item, dict) for item in found):
            raise ValueError("license entries must be objects")
        licenses.extend(found)
    if not licenses:
        # A valid scanner result with no detected license is an explicit unknown,
        # not a silent pass. ADR-0013 keeps it local-only and review-required.
        return {"unknown": 1}
    categories: dict[str, int] = {}
    for license_item in licenses:
        name = license_item.get("Name")
        category = str(license_item.get("Category", "unknown")).lower()
        if not isinstance(name, str) or not name:
            raise ValueError("license entry requires a name")
        categories[category] = categories.get(category, 0) + 1
    return categories


def validate_sbom(report: dict[str, object]) -> int:
    components = report.get("components")
    if report.get("bomFormat") != "CycloneDX" or not isinstance(components, list) or not components:
        raise ValueError("CycloneDX SBOM requires nonempty components")
    return len(components)


def effective_images(inventory: dict[str, object], lock: dict[str, object]) -> list[dict[str, object]]:
    if lock.get("schema_version") != 1 or lock.get("publication") is not False:
        raise ValueError("derived image lock schema/publication policy mismatch")
    try:
        derived = {item["component"]: item["image_id"] for item in lock["images"]}
    except (KeyError, TypeError) as error:
        raise ValueError(f"derived image lock invalid: {error}") from error
    if set(derived) != set(DERIVED_COMPONENTS.values()):
        raise ValueError("derived image lock component allowlist mismatch")
    if any(not isinstance(image, str) or not IMAGE_ID.fullmatch(image) for image in derived.values()):
        raise ValueError("derived image lock contains invalid image ID")
    images: list[dict[str, object]] = []
    for original in inventory["images"]:
        entry = dict(original)
        component = DERIVED_COMPONENTS.get(str(entry["component"]))
        if component:
            entry["image"] = derived[component]
            entry["derived_component"] = component
        images.append(entry)
    return images


def scanner_command(evidence: Path, cache: Path, arguments: list[str]) -> list[str]:
    return [
        "docker", "run", "--rm", "--pull", "missing", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
        "--user", f"{os.getuid()}:{os.getgid()}", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--env", "TMPDIR=/work", "--volume", f"{evidence}:/evidence:rw",
        "--volume", f"{cache}:/cache:rw", "--volume", f"{cache}:/work:rw",
        SCANNER, "--cache-dir", "/cache", *arguments,
    ]


def run_scan(evidence: Path, cache: Path, arguments: list[str]) -> None:
    result = subprocess.run(
        scanner_command(evidence, cache, arguments), cwd=ROOT,
        capture_output=True, text=True, timeout=900, check=False,
    )
    if result.returncode:
        decisive = (result.stderr or result.stdout).strip().splitlines()
        detail = decisive[-1] if decisive else f"exit {result.returncode}"
        raise RuntimeError(f"scanner failed: {detail}")


def database_snapshot(evidence: Path, cache: Path) -> dict[str, object]:
    run_scan(evidence, cache, ["image", "--download-db-only"])
    run_scan(evidence, cache, ["image", "--download-java-db-only"])
    files = {
        "vulnerability_db": cache / "db/trivy.db",
        "vulnerability_metadata": cache / "db/metadata.json",
        "java_db": cache / "java-db/trivy-java.db",
        "java_metadata": cache / "java-db/metadata.json",
    }
    if any(not path.is_file() for path in files.values()):
        raise ValueError("scanner database snapshot incomplete")
    metadata = json.loads(files["vulnerability_metadata"].read_text(encoding="utf-8"))
    java_metadata = json.loads(files["java_metadata"].read_text(encoding="utf-8"))
    return {
        "vulnerability_updated_at": metadata.get("UpdatedAt"),
        "vulnerability_next_update": metadata.get("NextUpdate"),
        "vulnerability_db_sha256": sha256_file(files["vulnerability_db"]),
        "java_updated_at": java_metadata.get("UpdatedAt"),
        "java_next_update": java_metadata.get("NextUpdate"),
        "java_db_sha256": sha256_file(files["java_db"]),
    }


def scan(runtime_root: Path, derived_lock_path: Path) -> tuple[list[dict[str, object]], bool]:
    root = external_root(runtime_root)
    evidence = root / "dev-build/evidence/supply-chain"
    cache = root / "dev-build/cache/trivy"
    evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    evidence.chmod(0o700)
    cache.chmod(0o700)
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    derived_lock = json.loads(derived_lock_path.read_text(encoding="utf-8"))
    if not isinstance(inventory.get("license_review"), str) or "OD-06" not in inventory["license_review"]:
        raise ValueError("explicit OD-06 license review disposition required")
    db_snapshot = database_snapshot(evidence, cache)
    frozen_db_flags = ["--skip-db-update", "--skip-java-db-update"]
    summaries: list[dict[str, object]] = []
    blocked = False
    for entry in effective_images(inventory, derived_lock):
        name = safe_name(entry["component"])
        vulnerability_file = f"{name}-vulnerabilities.json"
        license_file = f"{name}-licenses.json"
        sbom_file = f"{name}-sbom.cdx.json"
        image = entry["image"]
        derived_component = entry.get("derived_component")
        input_arguments: list[str] = []
        if derived_component:
            archive = evidence / f"{name}.tar"
            saved = subprocess.run(
                ["docker", "save", "--output", str(archive), str(image)], cwd=ROOT,
                capture_output=True, text=True, timeout=900, check=False,
            )
            if saved.returncode:
                raise RuntimeError(f"docker save failed for {entry['component']}")
            input_arguments = ["--input", f"/evidence/{archive.name}"]
        else:
            input_arguments = [str(image)]
        run_scan(evidence, cache, [
            "image", *frozen_db_flags, *input_arguments, "--scanners", "vuln",
            "--format", "json", "--output", f"/evidence/{vulnerability_file}",
        ])
        run_scan(evidence, cache, [
            "image", *frozen_db_flags, *input_arguments, "--scanners", "license",
            "--format", "json", "--output", f"/evidence/{license_file}",
        ])
        run_scan(evidence, cache, [
            "image", *frozen_db_flags, *input_arguments, "--format", "cyclonedx",
            "--output", f"/evidence/{sbom_file}",
        ])
        report = json.loads((evidence / vulnerability_file).read_text(encoding="utf-8"))
        critical, fixable_high, unfixable_high = blocking_counts(report)
        license_categories = validate_license_report(
            json.loads((evidence / license_file).read_text(encoding="utf-8"))
        )
        sbom_components = validate_sbom(
            json.loads((evidence / sbom_file).read_text(encoding="utf-8"))
        )
        blocked = blocked or bool(critical or fixable_high or unfixable_high)
        summaries.append(
            {
                "component": entry["component"],
                "image": image,
                "critical": critical,
                "fixable_high": fixable_high,
                "unfixable_high_without_disposition": unfixable_high,
                "license_categories": license_categories,
                "license_review": "ADR-0013 local Development only; publication prohibited; OD-06 open",
                "sbom_components": sbom_components,
                "evidence_sha256": {
                    "vulnerability": sha256_file(evidence / vulnerability_file),
                    "license": sha256_file(evidence / license_file),
                    "sbom": sha256_file(evidence / sbom_file),
                },
                "result": "fail" if critical or fixable_high or unfixable_high else "pass",
            }
        )
    summary = {
        "schema_version": 1,
        "scanner": SCANNER,
        "scanner_database": db_snapshot,
        "verified_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "target_platform": inventory["target_platform"],
        "images": summaries,
        "result": "fail" if blocked else "pass",
    }
    summary_path = evidence / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path.chmod(0o600)
    return summaries, blocked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--derived-lock", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        summaries, blocked = scan(arguments.runtime_root, arguments.derived_lock)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"foundation-supply-chain: {error}", file=sys.stderr)
        return 2
    for item in summaries:
        print(
            f"{item['component']}: {item['result']} "
            f"(critical={item['critical']}, fixable_high={item['fixable_high']}, "
            f"unfixable_high_without_disposition={item['unfixable_high_without_disposition']})"
        )
    print(f"foundation-supply-chain: {'NO-GO' if blocked else 'PASS'}")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
