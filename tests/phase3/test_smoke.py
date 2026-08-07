from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
import re
import sys
from typing import cast, override
import unittest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase3 import smoke


COMPOSE = ROOT / "deploy/compose/dev-build/compose.yaml"
PROMETHEUS = ROOT / "deploy/compose/dev-build/config/prometheus/prometheus.yml"
MAKEFILE = ROOT / "Makefile"


class FakeClient:
    def __init__(self, *, failures: dict[str, int] | None = None) -> None:
        self.failures = failures or {}
        self.authenticated_api_calls = 0

    def request(
        self,
        method: str,
        url: str,
        *,
        internal_token: str | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> tuple[int, bytes]:
        if internal_token is None and "/api/" in url:
            return 403, b"{}"
        if internal_token is not None and "/api/" in url:
            self.authenticated_api_calls += 1
        for marker, status in self.failures.items():
            if marker in url:
                return status, b"{}"
        if url.endswith("/health") or url.endswith("/ready"):
            return 200, b"{}"
        if url.endswith("/metrics"):
            return 200, b"process_metrics 1\n"
        if url.endswith("/api/v1/assets") and method == "POST":
            return 201, b'{"asset_id": "11111111-1111-4111-8111-111111111111"}'
        if "/api/v1/assets/" in url and method == "GET":
            return 200, b'{"asset_id": "11111111-1111-4111-8111-111111111111"}'
        if url.endswith("/api/v1/workflows/drafts") and method == "POST":
            return 201, b'{"draft_id": "22222222-2222-4222-8222-222222222222"}'
        if url.endswith("/simulate") and method == "POST":
            if payload == {"decision": "approve"}:
                return 200, b'{"status": "simulated_approved"}'
            return 409, b"{}"
        if "/api/v1/analytics/" in url:
            return 200, b"{}"
        return 200, b"{}"


def fake_resolve(service: str) -> str:
    return f"{service}.example.invalid"


class SmokeEnumerationTests(unittest.TestCase):
    def test_smoke_enumerates_all_five_services(self) -> None:
        self.assertEqual(
            ("asset-repository", "cmdb", "api", "analytics", "workflow"),
            smoke.SERVICES,
        )
        for service in smoke.SERVICES:
            with self.subTest(service=service):
                self.assertIn(service, smoke.API_PROBES)
                self.assertTrue(smoke.API_PROBES[service].startswith("/api/"))

    def test_evidence_schema_and_token_redaction(self) -> None:
        marker = "unit-test-marker"
        evidence = smoke.run_smoke(
            FakeClient(), fake_resolve, marker, generated_at="2026-08-03T00:00:00Z",
        )

        self.assertEqual("2026-08-03T00:00:00Z", evidence["generated_at"])
        services = cast(dict[str, object], evidence["services"])
        self.assertEqual(set(smoke.SERVICES), set(services))
        for service, result in services.items():
            with self.subTest(service=service):
                result = cast(dict[str, object], result)
                self.assertEqual(200, result["health"])
                self.assertEqual(200, result["ready"])
                self.assertGreater(cast(int, result["metrics_bytes"]), 0)
                self.assertEqual(403, result["auth_denial"])
        self.assertEqual(5, evidence["healthy_services"])
        self.assertEqual(5, evidence["auth_denials"])
        round_trip = cast(dict[str, object], evidence["gateway_round_trip"])
        self.assertEqual(201, round_trip["create_status"])
        self.assertEqual(200, round_trip["get_status"])
        self.assertIn("asset_id", round_trip)
        lifecycle = cast(dict[str, object], evidence["workflow_lifecycle"])
        self.assertEqual(201, lifecycle["create_status"])
        self.assertEqual(200, lifecycle["simulate_status"])
        self.assertEqual("simulated_approved", lifecycle["final_status"])
        self.assertEqual(409, lifecycle["terminal_status"])
        self.assertEqual(
            {"health": 200, "freshness": 200, "capacity": 200, "quality": 200},
            evidence["analytics"],
        )
        self.assertNotIn(marker, json.dumps(evidence))

    def test_unhealthy_service_fails_naming_the_service(self) -> None:
        client = FakeClient(failures={"cmdb.example.invalid:8000/health": 500})

        with self.assertRaises(smoke.SmokeFailure) as raised:
            smoke.run_smoke(client, fake_resolve, "token")

        self.assertIn("cmdb", str(raised.exception))

    def test_connection_failure_fails_naming_the_service(self) -> None:
        # Given: the real HTTP boundary cannot connect to CMDB.
        class ConnectionFailureClient(FakeClient):
            @override
            def request(
                self,
                method: str,
                url: str,
                *,
                internal_token: str | None = None,
                payload: Mapping[str, object] | None = None,
            ) -> tuple[int, bytes]:
                if "cmdb.example.invalid:8000/health" in url:
                    raise smoke.SmokeFailure("service connection failed")
                return super().request(method, url, internal_token=internal_token, payload=payload)

        # When: the full smoke reaches the stopped CMDB service.
        with self.assertRaises(smoke.SmokeFailure) as raised:
            smoke.run_smoke(ConnectionFailureClient(), fake_resolve, "token")

        # Then: the smoke failure itself identifies CMDB.
        self.assertEqual("cmdb: service connection failed", str(raised.exception))

    def test_unauthenticated_probe_must_return_403(self) -> None:
        class PermissiveClient(FakeClient):
            @override
            def request(
                self,
                method: str,
                url: str,
                *,
                internal_token: str | None = None,
                payload: Mapping[str, object] | None = None,
            ) -> tuple[int, bytes]:
                if internal_token is None and "/api/" in url:
                    return 200, b"{}"
                return super().request(method, url, internal_token=internal_token, payload=payload)

        with self.assertRaises(smoke.SmokeFailure) as raised:
            smoke.run_smoke(PermissiveClient(), fake_resolve, "token")

        self.assertIn("asset-repository", str(raised.exception))

    def test_metrics_must_be_non_empty(self) -> None:
        class EmptyMetricsClient(FakeClient):
            @override
            def request(
                self,
                method: str,
                url: str,
                *,
                internal_token: str | None = None,
                payload: Mapping[str, object] | None = None,
            ) -> tuple[int, bytes]:
                if url.endswith("/metrics"):
                    return 200, b"  \n"
                return super().request(method, url, internal_token=internal_token, payload=payload)

        with self.assertRaises(smoke.SmokeFailure) as raised:
            smoke.run_smoke(EmptyMetricsClient(), fake_resolve, "token")

        self.assertIn("metrics", str(raised.exception))

    def test_terminal_resimulation_must_conflict(self) -> None:
        class RepeatableClient(FakeClient):
            @override
            def request(
                self,
                method: str,
                url: str,
                *,
                internal_token: str | None = None,
                payload: Mapping[str, object] | None = None,
            ) -> tuple[int, bytes]:
                if url.endswith("/simulate") and method == "POST":
                    return 200, b'{"status": "simulated_approved"}'
                return super().request(method, url, internal_token=internal_token, payload=payload)

        with self.assertRaises(smoke.SmokeFailure) as raised:
            smoke.run_smoke(RepeatableClient(), fake_resolve, "token")

        self.assertIn("workflow", str(raised.exception))


class FullComposeContractTests(unittest.TestCase):
    compose: str = ""
    prometheus: str = ""

    @override
    def setUp(self) -> None:
        self.compose = COMPOSE.read_text(encoding="utf-8")
        self.prometheus = PROMETHEUS.read_text(encoding="utf-8")

    def service_block(self, service: str) -> str:
        match = re.search(
            rf"^  {re.escape(service)}:\n(?P<block>.*?)(?=^  [a-z][a-z-]*:\n|\Z)",
            self.compose,
            flags=re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, service)
        return match.group("block") if match is not None else ""

    def test_all_five_services_have_exact_profiles(self) -> None:
        expected_profiles = {
            "asset-repository": "profiles: [core]",
            "cmdb": "profiles: [core]",
            "api": "profiles: [dashboard]",
            "analytics": "profiles: [core]",
            "workflow": "profiles: [workflow]",
        }
        for service, profile in expected_profiles.items():
            with self.subTest(service=service):
                block = self.service_block(service)
                self.assertIn(profile, block)
                self.assertNotIn("ports:", block)

    def test_new_service_blocks_match_the_bounded_runtime_contract(self) -> None:
        expected = {
            "api": {
                "command": '["python3","-m","uvicorn","--factory","dcim_api.main:create_app","--host","0.0.0.0","--port","8000"]',
                "pythonpath": "PYTHONPATH: /opt/dcim/services/api/src:/opt/dcim/contracts/python:/opt/dcim/scripts",
                "role": "PGUSER: dcim_api_ro",
                "secrets": "secrets: [api-db-password, internal-api-token]",
            },
            "analytics": {
                "command": '["python3","-m","uvicorn","--factory","dcim_analytics.main:create_app","--host","0.0.0.0","--port","8000"]',
                "pythonpath": "PYTHONPATH: /opt/dcim/services/analytics/src:/opt/dcim/contracts/python:/opt/dcim/scripts",
                "role": "PGUSER: dcim_analytics_ro",
                "secrets": "secrets: [analytics-db-password, internal-api-token]",
            },
            "workflow": {
                "command": '["python3","-m","uvicorn","--factory","dcim_workflow.main:create_app","--host","0.0.0.0","--port","8000"]',
                "pythonpath": "PYTHONPATH: /opt/dcim/services/workflow/src:/opt/dcim/contracts/python:/opt/dcim/scripts",
                "role": "PGUSER: dcim_workflow_rw",
                "secrets": "secrets: [workflow-db-password, internal-api-token]",
            },
        }
        for service, contract in expected.items():
            with self.subTest(service=service):
                block = self.service_block(service)
                self.assertIn("<<: *long-running", block)
                self.assertIn("image: ${DCIM_SERVICES_IMAGE:?run make foundation-images-qualify}", block)
                self.assertIn('user: "10001:10001"', block)
                self.assertIn(contract["command"], block)
                self.assertIn(contract["pythonpath"], block)
                self.assertIn(contract["role"], block)
                self.assertIn(contract["secrets"], block)
                self.assertIn("PGHOST: postgres", block)
                self.assertIn("PGDATABASE: dcim_foundation", block)
                self.assertIn("DCIM_AUTH_REQUIRED: \"true\"", block)
                self.assertIn("INTERNAL_API_TOKEN_FILE: /run/secrets/internal-api-token", block)
                self.assertIn("../../../services:/opt/dcim/services:ro", block)
                self.assertIn("../../../contracts:/opt/dcim/contracts:ro", block)
                self.assertIn("../../../scripts:/opt/dcim/scripts:ro", block)
                self.assertIn("networks: [data, observability]", block)
                self.assertIn('sysctls: {net.ipv4.ip_forward: "0"}', block)
                self.assertIn("postgres: {condition: service_healthy}", block)
                self.assertIn('limits: {cpus: "0.5", memory: 512M}', block)
                self.assertIn("http://127.0.0.1:8000/ready", block)
                self.assertNotIn("ports:", block)

    def test_gateway_upstream_environment_is_literal(self) -> None:
        block = self.service_block("api")
        self.assertIn("ASSET_REPOSITORY_URL: http://asset-repository:8000", block)
        self.assertIn("CMDB_URL: http://cmdb:8000", block)

    def test_bind_mount_sources_resolve_to_existing_repo_root_directories(self) -> None:
        compose_dir = COMPOSE.parent
        for relative in ("services", "contracts", "scripts"):
            with self.subTest(relative=relative):
                source = (compose_dir / f"../../../{relative}").resolve()
                self.assertEqual(ROOT / relative, source)
                self.assertTrue(source.is_dir(), relative)

    def test_all_five_services_are_scraped(self) -> None:
        for service in smoke.SERVICES:
            with self.subTest(service=service):
                self.assertIn(f"job_name: {service}", self.prometheus)
                self.assertIn(f"targets: [{service}:8000]", self.prometheus)

    def test_makefile_wires_service_smoke_and_service_check(self) -> None:
        makefile = MAKEFILE.read_text(encoding="utf-8")
        self.assertIn("service-smoke:", makefile)
        self.assertIn("service-check: phase3-deps phase3-test service-smoke", makefile)
        self.assertIn("scripts/phase3/smoke.py", makefile)
        self.assertIn("--profile core --profile dashboard --profile workflow", makefile)
        self.assertIn("$(SERVICE_COMPOSE_CMD) stop --timeout 60 || status=$$?;", makefile)
        self.assertIn("if [ $$status -eq 0 ]; then", makefile)

    def test_every_compose_service_is_profile_gated(self) -> None:
        service_section = self.compose.split("services:", 1)[1].split("\nnetworks:\n", 1)[0]
        blocks = re.findall(
            r"^  ([a-z][a-z-]*):\n(?P<block>.*?)(?=^  [a-z][a-z-]*:\n|\Z)",
            service_section,
            flags=re.MULTILINE | re.DOTALL,
        )
        self.assertGreater(len(blocks), 0)
        for service, block in blocks:
            with self.subTest(service=service):
                self.assertIn("profiles:", block)


if __name__ == "__main__":
    _ = unittest.main()
