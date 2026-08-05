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
SOURCE = ROOT / "services/workflow/src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from dcim_workflow.main import DatabaseConfiguration, create_app


class FakePool:
    def __init__(self) -> None:
        self.rows: dict[UUID, dict[str, object]] = {}

    async def fetchval(self, _query: str) -> int:
        return 1

    async def fetchrow(self, query: str, *parameters: object) -> dict[str, object] | None:
        if query.lstrip().startswith("INSERT"):
            draft_id, created_at, event_id, draft_type, payload, status, audit = parameters
            row = {"draft_id": draft_id, "created_at": created_at, "event_id": event_id, "draft_type": draft_type, "payload": payload, "status": status, "audit": audit}
            assert isinstance(draft_id, UUID)
            self.rows[draft_id] = row
            return row
        if query.lstrip().startswith("UPDATE"):
            draft_id, status, audit = parameters
            assert isinstance(draft_id, UUID)
            row = self.rows[draft_id]
            row.update(status=status, audit=audit)
            return row
        draft_id = parameters[0]
        assert isinstance(draft_id, UUID)
        return self.rows.get(draft_id)

    async def fetch(self, _query: str) -> list[dict[str, object]]:
        return list(self.rows.values())

    async def close(self) -> None:
        return None


class WorkflowHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        credential_path = Path(self.directory.name) / "password"
        credential_path.write_text("placeholder\n", encoding="utf-8")
        self.environment = patch.dict(os.environ, {"DCIM_AUTH_REQUIRED": "false", "PGPASSWORD_FILE": str(credential_path)}, clear=True)
        self.environment.start()
        self.pool = FakePool()

    def tearDown(self) -> None:
        self.environment.stop()
        self.directory.cleanup()

    async def pool_factory(self, configuration: DatabaseConfiguration) -> FakePool:
        self.assertEqual("dcim_workflow_rw", configuration.user)
        return self.pool

    def test_draft_lifecycle_ends_in_approved_simulation(self) -> None:
        app = create_app(pool_factory=self.pool_factory)
        with TestClient(app) as client:
            created = client.post("/api/v1/workflows/drafts", json={"draft_type": "approval_request", "context": {"priority": "P1"}})
            listed = client.get("/api/v1/workflows/drafts")
            draft_id = created.json()["draft_id"]
            fetched = client.get(f"/api/v1/workflows/drafts/{draft_id}")
            simulated = client.post(f"/api/v1/workflows/drafts/{draft_id}/simulate", json={"decision": "approve"})

        self.assertEqual(201, created.status_code)
        self.assertEqual(1, len(created.json()["audit"]))
        self.assertEqual([created.json()], listed.json())
        self.assertEqual(created.json(), fetched.json())
        self.assertEqual("simulated_approved", simulated.json()["status"])
        self.assertEqual(2, len(simulated.json()["audit"]))

    def test_invalid_decision_returns_422(self) -> None:
        app = create_app(pool_factory=self.pool_factory)
        with TestClient(app) as client:
            created = client.post("/api/v1/workflows/drafts", json={"draft_type": "notification", "context": {}})
            response = client.post(f"/api/v1/workflows/drafts/{created.json()['draft_id']}/simulate", json={"decision": "execute"})
        self.assertEqual(422, response.status_code)

    def test_terminal_draft_cannot_be_resimulated(self) -> None:
        app = create_app(pool_factory=self.pool_factory)
        with TestClient(app) as client:
            created = client.post("/api/v1/workflows/drafts", json={"draft_type": "ticket_draft", "context": {}})
            url = f"/api/v1/workflows/drafts/{created.json()['draft_id']}/simulate"
            first = client.post(url, json={"decision": "reject"})
            second = client.post(url, json={"decision": "approve"})
        self.assertEqual(200, first.status_code)
        self.assertEqual(409, second.status_code)

    def test_missing_or_wrong_token_is_forbidden(self) -> None:
        auth_path = Path(self.directory.name) / "token"
        auth_path.write_text("placeholder\n", encoding="utf-8")
        self.environment.stop()
        self.environment = patch.dict(os.environ, {"DCIM_AUTH_REQUIRED": "true", "INTERNAL_API_TOKEN_FILE": str(auth_path), "PGPASSWORD_FILE": str(Path(self.directory.name) / "password")}, clear=True)
        self.environment.start()
        app = create_app(pool_factory=self.pool_factory)
        with TestClient(app) as client:
            missing = client.get("/api/v1/workflows/drafts")
            wrong = client.get("/api/v1/workflows/drafts", headers={"X-Internal-Token": "wrong"})
            allowed = client.get("/api/v1/workflows/drafts", headers={"X-Internal-Token": "placeholder"})
        self.assertEqual(403, missing.status_code)
        self.assertEqual(403, wrong.status_code)
        self.assertEqual(200, allowed.status_code)


if __name__ == "__main__":
    unittest.main()
