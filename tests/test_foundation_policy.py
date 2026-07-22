from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.foundation_acceptance import write_acceptance_compose_override


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy/compose/dev-build/compose.yaml"
POLICY = ROOT / "scripts/foundation_policy.py"
RECIPES = ROOT / "deploy/compose/derived-images/recipes.json"


class FoundationPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir="/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.runtime_root = Path(self.temporary.name) / "runtime"
        environment = os.environ.copy()
        environment["DCIM_RUNTIME_ROOT"] = str(self.runtime_root)
        for inherited_make_state in ("MAKEFLAGS", "MFLAGS", "MAKEOVERRIDES"):
            environment.pop(inherited_make_state, None)
        bootstrap = subprocess.run(
            ["make", "foundation-bootstrap"], cwd=ROOT, env=environment,
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, bootstrap.returncode, bootstrap.stderr)
        image_id = "sha256:" + "a" * 64
        self.license_dispositions = Path(self.temporary.name) / "license-dispositions.json"
        self.license_dispositions.write_text("{}\n", encoding="utf-8")
        disposition_sha256 = hashlib.sha256(self.license_dispositions.read_bytes()).hexdigest()
        self.image_lock = self.runtime_root / "dev-build/derived-images-lock.json"
        self.image_lock.write_text(json.dumps({
            "schema_version": 2,
            "publication": False,
            "manifest_sha256": hashlib.sha256(RECIPES.read_bytes()).hexdigest(),
            "license_dispositions_sha256": disposition_sha256,
            "images": [
                {"component": component, "image_id": image_id}
                for component in (
                    "postgres", "kafka", "grafana", "prometheus", "postgres-exporter",
                )
            ],
        }), encoding="utf-8")
        (self.runtime_root / "dev-build/images.env").write_text(
            "\n".join([
                f"DCIM_POSTGRES_IMAGE={image_id}",
                f"DCIM_KAFKA_IMAGE={image_id}",
                f"DCIM_GRAFANA_IMAGE={image_id}",
                f"DCIM_PROMETHEUS_IMAGE={image_id}",
                f"DCIM_POSTGRES_EXPORTER_IMAGE={image_id}",
            ]) + "\n",
            encoding="utf-8",
        )
        self.environment = environment

    def normalized_model(
        self,
        project_name: str = "dcim-build",
        *,
        acceptance_override: bool = False,
    ) -> dict[str, object]:
        environment = {**self.environment, "COMPOSE_PROJECT_NAME": project_name}
        command = [
            "docker", "compose", "--env-file",
            str(self.runtime_root / "dev-build/runtime.env"),
            "--env-file", str(self.runtime_root / "dev-build/images.env"),
            "-f", str(COMPOSE),
        ]
        if acceptance_override:
            command.extend(("-f", str(write_acceptance_compose_override(
                self.runtime_root,
                project_name,
            ))))
        command.extend(
            ["--profile", "data", "--profile", "observability", "--profile", "smoke"],
        )
        command.extend(["config", "--format", "json"])
        result = subprocess.run(
            command,
            cwd=ROOT, env=environment, capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def validate(
        self,
        model: dict[str, object],
        *,
        derived_lock: Path | None = None,
        project_name: str = "dcim-build",
    ) -> subprocess.CompletedProcess[str]:
        model_path = Path(self.temporary.name) / "model.json"
        model_path.write_text(json.dumps(model), encoding="utf-8")
        return subprocess.run(
            [
                "python3", str(POLICY), "--input", str(model_path),
                "--runtime-root", str(self.runtime_root),
                "--derived-lock", str(derived_lock or self.image_lock),
                "--license-dispositions", str(self.license_dispositions),
                "--project-name", project_name,
            ],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )

    def test_normalized_compose_model_passes(self) -> None:
        result = self.validate(self.normalized_model())
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("policy: PASS", result.stdout)

    def test_acceptance_namespace_model_passes_without_reusing_default_resources(self) -> None:
        project = "dcim-build-acceptance-abcdef123456"
        model = self.normalized_model(project, acceptance_override=True)

        result = self.validate(model, project_name=project)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(project, model["name"])
        self.assertEqual(f"{project}-data", model["networks"]["data"]["name"])
        self.assertEqual(
            {f"{project}-postgres-data", f"{project}-kafka-data", f"{project}-prometheus-data"},
            {value["name"] for value in model["volumes"].values()},
        )

    def test_direct_compose_project_name_does_not_change_resource_names(self) -> None:
        model = self.normalized_model("dcim-build-acceptance-abcdef123456")

        self.assertEqual("dcim-build-data", model["networks"]["data"]["name"])
        self.assertEqual("dcim-build-observability", model["networks"]["observability"]["name"])
        self.assertEqual(
            {"dcim-build-postgres-data", "dcim-build-kafka-data", "dcim-build-prometheus-data"},
            {value["name"] for value in model["volumes"].values()},
        )

    def test_unallowlisted_project_name_fails_closed(self) -> None:
        model = self.normalized_model()
        result = self.validate(model, project_name="dcim-build-prod")

        self.assertNotEqual(0, result.returncode)
        self.assertIn("project name", result.stderr)

    def test_license_disposition_digest_mismatch_fails_closed(self) -> None:
        lock = json.loads(self.image_lock.read_text(encoding="utf-8"))
        lock["license_dispositions_sha256"] = "f" * 64
        self.image_lock.write_text(json.dumps(lock), encoding="utf-8")
        result = self.validate(self.normalized_model())
        self.assertNotEqual(0, result.returncode)
        self.assertIn("license disposition digest", result.stderr)

    def test_derived_lock_must_bind_exact_recipe_manifest(self) -> None:
        lock = json.loads(self.image_lock.read_text(encoding="utf-8"))
        lock["manifest_sha256"] = "0" * 64
        self.image_lock.write_text(json.dumps(lock), encoding="utf-8")

        result = self.validate(self.normalized_model())

        self.assertNotEqual(0, result.returncode)
        self.assertIn("recipe manifest digest", result.stderr)

    def test_derived_lock_must_belong_to_selected_runtime_root(self) -> None:
        external_lock = Path(self.temporary.name) / "lookalike-lock.json"
        external_lock.write_bytes(self.image_lock.read_bytes())

        result = self.validate(self.normalized_model(), derived_lock=external_lock)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("selected runtime root", result.stderr)

    def test_duplicate_derived_lock_member_fails_closed(self) -> None:
        lock = self.image_lock.read_text(encoding="utf-8")
        self.image_lock.write_text(
            lock.replace('"schema_version": 2', '"schema_version": 2, "schema_version": 2'),
            encoding="utf-8",
        )
        result = self.validate(self.normalized_model())
        self.assertNotEqual(0, result.returncode)
        self.assertIn("duplicate JSON member", result.stderr)

    def test_unpinned_image_fails_closed(self) -> None:
        model = self.normalized_model()
        model["services"]["postgres"]["image"] = "postgres:17.10-bookworm"
        result = self.validate(model)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("immutable digest", result.stderr)

    def test_pinned_but_unapproved_image_fails_closed(self) -> None:
        model = self.normalized_model()
        model["services"]["postgres"]["image"] = "sha256:" + "b" * 64
        result = self.validate(model)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("image inventory", result.stderr)

    def test_unexpected_published_port_fails_closed(self) -> None:
        model = self.normalized_model()
        model["services"]["postgres"]["ports"] = [
            {"host_ip": "0.0.0.0", "published": "5432", "target": 5432, "protocol": "tcp"}
        ]
        result = self.validate(model)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("published port", result.stderr)

    def test_privilege_and_dual_home_bypass_fail_closed(self) -> None:
        model = self.normalized_model()
        model["services"]["prometheus"]["privileged"] = True
        model["services"]["prometheus"]["networks"] = {"data": None, "observability": None}
        result = self.validate(model)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("privileged", result.stderr)
        self.assertIn("dual-homed", result.stderr)

    def test_disguised_socket_and_privilege_relaxations_fail_closed(self) -> None:
        model = self.normalized_model()
        service = model["services"]["prometheus"]
        service["volumes"].append({
            "type": "bind", "source": "/var/run/docker.sock",
            "target": "/run/control.sock", "read_only": True,
        })
        service["group_add"] = ["999"]
        service["security_opt"].append("seccomp=unconfined")
        result = self.validate(model)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Docker socket", result.stderr)
        self.assertIn("supplemental groups", result.stderr)
        self.assertIn("exact no-new-privileges", result.stderr)
        self.assertIn("not allowlisted", result.stderr)

    def test_api_socket_and_secret_mount_bypasses_fail_closed(self) -> None:
        model = self.normalized_model()
        service = model["services"]["prometheus"]
        service["use_api_socket"] = True
        service["configs"] = [{"source": "control", "target": "/run/control"}]
        service["user"] = "65534:999"
        model["secrets"]["control"] = {
            "name": "dcim-build_control", "file": "/var/run/docker.sock",
        }
        service["secrets"] = [{"source": "control", "target": "/run/control"}]
        result = self.validate(model)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("alternate host mount", result.stderr)
        self.assertIn("exact reviewed UID:GID", result.stderr)
        self.assertIn("service secret allowlist", result.stderr)
        self.assertIn("top-level secret allowlist", result.stderr)
        self.assertIn("top-level secret source", result.stderr)

    def test_literal_secret_environment_fails_closed(self) -> None:
        model = self.normalized_model()
        model["services"]["grafana"]["environment"]["GF_SECURITY_ADMIN_PASSWORD"] = "not-public"
        result = self.validate(model)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("secret environment", result.stderr)

    def test_runtime_artifact_and_secret_must_match_selected_root(self) -> None:
        model = self.normalized_model()
        model["secrets"]["postgres-monitor-password"]["file"] = (
            "/tmp/other-runtime/dev-build/secrets/postgres-monitor-password"
        )
        for mount in model["services"]["kafka-jmx-exporter"]["volumes"]:
            if mount.get("target") == "/opt/jmx-exporter/jmx_prometheus_standalone-1.6.0.jar":
                mount["source"] = (
                    "/tmp/other-runtime/dev-build/artifacts/"
                    "jmx_prometheus_standalone-1.6.0.jar"
                )

        result = self.validate(model)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("bind source/target", result.stderr)
        self.assertIn("top-level secret source", result.stderr)

    def test_profile_membership_must_match_service_role(self) -> None:
        model = self.normalized_model()
        model["services"]["postgres"]["profiles"] = ["observability"]
        result = self.validate(model)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("profile membership", result.stderr)

    def test_aggregate_resource_budget_fails_closed(self) -> None:
        model = self.normalized_model()
        model["services"]["grafana"]["deploy"]["resources"]["limits"]["cpus"] = 2
        model["services"]["grafana"]["deploy"]["resources"]["limits"]["memory"] = str(2 * 1024**3)
        result = self.validate(model)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("aggregate CPU limit", result.stderr)
        self.assertIn("aggregate memory limit", result.stderr)

    def test_network_inventory_must_be_exact(self) -> None:
        model = self.normalized_model()
        model["networks"]["extra"] = {"internal": True}
        result = self.validate(model)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("network allowlist mismatch", result.stderr)

    def test_stateful_volume_mounts_must_match_exact_service_owner(self) -> None:
        model = self.normalized_model()
        model["services"]["postgres-exporter"]["volumes"] = [{
            "type": "volume",
            "source": "postgres-data",
            "target": "/var/lib/postgresql/data",
            "volume": {},
        }]

        result = self.validate(model)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("volume mount allowlist", result.stderr)

    def test_dual_homed_exporter_command_must_match_reviewed_inventory(self) -> None:
        model = self.normalized_model()
        model["services"]["kafka-jmx-exporter"]["command"] = [
            "python3", "-m", "http.server", "5556",
        ]

        result = self.validate(model)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("reviewed exporter process", result.stderr)

    def test_kafka_automatic_topic_creation_must_remain_disabled(self) -> None:
        model = self.normalized_model()
        model["services"]["kafka"]["environment"][
            "KAFKA_AUTO_CREATE_TOPICS_ENABLE"
        ] = "true"

        result = self.validate(model)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Kafka runtime contract", result.stderr)

    def test_service_namespace_and_network_membership_must_be_exact(self) -> None:
        model = self.normalized_model()
        model["services"]["postgres"]["network_mode"] = "container:outside"
        model["services"]["postgres"]["networks"] = {}

        result = self.validate(model)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("external namespace prohibited", result.stderr)
        self.assertIn("network membership mismatch", result.stderr)

    def test_project_and_network_names_must_bind_to_dev_build_plane(self) -> None:
        model = self.normalized_model()
        model["name"] = "other-project"
        model["networks"]["data"]["name"] = "other-data"

        result = self.validate(model)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("project name", result.stderr)
        self.assertIn("network runtime name", result.stderr)

    def test_healthcheck_must_match_functional_service_contract(self) -> None:
        model = self.normalized_model()
        model["services"]["kafka"]["healthcheck"]["test"] = ["CMD", "true"]

        result = self.validate(model)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("health contract mismatch", result.stderr)

    def test_prometheus_retention_command_must_match_capacity_contract(self) -> None:
        model = self.normalized_model()
        model["services"]["prometheus"]["command"] = [
            item.replace("7d", "14d")
            for item in model["services"]["prometheus"]["command"]
        ]

        result = self.validate(model)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Prometheus runtime contract", result.stderr)


if __name__ == "__main__":
    unittest.main()
