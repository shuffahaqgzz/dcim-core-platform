from __future__ import annotations

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
API_SOURCE = ROOT / "services/api/src"
if str(API_SOURCE) not in sys.path:
    sys.path.insert(0, str(API_SOURCE))

from dcim_api.auth import AuthConfigurationError
from dcim_api.main import DatabaseConfiguration, create_app


class EmptyPool:
    async def fetchval(self, query: str) -> int:
        return 1

    async def fetch(self, query: str, *params: str | None) -> list[dict[str, str]]:
        return []

    async def close(self) -> None:
        return None


class AuthMiddlewareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.token_path = root / "internal-token"
        self.token_path.write_text("synthetic-internal-token\n", encoding="utf-8")
        password_path = root / "db-password"
        password_path.write_text("synthetic-db-password\n", encoding="utf-8")
        self.environment = patch.dict(
            os.environ,
            {
                "DCIM_AUTH_REQUIRED": "true",
                "INTERNAL_API_TOKEN_FILE": str(self.token_path),
                "PGHOST": "synthetic-postgres",
                "PGPORT": "5432",
                "PGDATABASE": "dcim_foundation",
                "PGUSER": "dcim_api_ro",
                "PGPASSWORD_FILE": str(password_path),
            },
            clear=True,
        )
        self.environment.start()
        self.pool = EmptyPool()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_directory.cleanup()

    async def pool_factory(self, _configuration: DatabaseConfiguration) -> EmptyPool:
        return self.pool

    def test_missing_token_returns_403_for_api_route(self) -> None:
        # Given: authentication is required for a protected API route.
        app = create_app(pool_factory=self.pool_factory)

        # When: the route is requested without a token.
        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/noc-cards")

        # Then: access is denied by default.
        self.assertEqual(response.status_code, 403)

    def test_wrong_token_returns_403_for_api_route(self) -> None:
        # Given: authentication is required for a protected API route.
        app = create_app(pool_factory=self.pool_factory)

        # When: the route is requested with a different token.
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/dashboard/noc-cards",
                headers={"X-Internal-Token": "wrong-synthetic-token"},
            )

        # Then: access is denied.
        self.assertEqual(response.status_code, 403)

    def test_valid_token_returns_200_for_api_route(self) -> None:
        # Given: authentication is required for a protected API route.
        app = create_app(pool_factory=self.pool_factory)

        # When: the route is requested with the configured token.
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/dashboard/noc-cards",
                headers={"X-Internal-Token": "synthetic-internal-token"},
            )

        # Then: access succeeds.
        self.assertEqual(response.status_code, 200)

    def test_health_is_exempt_without_token(self) -> None:
        # Given: authentication is required for API routes.
        app = create_app(pool_factory=self.pool_factory)

        # When: the health endpoint is requested without a token.
        with TestClient(app) as client:
            response = client.get("/health")

        # Then: health remains exempt.
        self.assertEqual(response.status_code, 200)

    def test_missing_token_file_fails_closed_during_app_startup(self) -> None:
        # Given: authentication is required but its token file is missing.
        self.token_path.unlink()

        # When/Then: app startup fails closed before serving requests.
        with self.assertRaises(AuthConfigurationError):
            create_app(pool_factory=self.pool_factory)


if __name__ == "__main__":
    unittest.main()
