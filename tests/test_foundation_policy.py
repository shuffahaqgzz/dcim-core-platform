from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy/compose/dev-build/compose.yaml"
POLICY = ROOT / "scripts/foundation_policy.py"


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
            "license_dispositions_sha256": disposition_sha256,
            "images": [
                {"component": component, "image_id": image_id}
                for component in ("postgres", "kafka", "grafana", "postgres-exporter")
            ],
        }), encoding="utf-8")
        (self.runtime_root / "dev-build/images.env").write_text(
            "\n".join([
                f"DCIM_POSTGRES_IMAGE={image_id}",
                f"DCIM_KAFKA_IMAGE={image_id}",
                f"DCIM_GRAFANA_IMAGE={image_id}",
                f"DCIM_POSTGRES_EXPORTER_IMAGE={image_id}",
            ]) + "\n",
            encoding="utf-8",
        )
        self.environment = environment

    def normalized_model(self) -> dict[str, object]:
        result = subprocess.run(
            [
                "docker", "compose", "--env-file",
                str(self.runtime_root / "dev-build/runtime.env"),
                "--env-file", str(self.runtime_root / "dev-build/images.env"),
                "-f", str(COMPOSE), "--profile", "data", "--profile",
                "observability", "--profile", "smoke", "config", "--format", "json",
            ],
            cwd=ROOT, env=self.environment, capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def validate(self, model: dict[str, object]) -> subprocess.CompletedProcess[str]:
        model_path = Path(self.temporary.name) / "model.json"
        model_path.write_text(json.dumps(model), encoding="utf-8")
        return subprocess.run(
            [
                "python3", str(POLICY), "--input", str(model_path),
                "--derived-lock", str(self.image_lock),
                "--license-dispositions", str(self.license_dispositions),
            ],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )

    def test_normalized_compose_model_passes(self) -> None:
        result = self.validate(self.normalized_model())
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("policy: PASS", result.stdout)

    def test_license_disposition_digest_mismatch_fails_closed(self) -> None:
        lock = json.loads(self.image_lock.read_text(encoding="utf-8"))
        lock["license_dispositions_sha256"] = "f" * 64
        self.image_lock.write_text(json.dumps(lock), encoding="utf-8")
        result = self.validate(self.normalized_model())
        self.assertNotEqual(0, result.returncode)
        self.assertIn("license disposition digest", result.stderr)

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


if __name__ == "__main__":
    unittest.main()
