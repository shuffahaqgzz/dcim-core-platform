from __future__ import annotations

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/cmdb/src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from dcim_cmdb.main import DatabaseConfiguration, create_app


CI_ID = "00000000-0000-0000-0000-000000000001"
RELATED_CI_ID = "00000000-0000-0000-0000-000000000002"
NOW = "2026-08-05T12:00:00+00:00"


def ci_payload(ci_id: str = CI_ID, device_id: str = "device-1") -> dict[str, object]:
    return {
        "ci_id": ci_id,
        "asset_id": None,
        "source_system": "synthetic",
        "native_device_id": device_id,
        "ci_type": "server",
        "aliases": [],
        "created_at": NOW,
        "updated_at": NOW,
    }


def relationship_payload() -> dict[str, object]:
    return {
        "relationship_id": "00000000-0000-0000-0000-000000000003",
        "from_ci": CI_ID,
        "to_ci": RELATED_CI_ID,
        "relationship_type": "depends_on",
        "valid_from": NOW,
        "valid_to": None,
        "source": "synthetic-test",
    }


class FakePool:
    def __init__(self) -> None:
        self.cis: dict[UUID, dict[str, object]] = {}
        self.relationships: list[dict[str, object]] = []

    async def fetchval(self, _query: str) -> int:
        return 1

    async def fetchrow(self, query: str, *parameters: object) -> dict[str, object] | None:
        if "FROM phase2.cis" in query:
            return self.cis.get(parameters[0])
        return None

    async def fetch(self, query: str, *parameters: object) -> list[dict[str, object]]:
        if "FROM phase2.aliases" in query:
            return []
        if "WITH RECURSIVE impact" in query:
            start, depth = parameters
            closure: list[dict[str, object]] = []
            frontier = [start]
            for _ in range(depth):
                matches = [item for item in self.relationships if item["from_ci"] in frontier]
                closure.extend(matches)
                frontier = [item["to_ci"] for item in matches]
            return closure
        if "FROM phase2.ci_relationships" in query:
            return self.relationships
        return list(self.cis.values())

    async def execute(self, query: str, *parameters: object) -> None:
        if "INSERT INTO phase2.cis" in query:
            self.cis[parameters[0]] = {
                "ci_id": parameters[0], "asset_id": parameters[1],
                "source_system": parameters[2], "native_device_id": parameters[3],
                "ci_type": parameters[4], "created_at": parameters[5], "updated_at": parameters[6],
            }
        if "INSERT INTO phase2.ci_relationships" in query:
            self.relationships.append({
                "relationship_id": parameters[0], "from_ci": parameters[1], "to_ci": parameters[2],
                "relationship_type": parameters[3], "valid_from": parameters[4], "valid_to": parameters[5],
                "source": parameters[6], "created_at": NOW,
            })

    async def executemany(self, _query: str, _parameters: object) -> None:
        return None

    async def close(self) -> None:
        return None


class CmdbModelTests(unittest.TestCase):
    def test_ci_when_schema_fields_are_supplied_accepts_canonical_payload(self) -> None:
        try:
            from dcim_cmdb.models import CI
        except ModuleNotFoundError as error:
            self.skipTest(str(error))

        value = CI.model_validate({"ci_id": "00000000-0000-0000-0000-000000000001", "source_system": "synthetic", "native_device_id": "device-1", "ci_type": "server", "aliases": [], "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"})

        self.assertEqual("synthetic", value.source_system)

    def test_relationship_when_type_is_invalid_rejects_it(self) -> None:
        try:
            from dcim_cmdb.models import Relationship
        except ModuleNotFoundError as error:
            self.skipTest(str(error))

        with self.assertRaises(ValueError):
            Relationship.model_validate({"relationship_id": "00000000-0000-0000-0000-000000000001", "from_ci": "00000000-0000-0000-0000-000000000002", "to_ci": "00000000-0000-0000-0000-000000000003", "relationship_type": "bogus"})


class CmdbAuthTests(unittest.TestCase):
    def test_auth_when_token_is_wrong_denies_request(self) -> None:
        from dcim_cmdb.auth import load_internal_token_auth

        with TemporaryDirectory() as directory:
            token_file = Path(directory) / "token"
            token_file.write_text("synthetic-token\n", encoding="utf-8")
            with patch.dict(os.environ, {"DCIM_AUTH_REQUIRED": "true", "INTERNAL_API_TOKEN_FILE": str(token_file)}, clear=True):
                self.assertFalse(load_internal_token_auth().permits("wrong-token"))


class CmdbHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        root = Path(self.directory.name)
        token_path = root / "internal-token"
        password_path = root / "database-password"
        token_path.write_text("synthetic-token\n", encoding="utf-8")
        password_path.write_text("synthetic-password\n", encoding="utf-8")
        self.environment = patch.dict(
            os.environ,
            {
                "DCIM_AUTH_REQUIRED": "true",
                "INTERNAL_API_TOKEN_FILE": str(token_path),
                "PGPASSWORD_FILE": str(password_path),
            },
            clear=True,
        )
        self.environment.start()
        self.pool = FakePool()

    def tearDown(self) -> None:
        self.environment.stop()
        self.directory.cleanup()

    async def pool_factory(self, _configuration: DatabaseConfiguration) -> FakePool:
        return self.pool

    def client(self) -> TestClient:
        return TestClient(create_app(pool_factory=self.pool_factory))

    def test_create_ci_then_get_round_trips_payload(self) -> None:
        # Given: an authorized synthetic CMDB client and CI payload.
        with self.client() as client:
            # When: the CI is created and retrieved by identifier.
            created = client.post("/api/v1/cis", json=ci_payload(), headers={"X-Internal-Token": "synthetic-token"})
            retrieved = client.get(f"/api/v1/cis/{CI_ID}", headers={"X-Internal-Token": "synthetic-token"})

        # Then: the API returns the persisted CI without alteration.
        self.assertEqual(201, created.status_code)
        self.assertEqual(200, retrieved.status_code)
        self.assertEqual(created.json(), retrieved.json())

    def test_relationship_then_impact_returns_transitive_closure_within_depth_limit(self) -> None:
        # Given: two persisted CIs and an authorized CMDB client.
        with self.client() as client:
            headers = {"X-Internal-Token": "synthetic-token"}
            client.post("/api/v1/cis", json=ci_payload(), headers=headers)
            client.post("/api/v1/cis", json=ci_payload(RELATED_CI_ID, "device-2"), headers=headers)

            # When: a relationship is created and impact is queried at depth five.
            created = client.post("/api/v1/relationships", json=relationship_payload(), headers=headers)
            impact = client.get(f"/api/v1/impact?ci_id={CI_ID}&depth=5", headers=headers)

        # Then: the relationship is returned in the bounded impact closure.
        self.assertEqual(201, created.status_code)
        self.assertEqual(200, impact.status_code)
        self.assertEqual([relationship_payload()["relationship_id"]], [item["relationship_id"] for item in impact.json()])

    def test_impact_when_depth_exceeds_five_returns_422(self) -> None:
        # Given / When: an authorized impact query uses an out-of-contract depth.
        with self.client() as client:
            response = client.get(f"/api/v1/impact?ci_id={CI_ID}&depth=6", headers={"X-Internal-Token": "synthetic-token"})

        # Then: FastAPI rejects the request at the boundary.
        self.assertEqual(422, response.status_code)

    def test_auth_denies_api_but_exempts_health(self) -> None:
        # Given: CMDB internal-token authentication is required.
        with self.client() as client:
            # When: protected routes omit or misuse the token, while health remains public.
            missing = client.get("/api/v1/cis")
            wrong = client.get("/api/v1/cis", headers={"X-Internal-Token": "wrong"})
            health = client.get("/health")

        # Then: API access fails closed and liveness stays observable.
        self.assertEqual(403, missing.status_code)
        self.assertEqual(403, wrong.status_code)
        self.assertEqual(200, health.status_code)


class CmdbIdentityTests(unittest.TestCase):
    def test_ci_id_when_native_identity_replayed_is_deterministic(self) -> None:
        from scripts.phase2.identity import derive_ci_id

        self.assertEqual(UUID("ec059315-8c4d-57a0-a4d0-77a1a71bd7e9"), derive_ci_id("synthetic", "device-1"))
