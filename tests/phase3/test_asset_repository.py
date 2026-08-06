from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/asset-repository/src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from dcim_asset_repository.main import DatabaseConfiguration, create_app
from dcim_asset_repository.models import Alias, Asset


ASSET_ID = "11111111-1111-1111-1111-111111111111"
NOW = "2026-08-05T12:00:00+00:00"


def asset_payload(serial: str = "SYNTHETIC-SERIAL-001") -> dict[str, object]:
    return {
        "asset_id": ASSET_ID,
        "identity": {"manufacturer": "Synthetic Systems", "serial_number": serial},
        "asset_type": "server",
        "aliases": [
            {
                "type": "hostname",
                "value": "synthetic-host",
                "valid_from": NOW,
                "valid_to": None,
                "source": "synthetic-test",
                "confidence": 0.9,
            }
        ],
        "created_at": NOW,
        "updated_at": NOW,
    }


class FakePool:
    def __init__(self) -> None:
        self.assets: dict[UUID, dict[str, object]] = {}
        self.aliases: list[dict[str, object]] = []
        self.sql = ""
        self.params: tuple[object, ...] = ()

    async def fetchval(self, _query: str) -> int:
        return 1

    async def fetchrow(self, query: str, *params: object) -> dict[str, object] | None:
        self.sql, self.params = query, params
        if "FROM phase2.assets" in query:
            return self.assets.get(params[0])
        return None

    async def fetch(self, query: str, *params: object) -> list[dict[str, object]]:
        self.sql, self.params = query, params
        if "FROM phase2.aliases" in query:
            asset_id = params[0]
            return [
                {key: value for key, value in alias.items() if key != "owner_id"}
                for alias in self.aliases
                if alias["owner_id"] == asset_id
            ]
        if "JOIN phase2.aliases" in query:
            alias_type, alias_value = params[:2]
            return [
                self.assets[alias["owner_id"]]
                for alias in self.aliases
                if alias["type"] == alias_type and alias["value"] == alias_value and alias["valid_to"] is None
            ]
        return list(self.assets.values())

    async def execute(self, query: str, *params: object) -> None:
        self.sql, self.params = query, params
        if "INSERT INTO phase2.assets" in query:
            self.assets[params[0]] = {
                "asset_id": params[0],
                "identity": params[1],
                "asset_type": params[2],
                "created_at": params[3],
                "updated_at": params[4],
            }

    async def executemany(self, query: str, params: list[tuple[object, ...]]) -> None:
        self.sql = query
        for values in params:
            self.aliases.append(
                {
                    "owner_id": values[0], "type": values[1], "value": values[2],
                    "valid_from": values[3], "valid_to": values[4], "source": values[5],
                    "confidence": values[6],
                }
            )

    async def close(self) -> None:
        return None


class AssetRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        root = Path(self.directory.name)
        auth_path = root / "internal-auth"
        database_path = root / "database-auth"
        auth_path.write_text("synthetic-token\n", encoding="utf-8")
        database_path.write_text("synthetic-password\n", encoding="utf-8")
        self.environment = patch.dict(os.environ, {
            "DCIM_AUTH_REQUIRED": "true", "INTERNAL_API_TOKEN_FILE": str(auth_path),
            "PGPASSWORD_FILE": str(database_path),
        }, clear=True)
        self.environment.start()
        self.pool = FakePool()

    def tearDown(self) -> None:
        self.environment.stop()
        self.directory.cleanup()

    async def pool_factory(self, _configuration: DatabaseConfiguration) -> FakePool:
        return self.pool

    def client(self) -> TestClient:
        return TestClient(create_app(pool_factory=self.pool_factory))

    def test_models_match_schema_fixture_fields(self) -> None:
        # Given: a synthetic fixture containing every schema field.
        payload = asset_payload()
        schema = json.loads((ROOT / "schemas/asset.schema.json").read_text(encoding="utf-8"))
        # When: it crosses the Pydantic contract boundary.
        model = Asset.model_validate(payload)
        # Then: the model preserves schema fields and validates alias confidence.
        self.assertEqual(set(model.model_dump(mode="json")), set(schema["required"]))
        self.assertEqual(Alias.model_validate(payload["aliases"][0]).confidence, 0.9)

    def test_create_uses_canonical_identity_derivation(self) -> None:
        # Given: the shared Phase 2 identity derivation at the service boundary.
        with patch("scripts.phase2.identity.derive_asset_id") as derive:
            with self.client() as client:
                # When: an authorized asset is created.
                response = client.post("/api/v1/assets", json=asset_payload(), headers={"X-Internal-Token": "synthetic-token"})
        # Then: the service delegates identity validation to the canonical module.
        self.assertEqual(response.status_code, 201)
        derive.assert_called_once_with({"manufacturer": "Synthetic Systems", "serial_number": "SYNTHETIC-SERIAL-001"})

    def test_create_then_get_returns_identical_payload(self) -> None:
        # Given: an authorized repository client and synthetic asset.
        with self.client() as client:
            # When: the asset is created then retrieved.
            created = client.post("/api/v1/assets", json=asset_payload(), headers={"X-Internal-Token": "synthetic-token"})
            retrieved = client.get(f"/api/v1/assets/{ASSET_ID}", headers={"X-Internal-Token": "synthetic-token"})
        # Then: persistence round-trips the full public payload.
        self.assertEqual(created.status_code, 201)
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(retrieved.json(), created.json())

    def test_replay_is_idempotent_and_changed_identity_conflicts(self) -> None:
        # Given: an existing authorized asset idempotency key.
        with self.client() as client:
            headers = {"X-Internal-Token": "synthetic-token"}
            client.post("/api/v1/assets", json=asset_payload(), headers=headers)
            # When: its payload is replayed and then changed.
            replay = client.post("/api/v1/assets", json=asset_payload(), headers=headers)
            conflict = client.post("/api/v1/assets", json=asset_payload("SYNTHETIC-SERIAL-002"), headers=headers)
        # Then: only the byte-equivalent replay succeeds.
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(conflict.status_code, 409)

    def test_alias_resolution_filters_expired_aliases_in_sql(self) -> None:
        # Given: a stored alias whose validity period has ended.
        with self.client() as client:
            headers = {"X-Internal-Token": "synthetic-token"}
            client.post("/api/v1/assets", json=asset_payload(), headers=headers)
            self.pool.aliases[0]["valid_to"] = "2000-01-01T00:00:00+00:00"
            # When: the live alias is resolved.
            response = client.get("/api/v1/assets?alias_type=hostname&alias_value=synthetic-host", headers=headers)
        # Then: SQL applies the ADR-0020 validity window and excludes it.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        self.assertIn("valid_to IS NULL OR a.valid_to > now()", self.pool.sql)
        self.assertIn("ORDER BY a.confidence DESC, a.valid_from DESC", self.pool.sql)

    def test_auth_denies_api_but_exempts_health(self) -> None:
        # Given: token authentication is required.
        with self.client() as client:
            # When: a protected route has no or wrong token, while health has none.
            missing = client.get("/api/v1/assets")
            wrong = client.get("/api/v1/assets", headers={"X-Internal-Token": "wrong"})
            health = client.get("/health")
        # Then: API access is denied and liveness stays public.
        self.assertEqual(missing.status_code, 403)
        self.assertEqual(wrong.status_code, 403)
        self.assertEqual(health.status_code, 200)


if __name__ == "__main__":
    unittest.main()
