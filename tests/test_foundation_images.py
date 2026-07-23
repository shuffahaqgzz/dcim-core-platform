from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.foundation_images import build_once, runtime_environment


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
            recipe("prometheus"),
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
    def test_prometheus_recipe_remediates_fixable_grpc_high(self) -> None:
        repository_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        prometheus = next(
            item for item in repository_manifest["recipes"]
            if item["component"] == "prometheus"
        )
        source_sha256 = (
            "322276709c16cb3c22a4d01d244beb91f0380a257699358d2a20ac7086d7256c"
        )
        grpc_sha256 = (
            "50947ea17daeccbfcc031e7d7b93dd3293da79ed0573352d8ea3d324c8326582"
        )
        ui_sha256 = (
            "2194bfbb5d36457df2b8f480037ce89786ee32f03b5ee6ad5597989f14deafb0"
        )
        self.assertEqual("3.13.1-r2", prometheus["output_tag"])
        self.assertEqual(source_sha256, prometheus["source"]["archive_sha256"])
        self.assertIn(
            {
                "filename": "prometheus-web-ui-3.13.1.tar.gz",
                "url": (
                    "https://github.com/prometheus/prometheus/releases/download/"
                    "v3.13.1/prometheus-web-ui-3.13.1.tar.gz"
                ),
                "sha256": ui_sha256,
                "context": True,
            },
            prometheus["inputs"],
        )
        self.assertIn(
            {
                "filename": "grpc-go-ebd8f06.tar.gz",
                "url": (
                    "https://codeload.github.com/grpc/grpc-go/tar.gz/"
                    "ebd8f06a09426fbece97157c95c3917abff28f4e"
                ),
                "sha256": grpc_sha256,
                "context": True,
            },
            prometheus["inputs"],
        )
        self.assertIn(
            {
                "finding": "GHSA-hrxh-6v49-42gf",
                "artifact": "google.golang.org/grpc",
                "from_version": "1.81.1",
                "to_version": "1.82.1",
                "sha256": grpc_sha256,
            },
            prometheus["patches"],
        )
        dockerfile = (MANIFEST.parent / prometheus["dockerfile"]).read_text(
            encoding="utf-8",
        )
        self.assertIn("ARG PROMETHEUS_ARCHIVE=\"prometheus-73ff57c.tar.gz\"", dockerfile)
        self.assertIn(
            "replace google.golang.org/grpc => /src/grpc-go",
            dockerfile,
        )
        self.assertIn("go mod vendor", dockerfile)
        self.assertIn(
            "go mod edit -dropreplace=google.golang.org/grpc",
            dockerfile,
        )
        self.assertIn("go list -mod=vendor -m google.golang.org/grpc", dockerfile)
        self.assertEqual(2, dockerfile.count("go build -mod=vendor"))
        self.assertIn('io.dcim.remediation.grpc-go="1.82.1"', dockerfile)

    def test_grafana_recipe_remediates_fixable_grpc_high(self) -> None:
        repository_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        grafana = next(
            item for item in repository_manifest["recipes"]
            if item["component"] == "grafana"
        )
        expected_sha256 = (
            "50947ea17daeccbfcc031e7d7b93dd3293da79ed0573352d8ea3d324c8326582"
        )
        self.assertEqual("13.1.0-r3", grafana["output_tag"])
        self.assertIn(
            {
                "filename": "grpc-go-ebd8f06.tar.gz",
                "url": (
                    "https://codeload.github.com/grpc/grpc-go/tar.gz/"
                    "ebd8f06a09426fbece97157c95c3917abff28f4e"
                ),
                "sha256": expected_sha256,
                "context": True,
            },
            grafana["inputs"],
        )
        self.assertIn(
            {
                "finding": "GHSA-hrxh-6v49-42gf",
                "artifact": "google.golang.org/grpc",
                "from_version": "1.81.1",
                "to_version": "1.82.1",
                "sha256": expected_sha256,
            },
            grafana["patches"],
        )
        dockerfile = (MANIFEST.parent / grafana["dockerfile"]).read_text(
            encoding="utf-8",
        )
        self.assertIn("ARG GRPC_ARCHIVE=\"grpc-go-ebd8f06.tar.gz\"", dockerfile)
        self.assertIn(
            "replace google.golang.org/grpc => /src/grpc-go",
            dockerfile,
        )
        self.assertIn("go mod vendor -e", dockerfile)
        self.assertIn(
            "go mod edit -dropreplace=github.com/grafana/tempo",
            dockerfile,
        )
        self.assertIn(
            "go mod edit -dropreplace=google.golang.org/grpc",
            dockerfile,
        )
        self.assertIn(
            "go list -mod=vendor -m github.com/grafana/tempo google.golang.org/grpc",
            dockerfile,
        )
        self.assertEqual(1, dockerfile.count("go build -mod=vendor"))
        self.assertIn('io.dcim.remediation.grpc-go="1.82.1"', dockerfile)

    def test_kafka_recipe_remediates_fixable_jackson_core_high(self) -> None:
        repository_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        kafka = next(
            item for item in repository_manifest["recipes"]
            if item["component"] == "kafka"
        )
        expected_sha256 = (
            "4b40a06396f239f8de2da57419adde6e94e5edc18a2171d471ea05eeed4e5c2d"
        )
        self.assertIn(
            {
                "filename": "jackson-core-2.21.4.jar",
                "url": (
                    "https://repo.maven.apache.org/maven2/com/fasterxml/jackson/"
                    "core/jackson-core/2.21.4/jackson-core-2.21.4.jar"
                ),
                "sha256": expected_sha256,
                "context": True,
            },
            kafka["inputs"],
        )
        self.assertIn(
            {
                "finding": "GHSA-r7wm-3cxj-wff9",
                "artifact": "jackson-core",
                "from_version": "2.21.2",
                "to_version": "2.21.4",
                "sha256": expected_sha256,
            },
            kafka["patches"],
        )
        dockerfile = (MANIFEST.parent / kafka["dockerfile"]).read_text(
            encoding="utf-8",
        )
        self.assertIn("rm /opt/kafka/libs/jackson-core-2.21.2.jar", dockerfile)
        self.assertIn(
            "install -o root -g root -m 0444 /tmp/jackson-core-2.21.4.jar "
            "/opt/kafka/libs/jackson-core-2.21.4.jar",
            dockerfile,
        )

    def test_build_preserves_oci_export_but_loads_docker_archive(self) -> None:
        image_id = "sha256:" + "f" * 64
        with tempfile.TemporaryDirectory() as temporary:
            context = Path(temporary) / "contexts" / "postgres"
            context.mkdir(parents=True)
            output_root = context.parent.parent / "outputs"
            oci_archive = output_root / "postgres-first.oci.tar"
            docker_archive = output_root / "postgres-first.docker.tar"
            with (
                patch("scripts.foundation_images.run") as run_mock,
                patch(
                    "scripts.foundation_images.inspect_image",
                    return_value=(image_id, {}),
                ),
            ):
                build_once(recipe("postgres"), context, "first", clean=False)

        commands = [call.args[0] for call in run_mock.call_args_list]
        self.assertIn(
            f"type=oci,dest={oci_archive},rewrite-timestamp=true", commands[0],
        )
        self.assertIn(
            f"type=docker,dest={docker_archive},rewrite-timestamp=true", commands[0],
        )
        self.assertIn(
            ["docker", "load", "--input", str(docker_archive)], commands,
        )

    def test_runtime_environment_uses_only_immutable_local_image_ids(self) -> None:
        image_id = "sha256:" + "f" * 64
        environment = runtime_environment([
            {"component": component, "image_id": image_id}
            for component in (
                "postgres", "kafka", "grafana", "prometheus", "postgres-exporter",
            )
        ])
        self.assertEqual(
            {
                "DCIM_POSTGRES_IMAGE": image_id,
                "DCIM_KAFKA_IMAGE": image_id,
                "DCIM_GRAFANA_IMAGE": image_id,
                "DCIM_PROMETHEUS_IMAGE": image_id,
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
