from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.foundation_images import runtime_environment


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/foundation_images.py"
MANIFEST = ROOT / "deploy/compose/derived-images/recipes.json"
LICENSE_DISPOSITIONS = ROOT / "deploy/compose/derived-images/license-dispositions.json"


def locked_image(name: str) -> dict[str, str]:
    return {
        "image": f"{name}:1.0@sha256:" + "a" * 64,
        "amd64_manifest": "sha256:" + "b" * 64,
    }


def recipe(component: str) -> dict[str, object]:
    return {
        "component": component,
        "source": {
            "repository": f"https://github.com/example/{component}",
            "tag": "v1.0.0",
            "commit": "c" * 40,
            "archive_sha256": "d" * 64,
        },
        "inputs": [{
            "filename": "source.tar.gz",
            "url": f"https://github.com/example/{component}/archive/refs/tags/v1.0.0.tar.gz",
            "sha256": "d" * 64,
            "context": True,
        }],
        "base_images": [locked_image("example/base")],
        "build_tools": [locked_image("example/builder")],
        "dockerfile": f"{component}/Dockerfile",
        "output_repository": f"dcim-development/{component}",
        "output_tag": "1.0.0-r1",
        "source_date_epoch": 1_700_000_000,
        "patches": [{
            "finding": "CVE-2099-0001",
            "artifact": "example-package",
            "from_version": "1.0.0",
            "to_version": "1.0.1",
            "sha256": "e" * 64,
        }],
        "publish": False,
    }


def manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "target_platform": "linux/amd64",
        "publication": False,
        "scanner": locked_image("aquasec/trivy"),
        "recipes": [
            recipe("postgres"),
            recipe("kafka"),
            recipe("grafana"),
            recipe("postgres-exporter"),
        ],
    }


def license_dispositions(recipes_sha256: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "recipes_sha256": recipes_sha256,
        "decision": {
            "owner": "synthetic-owner",
            "date": "2026-07-20",
            "issue": "#10",
            "scope": "synthetic dcim-build local Development only",
            "publication": False,
            "distribution": False,
            "od_06": "OPEN",
        },
        "dispositions": [
            {
                "component": component,
                "category": "unknown",
                "reviewed_count": 1,
                "inventory_sha256": "a" * 64,
                "disposition": "accepted-local-development-only",
            }
            for component in (
                "postgresql", "apache-kafka", "grafana-oss", "postgresql-exporter",
                "prometheus", "jmx-exporter-java-runtime",
            )
        ],
        "revalidation_triggers": [
            "license-inventory-change",
            "recipe-change",
            "publication-or-distribution-request",
            "od-06-status-change",
            "staging-production-or-handover-request",
        ],
    }


class FoundationImagesTests(unittest.TestCase):
    def test_runtime_environment_uses_only_immutable_local_image_ids(self) -> None:
        image_id = "sha256:" + "f" * 64
        environment = runtime_environment([
            {"component": component, "image_id": image_id}
            for component in ("postgres", "kafka", "grafana", "postgres-exporter")
        ])
        self.assertEqual(
            {
                "DCIM_POSTGRES_IMAGE": image_id,
                "DCIM_KAFKA_IMAGE": image_id,
                "DCIM_GRAFANA_IMAGE": image_id,
                "DCIM_POSTGRES_EXPORTER_IMAGE": image_id,
            },
            environment,
        )
    def test_complete_locked_manifest_passes_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "recipes.json"
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            dispositions_path = root / "license-dispositions.json"
            recipes_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            dispositions_path.write_text(
                json.dumps(license_dispositions(recipes_sha256)), encoding="utf-8",
            )
            result = subprocess.run(
                [
                    "python3", str(SCRIPT), "--manifest", str(manifest_path),
                    "--license-dispositions", str(dispositions_path),
                    "--runtime-root", "/var/empty/dcim-foundation-test", "--validate-only",
                ],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("foundation-images: manifest PASS", result.stdout)

    def test_repository_manifest_passes_validation(self) -> None:
        result = subprocess.run(
            [
                "python3", str(SCRIPT), "--manifest", str(MANIFEST),
                "--license-dispositions", str(LICENSE_DISPOSITIONS),
                "--runtime-root", "/var/empty/dcim-foundation-test", "--validate-only",
            ],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("foundation-images: manifest PASS", result.stdout)

    def test_recipe_change_requires_new_license_disposition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "recipes.json"
            changed_manifest = manifest()
            changed_manifest["recipes"][0]["output_tag"] = "1.0.0-r2"
            manifest_path.write_text(json.dumps(changed_manifest), encoding="utf-8")
            dispositions_path = root / "license-dispositions.json"
            dispositions_path.write_text(
                json.dumps(license_dispositions("a" * 64)), encoding="utf-8",
            )
            result = subprocess.run(
                [
                    "python3", str(SCRIPT), "--manifest", str(manifest_path),
                    "--license-dispositions", str(dispositions_path),
                    "--runtime-root", "/var/empty/dcim-foundation-test", "--validate-only",
                ],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("recipe digest mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
