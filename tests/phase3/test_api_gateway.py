from __future__ import annotations

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
API_SOURCE = ROOT / "services/api/src"
if str(API_SOURCE) not in sys.path:
    sys.path.insert(0, str(API_SOURCE))

from dcim_api.main import DatabaseConfiguration, UpstreamConfigurationError, create_app


class FakePool:
    async def fetchval(self, query: str) -> int | str | None:
        if "MAX" in query:
            return "2026-08-05T10:30:00Z"
        return 1

    async def fetch(self, query: str, *params: str | None) -> list[dict[str, int | str]]:
        if "GROUP BY" in query:
            return [{"priority": "P1", "count": 2}, {"priority": "P2", "count": 3}]
        return []

    async def close(self) -> None:
        return None


class ApiGatewayTests(unittest.TestCase):
    temporary_directory: TemporaryDirectory[str]
    requests: list[httpx.Request]
    asset_count: int
    ci_count: int

    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        password_path = root / "db-password"
        password_path.write_text("synthetic-db-password\n", encoding="utf-8")
        token_path = root / "internal-token"
        token_path.write_text("synthetic-internal-token\n", encoding="utf-8")
        self.environment = patch.dict(
            os.environ,
            {
                "ASSET_REPOSITORY_URL": "http://asset-repository:8000",
                "CMDB_URL": "http://cmdb:8000",
                "DCIM_AUTH_REQUIRED": "true",
                "INTERNAL_API_TOKEN_FILE": str(token_path),
                "PGPASSWORD_FILE": str(password_path),
            },
            clear=True,
        )
        self.environment.start()
        self.requests: list[httpx.Request] = []
        self.asset_count = 4
        self.ci_count = 5

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_directory.cleanup()

    async def pool_factory(self, _configuration: DatabaseConfiguration) -> FakePool:
        return FakePool()

    def client_factory(self, base_url: str, header_value: str) -> httpx.AsyncClient:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if request.url.path == "/api/v1/assets":
                return httpx.Response(200, json=[{"asset_id": str(index)} for index in range(self.asset_count)])
            if request.url.path == "/api/v1/cis":
                return httpx.Response(200, json=[{"ci_id": str(index)} for index in range(self.ci_count)])
            return httpx.Response(201, content=request.content, headers={"content-type": "application/json"})

        return httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Internal-Token": header_value},
            transport=httpx.MockTransport(handler),
        )

    def test_proxy_preserves_path_query_body_and_injects_token(self) -> None:
        app = create_app(pool_factory=self.pool_factory, client_factory=self.client_factory)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/assets/synthetic-id?expand=aliases",
                content=b'{"asset_type":"server"}',
                headers={"X-Internal-Token": "synthetic-internal-token", "content-type": "application/json"},
            )

        self.assertEqual(response.status_code, 201)
        outbound = self.requests[0]
        self.assertEqual(outbound.url.path, "/api/v1/assets/synthetic-id")
        self.assertEqual(outbound.url.query, b"expand=aliases")
        self.assertEqual(outbound.content, b'{"asset_type":"server"}')
        self.assertEqual(outbound.headers["X-Internal-Token"], "synthetic-internal-token")

    def test_connect_error_returns_sanitized_bad_gateway(self) -> None:
        def failing_client_factory(base_url: str, header_value: str) -> httpx.AsyncClient:
            async def fail(request: httpx.Request) -> httpx.Response:
                raise httpx.ConnectError("synthetic private upstream detail", request=request)

            return httpx.AsyncClient(base_url=base_url, transport=httpx.MockTransport(fail))

        app = create_app(pool_factory=self.pool_factory, client_factory=failing_client_factory)

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/cis/synthetic-id",
                headers={"X-Internal-Token": "synthetic-internal-token"},
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "Upstream service unavailable"})
        self.assertNotIn("synthetic private upstream detail", response.text)
        self.assertNotIn("Traceback", response.text)

    def test_dashboard_summary_combines_noc_freshness_and_upstream_counts(self) -> None:
        app = create_app(pool_factory=self.pool_factory, client_factory=self.client_factory)

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/dashboard/summary",
                headers={"X-Internal-Token": "synthetic-internal-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "noc_cards": {"P1": 2, "P2": 3},
                "freshness": {"observed_at": "2026-08-05T10:30:00Z"},
                "assets": {"count": 4},
                "cis": {"count": 5},
            },
        )

    def test_startup_fails_when_an_upstream_url_is_unset(self) -> None:
        del os.environ["CMDB_URL"]
        app = create_app(pool_factory=self.pool_factory, client_factory=self.client_factory)

        with self.assertRaisesRegex(UpstreamConfigurationError, "gateway upstream configuration is unavailable"):
            with TestClient(app):
                pass


if __name__ == "__main__":
    unittest.main()
