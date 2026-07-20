#!/usr/bin/env python3
"""Validate and qualify Development-only derived foundation images."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
from urllib.parse import urlsplit

try:
    from scripts.foundation_supply_chain import (
        blocking_counts,
        license_category_fingerprints,
        review_license_categories,
        validate_license_disposition_manifest,
        validate_license_report,
        validate_sbom,
    )
    from scripts.strict_json import load_object, loads_object
except ModuleNotFoundError:  # Direct script execution adds scripts/, not repository root.
    from foundation_supply_chain import (
        blocking_counts,
        license_category_fingerprints,
        review_license_categories,
        validate_license_disposition_manifest,
        validate_license_report,
        validate_sbom,
    )
    from strict_json import load_object, loads_object


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COMPONENTS = {"postgres", "kafka", "grafana", "postgres-exporter"}
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
IMAGE = re.compile(r"[^\s:@]+(?:/[^\s:@]+)*:[^\s@]+@sha256:[0-9a-f]{64}\Z")
CVE = re.compile(r"CVE-[0-9]{4}-[0-9]{4,}\Z")
GHSA = re.compile(r"GHSA-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}\Z")
IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")
ENVIRONMENT_KEYS = {
    "postgres": "DCIM_POSTGRES_IMAGE",
    "kafka": "DCIM_KAFKA_IMAGE",
    "grafana": "DCIM_GRAFANA_IMAGE",
    "postgres-exporter": "DCIM_POSTGRES_EXPORTER_IMAGE",
}
LICENSE_COMPONENTS = {
    "postgres": "postgresql",
    "kafka": "apache-kafka",
    "grafana": "grafana-oss",
    "postgres-exporter": "postgresql-exporter",
}


def external_root(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        return resolved
    raise ValueError("runtime root must resolve outside repository")


def validate_locked_image(value: object, field: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{field}: locked image must be an object")
        return
    image = value.get("image")
    manifest = value.get("amd64_manifest")
    if not isinstance(image, str) or not IMAGE.fullmatch(image):
        errors.append(f"{field}: exact image tag and immutable digest required")
    if not isinstance(manifest, str) or not DIGEST.fullmatch(manifest):
        errors.append(f"{field}: linux/amd64 manifest digest required")


def public_https(value: object) -> bool:
    parsed = urlsplit(value) if isinstance(value, str) else None
    return bool(
        parsed is not None and parsed.scheme == "https" and parsed.hostname
        and not parsed.username and not parsed.password
        and not parsed.query and not parsed.fragment
    )


def validate_manifest(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["manifest must be an object"]
    if value.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if value.get("target_platform") != "linux/amd64":
        errors.append("target_platform must be linux/amd64")

    if value.get("publication") is not False:
        errors.append("publication must be disabled")
    validate_locked_image(value.get("scanner"), "scanner", errors)

    recipes = value.get("recipes")
    if not isinstance(recipes, list):
        return errors + ["recipes must be an array"]
    components = [item.get("component") for item in recipes if isinstance(item, dict)]
    if len(components) != len(recipes) or set(components) != REQUIRED_COMPONENTS or len(components) != len(set(components)):
        errors.append("recipes must contain exactly postgres, kafka, grafana, and postgres-exporter")

    for index, recipe in enumerate(recipes):
        field = f"recipes[{index}]"
        if not isinstance(recipe, dict):
            errors.append(f"{field}: recipe must be an object")
            continue
        component = recipe.get("component")
        source = recipe.get("source")
        if not isinstance(source, dict):
            errors.append(f"{field}.source: source must be an object")
        else:
            repository = source.get("repository")
            if not public_https(repository):
                errors.append(f"{field}.source: public HTTPS repository required")
            tag = source.get("tag")
            if not isinstance(tag, str) or not tag or tag.lower() == "latest":
                errors.append(f"{field}.source: immutable release tag required")
            if not isinstance(source.get("commit"), str) or not COMMIT.fullmatch(source["commit"]):
                errors.append(f"{field}.source: 40-character commit required")
            if not isinstance(source.get("archive_sha256"), str) or not SHA256.fullmatch(source["archive_sha256"]):
                errors.append(f"{field}.source: archive SHA-256 required")

        inputs = recipe.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            errors.append(f"{field}.inputs: nonempty locked input list required")
        else:
            filenames: set[str] = set()
            for input_index, item in enumerate(inputs):
                input_field = f"{field}.inputs[{input_index}]"
                if not isinstance(item, dict):
                    errors.append(f"{input_field}: input must be an object")
                    continue
                filename = item.get("filename")
                if (
                    not isinstance(filename, str) or not filename
                    or Path(filename).name != filename or filename in filenames
                ):
                    errors.append(f"{input_field}: unique plain filename required")
                else:
                    filenames.add(filename)
                if not public_https(item.get("url")):
                    errors.append(f"{input_field}: public HTTPS URL required")
                if not isinstance(item.get("sha256"), str) or not SHA256.fullmatch(item["sha256"]):
                    errors.append(f"{input_field}: SHA-256 required")
                if item.get("context") not in (True, False):
                    errors.append(f"{input_field}: explicit context boolean required")

        for collection in ("base_images", "build_tools"):
            images = recipe.get(collection)
            if not isinstance(images, list) or not images:
                errors.append(f"{field}.{collection}: nonempty locked image list required")
            else:
                for image_index, image in enumerate(images):
                    validate_locked_image(image, f"{field}.{collection}[{image_index}]", errors)

        dockerfile = recipe.get("dockerfile")
        expected_prefix = f"{component}/" if isinstance(component, str) else ""
        if (
            not isinstance(dockerfile, str) or not dockerfile.startswith(expected_prefix)
            or Path(dockerfile).is_absolute() or ".." in Path(dockerfile).parts
        ):
            errors.append(f"{field}: component-local Dockerfile required")
        repository = recipe.get("output_repository")
        if not isinstance(repository, str) or not repository.startswith("dcim-development/"):
            errors.append(f"{field}: local derivative output namespace required")
        output_tag = recipe.get("output_tag")
        if not isinstance(output_tag, str) or not output_tag or output_tag.lower() == "latest":
            errors.append(f"{field}: immutable output tag required")
        epoch = recipe.get("source_date_epoch")
        if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch <= 0:
            errors.append(f"{field}: deterministic source_date_epoch required")
        if recipe.get("publish") is not False:
            errors.append(f"{field}: publication must be disabled")

        patches = recipe.get("patches")
        if not isinstance(patches, list) or not patches:
            errors.append(f"{field}.patches: nonempty remediation allowlist required")
        else:
            for patch_index, patch in enumerate(patches):
                patch_field = f"{field}.patches[{patch_index}]"
                if not isinstance(patch, dict):
                    errors.append(f"{patch_field}: patch must be an object")
                    continue
                finding = patch.get("finding")
                if not isinstance(finding, str) or not (CVE.fullmatch(finding) or GHSA.fullmatch(finding)):
                    errors.append(f"{patch_field}: public CVE or GHSA identifier required")
                for name in ("artifact", "from_version", "to_version"):
                    if not isinstance(patch.get(name), str) or not patch[name]:
                        errors.append(f"{patch_field}: {name} required")
                if not isinstance(patch.get("sha256"), str) or not SHA256.fullmatch(patch["sha256"]):
                    errors.append(f"{patch_field}: patch SHA-256 required")
    return errors


def runtime_environment(records: list[dict[str, object]]) -> dict[str, str]:
    environment: dict[str, str] = {}
    for record in records:
        component = record.get("component")
        image_id = record.get("image_id")
        if component not in ENVIRONMENT_KEYS or not isinstance(image_id, str) or not IMAGE_ID.fullmatch(image_id):
            raise ValueError("complete immutable derived image records required")
        environment[ENVIRONMENT_KEYS[component]] = image_id
    if set(environment) != set(ENVIRONMENT_KEYS.values()):
        raise ValueError("complete immutable derived image records required")
    return environment


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], *, timeout: int = 1800) -> str:
    result = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True,
        timeout=timeout, check=False,
    )
    if result.returncode:
        lines = (result.stderr or result.stdout).strip().splitlines()
        detail = lines[-1] if lines else f"exit {result.returncode}"
        raise RuntimeError(f"{' '.join(command[:3])}: {detail}")
    return result.stdout.strip()


def download_input(item: dict[str, object], input_root: Path) -> Path:
    filename = str(item["filename"])
    destination = input_root / filename
    expected = str(item["sha256"])
    if destination.is_file() and sha256_file(destination) == expected:
        return destination
    temporary = input_root / f".{filename}.part"
    request = urllib.request.Request(str(item["url"]), headers={"User-Agent": "dcim-foundation-images/1"})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output)
    if sha256_file(temporary) != expected:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"input checksum mismatch: {filename}")
    temporary.replace(destination)
    return destination


def prepare_context(
    recipe: dict[str, object], input_root: Path, context_root: Path,
) -> Path:
    component = str(recipe["component"])
    context = context_root / component
    context.mkdir(parents=True, exist_ok=True, mode=0o700)
    dockerfile = ROOT / "deploy/compose/derived-images" / str(recipe["dockerfile"])
    shutil.copyfile(dockerfile, context / "Dockerfile")
    for item in recipe["inputs"]:
        source = download_input(item, input_root)
        if item["context"]:
            shutil.copyfile(source, context / str(item["filename"]))
    return context


def inspect_image(image: str) -> tuple[str, dict[str, str]]:
    raw = run(["docker", "image", "inspect", image, "--format", "{{json .}}"])
    inspected = loads_object(raw, "docker image inspection")
    image_id = inspected.get("Id")
    labels = inspected.get("Config", {}).get("Labels", {}) or {}
    if not isinstance(image_id, str) or not IMAGE_ID.fullmatch(image_id):
        raise ValueError(f"invalid local image ID: {image}")
    if not isinstance(labels, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in labels.items()):
        raise ValueError(f"invalid OCI labels: {image}")
    return image_id, labels


def build_once(recipe: dict[str, object], context: Path, suffix: str, clean: bool) -> tuple[str, dict[str, str]]:
    tag = f"{recipe['output_repository']}:{recipe['output_tag']}-{suffix}"
    output_root = context.parent.parent / "outputs"
    output_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    archive = output_root / f"{recipe['component']}-{suffix}.oci.tar"
    command = [
        "docker", "buildx", "build", "--output",
        f"type=oci,dest={archive},rewrite-timestamp=true",
        "--platform", "linux/amd64",
        "--provenance=false", "--build-arg", f"SOURCE_DATE_EPOCH={recipe['source_date_epoch']}",
        "--tag", tag,
    ]
    if clean:
        command.append("--no-cache")
    command.append(str(context))
    run(command, timeout=3600)
    run(["docker", "load", "--input", str(archive)], timeout=900)
    return inspect_image(tag)


def scanner_command(
    scanner: str, evidence: Path, cache: Path, arguments: list[str],
) -> list[str]:
    return [
        "docker", "run", "--rm", "--pull", "missing", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m", "--env", "TMPDIR=/work",
        "--volume", f"{evidence}:/evidence:rw", "--volume", f"{cache}:/cache:rw",
        "--volume", f"{cache}:/work:rw", scanner, "--cache-dir", "/cache", *arguments,
    ]


def scan_image(
    component: str,
    image: str,
    scanner: str,
    evidence: Path,
    cache: Path,
    license_dispositions: dict[str, object],
) -> tuple[dict[str, int], dict[str, object]]:
    archive = evidence / f"{component}.tar"
    run(["docker", "save", "--output", str(archive), image], timeout=900)
    vulnerability = f"{component}-vulnerabilities.json"
    license_report = f"{component}-licenses.json"
    sbom = f"{component}-sbom.cdx.json"
    run(scanner_command(scanner, evidence, cache, [
        "image", "--input", f"/evidence/{archive.name}", "--scanners", "vuln",
        "--format", "json", "--output", f"/evidence/{vulnerability}",
    ]), timeout=900)
    run(scanner_command(scanner, evidence, cache, [
        "image", "--input", f"/evidence/{archive.name}", "--scanners", "license",
        "--format", "json", "--output", f"/evidence/{license_report}",
    ]), timeout=900)
    run(scanner_command(scanner, evidence, cache, [
        "image", "--input", f"/evidence/{archive.name}", "--format", "cyclonedx",
        "--output", f"/evidence/{sbom}",
    ]), timeout=900)
    report = load_object(evidence / vulnerability)
    critical, fixable_high, unfixable_high = blocking_counts(report)
    counts = {
        "critical": critical,
        "fixable_high": fixable_high,
        "unfixable_high_without_disposition": unfixable_high,
    }
    license_data = load_object(evidence / license_report)
    license_categories = validate_license_report(license_data)
    reviewed_license_categories = review_license_categories(
        license_dispositions, LICENSE_COMPONENTS[component], license_categories,
        license_category_fingerprints(license_data),
    )
    sbom_components = validate_sbom(
        load_object(evidence / sbom)
    )
    metadata = {
        "license_categories": license_categories,
        "license_disposition": reviewed_license_categories,
        "license_review": "Issue #10 owner disposition; local synthetic Development only; publication/distribution prohibited; OD-06 OPEN",
        "sbom_components": sbom_components,
        "sha256": {
            "vulnerability": sha256_file(evidence / vulnerability),
            "license": sha256_file(evidence / license_report),
            "sbom": sha256_file(evidence / sbom),
        },
    }
    return counts, metadata


def qualify(
    manifest: dict[str, object],
    runtime_root: Path,
    license_dispositions: dict[str, object],
) -> list[dict[str, object]]:
    root = external_root(runtime_root) / "dev-build"
    input_root = root / "derived-images/inputs"
    context_root = root / "derived-images/contexts"
    evidence = root / "evidence/derived-images"
    cache = root / "cache/trivy"
    for path in (input_root, context_root, evidence, cache):
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.chmod(0o700)
    scanner = str(manifest["scanner"]["image"])
    records: list[dict[str, object]] = []
    for recipe in manifest["recipes"]:
        component = str(recipe["component"])
        print(f"foundation-images: qualifying {component}", flush=True)
        context = prepare_context(recipe, input_root, context_root)
        first_id, first_labels = build_once(recipe, context, "verify-a", clean=False)
        second_id, second_labels = build_once(recipe, context, "verify-b", clean=True)
        if first_id != second_id:
            raise RuntimeError(f"{component}: reproducibility mismatch {first_id} != {second_id}")
        if first_labels != second_labels:
            raise RuntimeError(f"{component}: OCI label reproducibility mismatch")
        expected_revision = recipe["source"]["commit"]
        required_labels = {
            "io.dcim.derivative": "true",
            "org.opencontainers.image.revision": expected_revision,
        }
        for key, expected in required_labels.items():
            if first_labels.get(key) != expected:
                raise RuntimeError(f"{component}: required OCI label mismatch: {key}")
        final_tag = f"{recipe['output_repository']}:{recipe['output_tag']}"
        run(["docker", "image", "tag", second_id, final_tag])
        counts, evidence_metadata = scan_image(
            component, final_tag, scanner, evidence, cache, license_dispositions,
        )
        if any(counts.values()):
            raise RuntimeError(f"{component}: vulnerability gate failed: {counts}")
        records.append({
            "component": component,
            "image_id": second_id,
            "local_tag": final_tag,
            "source": recipe["source"],
            "build_inputs": {
                "base_images": recipe["base_images"],
                "build_tools": recipe["build_tools"],
            },
            "reproducibility": {
                "first_image_id": first_id,
                "second_image_id": second_id,
                "clean_second_build": True,
                "oci_timestamp_rewrite": True,
            },
            "counts": counts,
            "evidence": evidence_metadata,
        })
    return records


def write_lock(
    records: list[dict[str, object]],
    manifest_path: Path,
    license_dispositions_path: Path,
    runtime_root: Path,
) -> None:
    root = external_root(runtime_root) / "dev-build"
    environment = runtime_environment(records)
    environment_path = root / "images.env"
    environment_path.write_text(
        "".join(f"{key}={value}\n" for key, value in sorted(environment.items())),
        encoding="utf-8",
    )
    environment_path.chmod(0o600)
    lock = {
        "schema_version": 2,
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "manifest_sha256": sha256_file(manifest_path),
        "license_dispositions_sha256": sha256_file(license_dispositions_path),
        "publication": False,
        "images": records,
    }
    lock_path = root / "derived-images-lock.json"
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lock_path.chmod(0o600)


def reusable_records(
    manifest_path: Path,
    license_dispositions_path: Path,
    license_dispositions: dict[str, object],
    runtime_root: Path,
) -> list[dict[str, object]] | None:
    root = external_root(runtime_root) / "dev-build"
    lock_path = root / "derived-images-lock.json"
    environment_path = root / "images.env"
    if not lock_path.is_file() or not environment_path.is_file():
        return None
    try:
        lock = load_object(lock_path)
        records = lock["images"]
        manifest = load_object(manifest_path)
        recipes = {str(recipe["component"]): recipe for recipe in manifest["recipes"]}
        lock_upgraded = False
        if (
            lock.get("schema_version") not in (1, 2) or lock.get("publication") is not False
            or lock.get("manifest_sha256") != sha256_file(manifest_path)
            or not isinstance(records, list)
        ):
            return None
        if lock.get("schema_version") == 1:
            lock_upgraded = True
        elif lock.get("license_dispositions_sha256") != sha256_file(license_dispositions_path):
            # Rebind only after every stored report is validated against the new
            # exact component/category count and canonical inventory fingerprint.
            lock_upgraded = True
        expected_environment = runtime_environment(records)
        actual_environment = dict(
            line.split("=", 1) for line in environment_path.read_text(encoding="utf-8").splitlines()
            if line
        )
        if actual_environment != expected_environment:
            return None
        for record in records:
            image_id, labels = inspect_image(str(record["image_id"]))
            if image_id != record["image_id"] or labels.get("io.dcim.derivative") != "true":
                return None
            component = str(record["component"])
            recipe = recipes.get(component)
            if recipe is None:
                return None
            reproducibility = record.get("reproducibility")
            if not isinstance(reproducibility, dict):
                tag_prefix = f"{recipe['output_repository']}:{recipe['output_tag']}"
                first_id, first_labels = inspect_image(f"{tag_prefix}-verify-a")
                second_id, second_labels = inspect_image(f"{tag_prefix}-verify-b")
                if first_id != image_id or second_id != image_id or first_labels != second_labels:
                    return None
                record["build_inputs"] = {
                    "base_images": recipe["base_images"],
                    "build_tools": recipe["build_tools"],
                }
                record["reproducibility"] = {
                    "first_image_id": first_id,
                    "second_image_id": second_id,
                    "clean_second_build": True,
                    "oci_timestamp_rewrite": True,
                }
                reproducibility = record["reproducibility"]
                lock_upgraded = True
            if (
                not isinstance(reproducibility, dict)
                or reproducibility.get("first_image_id") != image_id
                or reproducibility.get("second_image_id") != image_id
                or reproducibility.get("clean_second_build") is not True
                or reproducibility.get("oci_timestamp_rewrite") is not True
            ):
                return None
            counts = record.get("counts")
            if not isinstance(counts, dict) or any(counts.values()):
                return None
            report_paths = {
                "vulnerability": root / "evidence/derived-images" / f"{component}-vulnerabilities.json",
                "license": root / "evidence/derived-images" / f"{component}-licenses.json",
                "sbom": root / "evidence/derived-images" / f"{component}-sbom.cdx.json",
            }
            for suffix in ("vulnerabilities.json", "licenses.json", "sbom.cdx.json"):
                if not (root / "evidence/derived-images" / f"{component}-{suffix}").is_file():
                    return None
            actual_critical, actual_fixable, actual_unfixable = blocking_counts(
                load_object(report_paths["vulnerability"])
            )
            if counts != {
                "critical": actual_critical,
                "fixable_high": actual_fixable,
                "unfixable_high_without_disposition": actual_unfixable,
            }:
                return None
            license_data = load_object(report_paths["license"])
            actual_license_categories = validate_license_report(license_data)
            reviewed_license_categories = review_license_categories(
                license_dispositions, LICENSE_COMPONENTS[component], actual_license_categories,
                license_category_fingerprints(license_data),
            )
            actual_sbom_components = validate_sbom(
                load_object(report_paths["sbom"])
            )
            evidence_metadata = record.get("evidence")
            if not isinstance(evidence_metadata, dict):
                evidence_metadata = {
                    "license_categories": actual_license_categories,
                    "license_disposition": reviewed_license_categories,
                    "license_review": "Issue #10 owner disposition; local synthetic Development only; publication/distribution prohibited; OD-06 OPEN",
                    "sbom_components": actual_sbom_components,
                    "sha256": {name: sha256_file(path) for name, path in report_paths.items()},
                }
                record["evidence"] = evidence_metadata
                lock_upgraded = True
            elif evidence_metadata.get("license_disposition") is None:
                evidence_metadata["license_disposition"] = reviewed_license_categories
                evidence_metadata["license_review"] = "Issue #10 owner disposition; local synthetic Development only; publication/distribution prohibited; OD-06 OPEN"
                lock_upgraded = True
            expected_hashes = evidence_metadata.get("sha256")
            if (
                not isinstance(expected_hashes, dict)
                or evidence_metadata.get("license_categories") != actual_license_categories
                or evidence_metadata.get("license_disposition") != reviewed_license_categories
                or evidence_metadata.get("sbom_components") != actual_sbom_components
                or expected_hashes != {name: sha256_file(path) for name, path in report_paths.items()}
            ):
                return None
        if lock_upgraded:
            write_lock(records, manifest_path, license_dispositions_path, runtime_root)
        return records
    except (OSError, KeyError, TypeError, ValueError, RuntimeError, json.JSONDecodeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--license-dispositions", required=True, type=Path)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    arguments = parser.parse_args()
    try:
        external_root(arguments.runtime_root)
        manifest = load_object(arguments.manifest)
        license_dispositions = load_object(arguments.license_dispositions)
        validate_license_disposition_manifest(
            license_dispositions, sha256_file(arguments.manifest),
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"foundation-images: invalid input: {error}", file=sys.stderr)
        return 2
    errors = validate_manifest(manifest)
    if errors:
        for error in errors:
            print(f"foundation-images: {error}", file=sys.stderr)
        return 1
    if arguments.validate_only:
        print("foundation-images: manifest PASS")
        return 0
    try:
        records = None if arguments.force else reusable_records(
            arguments.manifest,
            arguments.license_dispositions,
            license_dispositions,
            arguments.runtime_root,
        )
        if records is None:
            records = qualify(manifest, arguments.runtime_root, license_dispositions)
            write_lock(
                records, arguments.manifest, arguments.license_dispositions,
                arguments.runtime_root,
            )
        else:
            print("foundation-images: reusing qualified immutable image lock")
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"foundation-images: qualification failed: {error}", file=sys.stderr)
        return 1
    print("foundation-images: qualification PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
