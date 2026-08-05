from __future__ import annotations

from pathlib import Path
import re
from typing import override
import unittest


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "deploy/compose/dev-build/compose.yaml"
PROMETHEUS = ROOT / "deploy/compose/dev-build/config/prometheus/prometheus.yml"
SMOKE = ROOT / "scripts/phase3/smoke.py"


class CoreComposeContractTests(unittest.TestCase):
    compose: str = ""
    prometheus: str = ""

    @override
    def setUp(self) -> None:
        self.compose = COMPOSE.read_text(encoding="utf-8")
        self.prometheus = PROMETHEUS.read_text(encoding="utf-8")

    def test_core_services_have_the_bounded_runtime_contract(self) -> None:
        expected = {
            "asset-repository": {
                "command": '["python3","-m","uvicorn","--factory","dcim_asset_repository.main:create_app","--host","0.0.0.0","--port","8000"]',
                "pythonpath": "PYTHONPATH: /opt/dcim/services/asset-repository/src:/opt/dcim/contracts/python:/opt/dcim/scripts",
                "role": "PGUSER: dcim_assets_rw",
                "password": "assets-db-password",
            },
            "cmdb": {
                "command": '["python3","-m","uvicorn","--factory","dcim_cmdb.main:create_app","--host","0.0.0.0","--port","8000"]',
                "pythonpath": "PYTHONPATH: /opt/dcim/services/cmdb/src:/opt/dcim/contracts/python:/opt/dcim/scripts",
                "role": "PGUSER: dcim_cmdb_rw",
                "password": "cmdb-db-password",
            },
        }

        for service, contract in expected.items():
            with self.subTest(service=service):
                match = re.search(
                    rf"^  {re.escape(service)}:\n(?P<block>.*?)(?=^  [a-z][a-z-]*:\n|\Z)",
                    self.compose,
                    flags=re.MULTILINE | re.DOTALL,
                )
                self.assertIsNotNone(match)
                block = match.group("block") if match is not None else ""
                self.assertIn("<<: *long-running", block)
                self.assertIn("profiles: [core]", block)
                self.assertIn("image: ${DCIM_SERVICES_IMAGE:?run make foundation-images-qualify}", block)
                self.assertIn('user: "10001:10001"', block)
                self.assertIn(contract["command"], block)
                self.assertIn(contract["pythonpath"], block)
                self.assertIn(contract["role"], block)
                self.assertIn("PGHOST: postgres", block)
                self.assertIn("PGPORT: \"5432\"", block)
                self.assertIn("PGDATABASE: dcim_foundation", block)
                self.assertIn("PORT: \"8000\"", block)
                self.assertIn("DCIM_AUTH_REQUIRED: \"true\"", block)
                self.assertIn("INTERNAL_API_TOKEN_FILE: /run/secrets/internal-api-token", block)
                self.assertIn(contract["password"], block)
                self.assertIn("internal-api-token", block)
                self.assertIn("../../../services:/opt/dcim/services:ro", block)
                self.assertIn("../../../contracts:/opt/dcim/contracts:ro", block)
                self.assertIn("../../../scripts:/opt/dcim/scripts:ro", block)
                self.assertIn("networks: [data, observability]", block)
                self.assertIn('sysctls: {net.ipv4.ip_forward: "0"}', block)
                self.assertIn("postgres: {condition: service_healthy}", block)
                self.assertIn('limits: {cpus: "0.5", memory: 512M}', block)
                self.assertIn("http://127.0.0.1:8000/ready", block)
                self.assertNotIn("ports:", block)

    def test_core_metrics_are_scraped_without_host_ports(self) -> None:
        for service in ("asset-repository", "cmdb"):
            with self.subTest(service=service):
                self.assertIn(f"job_name: {service}", self.prometheus)
                self.assertIn(f"targets: [{service}:8000]", self.prometheus)
                self.assertIn("metrics_path: /metrics", self.prometheus)

    def test_core_smoke_checks_health_and_readiness_for_each_service(self) -> None:
        source = SMOKE.read_text(encoding="utf-8")
        for service in ("asset-repository", "cmdb"):
            with self.subTest(service=service):
                self.assertIn(service, source)
        self.assertIn('"/health"', source)
        self.assertIn('"/ready"', source)
        self.assertIn("status == 200", source)


if __name__ == "__main__":
    _ = unittest.main()
