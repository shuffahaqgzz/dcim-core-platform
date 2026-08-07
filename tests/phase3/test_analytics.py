from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/analytics/src"
MAIN_PATH = SOURCE / "dcim_analytics/main.py"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from dcim_analytics.main import DatabaseConfiguration, create_app
from scripts.phase2.capacity import ADMISSION_THRESHOLD_PERCENT, POSTGRES_LOGICAL_BUDGET_BYTES


class AnalyticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        root = Path(self.directory.name)
        (root / "database-auth").write_text("synthetic-password\n", encoding="utf-8")
        (root / "internal-auth").write_text("synthetic-token\n", encoding="utf-8")
        self.environment = patch.dict(
            os.environ,
            {
                "DCIM_AUTH_REQUIRED": "true",
                "INTERNAL_API_TOKEN_FILE": str(root / "internal-auth"),
                "PGPASSWORD_FILE": str(root / "database-auth"),
            },
            clear=True,
        )
        self.environment.start()
        self.pool = AsyncMock()
        self.pool.fetchval.return_value = 1

    def tearDown(self) -> None:
        self.environment.stop()
        self.directory.cleanup()

    async def pool_factory(self, configuration: DatabaseConfiguration):
        self.assertEqual(configuration.user, "dcim_analytics_ro")
        return self.pool

    def client(self) -> TestClient:
        return TestClient(create_app(pool_factory=self.pool_factory))

    def test_module_ast_contains_no_mutating_sql(self) -> None:
        # Given: every string literal in the analytics service module.
        tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8"))
        strings = "\n".join(
            node.value.upper()
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        )

        # When/Then: no database mutation or DDL verb is present.
        for forbidden in ("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "TRUNCATE"):
            self.assertNotIn(forbidden, strings)

    def test_health_reports_trailing_day_validation_counts(self) -> None:
        self.pool.fetch.return_value = [
            {"validation_status": "accepted", "event_count": 7},
            {"validation_status": "quarantined", "event_count": 2},
        ]
        with self.client() as client:
            response = client.get(
                "/api/v1/analytics/health",
                headers={"X-Internal-Token": "synthetic-token"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["window_hours"], 24)
        self.assertEqual(response.json()["counts"], {"accepted": 7, "quarantined": 2})

    def test_freshness_marks_only_sources_older_than_fifteen_minutes_stale(self) -> None:
        now = datetime(2026, 8, 5, 12, tzinfo=UTC)
        self.pool.fetch.return_value = [
            {"source": "fresh-source", "latest_observed_at": now - timedelta(minutes=14, seconds=59)},
            {"source": "stale-source", "latest_observed_at": now - timedelta(minutes=15, seconds=1)},
        ]
        with patch("dcim_analytics.main._utc_now", return_value=now), self.client() as client:
            response = client.get(
                "/api/v1/analytics/freshness",
                headers={"X-Internal-Token": "synthetic-token"},
            )
        sources = {item["source"]: item for item in response.json()["sources"]}
        self.assertFalse(sources["fresh-source"]["stale"])
        self.assertTrue(sources["stale-source"]["stale"])
        self.assertEqual(response.json()["stale_after_seconds"], 900)

    def test_capacity_uses_imported_budget_and_admission_threshold(self) -> None:
        self.pool.fetchval.return_value = POSTGRES_LOGICAL_BUDGET_BYTES * 9 // 10
        with self.client() as client:
            response = client.get(
                "/api/v1/analytics/capacity",
                headers={"X-Internal-Token": "synthetic-token"},
            )
        self.assertEqual(response.json()["budget_bytes"], POSTGRES_LOGICAL_BUDGET_BYTES)
        self.assertEqual(response.json()["threshold_percent"], ADMISSION_THRESHOLD_PERCENT)
        self.assertEqual(response.json()["usage_percent"], 90.0)
        self.assertFalse(response.json()["within_budget"])

    def test_quality_reports_trailing_day_ratios(self) -> None:
        self.pool.fetchrow.return_value = {"total": 10, "quarantined": 2, "duplicate": 1}
        with self.client() as client:
            response = client.get(
                "/api/v1/analytics/quality",
                headers={"X-Internal-Token": "synthetic-token"},
            )
        self.assertEqual(
            response.json(),
            {"window_hours": 24, "total": 10, "quarantine_ratio": 0.2, "duplicate_ratio": 0.1},
        )

    def test_auth_denies_analytics_but_exempts_operational_endpoints(self) -> None:
        with self.client() as client:
            missing = client.get("/api/v1/analytics/health")
            wrong = client.get("/api/v1/analytics/health", headers={"X-Internal-Token": "wrong"})
            health = client.get("/health")
            metrics = client.get("/metrics")
        self.assertEqual(missing.status_code, 403)
        self.assertEqual(wrong.status_code, 403)
        self.assertEqual(health.status_code, 200)
        self.assertEqual(metrics.status_code, 200)


if __name__ == "__main__":
    unittest.main()
