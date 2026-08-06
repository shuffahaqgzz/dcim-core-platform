from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
API_SOURCE = ROOT / "services/api/src"
if str(API_SOURCE) not in sys.path:
    sys.path.insert(0, str(API_SOURCE))

from dcim_api.main import DatabaseConfiguration, create_app


class FakePool:
    def __init__(self) -> None:
        self.ready_error: OSError | None = None
        self.sql = ""
        self.params: tuple[str | None, ...] = ()
        self.rows: list[dict[str, str]] = []

    async def fetchval(self, query: str) -> int:
        if self.ready_error is not None:
            raise self.ready_error
        return 1

    async def fetch(self, query: str, *params: str | None) -> list[dict[str, str]]:
        self.sql = query
        self.params = params
        return self.rows

    async def close(self) -> None:
        return None


class ApiNocTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        password_path = Path(self.temporary_directory.name) / "db-password"
        password_path.write_text("synthetic-db-password\n", encoding="utf-8")
        token_path = Path(self.temporary_directory.name) / "internal-token"
        token_path.write_text("synthetic-internal-token\n", encoding="utf-8")
        self.environment = patch.dict(
            os.environ,
            {
                "DCIM_AUTH_REQUIRED": "false",
                "ASSET_REPOSITORY_URL": "http://asset-repository:8000",
                "CMDB_URL": "http://cmdb:8000",
                "INTERNAL_API_TOKEN_FILE": str(token_path),
                "PGHOST": "synthetic-postgres",
                "PGPORT": "5432",
                "PGDATABASE": "dcim_foundation",
                "PGUSER": "dcim_api_ro",
                "PGPASSWORD_FILE": str(password_path),
            },
            clear=True,
        )
        self.environment.start()
        self.pool = FakePool()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_directory.cleanup()

    async def pool_factory(self, _configuration: DatabaseConfiguration) -> FakePool:
        return self.pool

    def test_import_has_no_fastapi_side_effect_when_module_is_loaded(self) -> None:
        # Given: a fresh interpreter with only the API source on its import path.
        script = (
            "import sys; import dcim_api.main; "
            "raise SystemExit(1 if 'fastapi' in sys.modules else 0)"
        )

        # When: the scaffold module is imported without creating an app.
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            env={"PYTHONPATH": str(API_SOURCE)},
            capture_output=True,
            text=True,
            check=False,
        )

        # Then: FastAPI has not been imported and no output was emitted.
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_health_returns_200_without_database_access(self) -> None:
        # Given: an app whose database pool has no rows.
        app = create_app(pool_factory=self.pool_factory)

        # When: the exempt health endpoint is requested in process.
        with TestClient(app) as client:
            response = client.get("/health")

        # Then: liveness is independent of the database.
        self.assertEqual(response.status_code, 200)

    def test_health_returns_200_without_database_configuration(self) -> None:
        # Given: the API starts without read-only database configuration.
        self.environment.stop()
        self.environment = patch.dict(
            os.environ,
            {
                "DCIM_AUTH_REQUIRED": "false",
                "ASSET_REPOSITORY_URL": "http://asset-repository:8000",
                "CMDB_URL": "http://cmdb:8000",
                "INTERNAL_API_TOKEN_FILE": str(Path(self.temporary_directory.name) / "internal-token"),
            },
            clear=True,
        )
        self.environment.start()
        app = create_app(pool_factory=self.pool_factory)

        # When: the exempt health endpoint is requested.
        with TestClient(app) as client:
            response = client.get("/health")

        # Then: liveness remains available while the read model is unavailable.
        self.assertEqual(response.status_code, 200)

    def test_ready_returns_503_when_database_probe_fails(self) -> None:
        # Given: a running app whose read-only database probe fails.
        self.pool.ready_error = OSError("synthetic database unavailable")
        app = create_app(pool_factory=self.pool_factory)

        # When: readiness is requested in process.
        with TestClient(app) as client:
            response = client.get("/ready")

        # Then: the app reports unavailable without exposing the error.
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotIn("synthetic database unavailable", response.text)

    def test_priority_filter_reaches_read_only_sql_parameter(self) -> None:
        # Given: an app with a recording database pool.
        app = create_app(pool_factory=self.pool_factory)

        # When: NOC cards are filtered by priority.
        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/noc-cards?priority=P1")

        # Then: the filter is bound as a SQL parameter on the read model query.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.pool.params, ("P1",))
        self.assertIn("SELECT", self.pool.sql)
        self.assertIn("FROM phase2.noc_cards", self.pool.sql)

    def test_noc_cards_decodes_jsonb_text_from_asyncpg(self) -> None:
        # Given: asyncpg returns the JSONB payload using its text representation.
        self.pool.rows = [
            {
                "run_id": "synthetic-run",
                "kind": "event",
                "subject_key": "synthetic-subject",
                "payload": '{"envelope":{"priority":"P1"}}',
                "generated_at": "2026-08-06T00:00:00Z",
            }
        ]
        app = create_app(pool_factory=self.pool_factory)

        # When: the NOC-card read model is requested through the HTTP API.
        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/noc-cards?priority=P1")

        # Then: the JSON response exposes payload as an object, not encoded text.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["payload"], {"envelope": {"priority": "P1"}})


if __name__ == "__main__":
    unittest.main()
