from __future__ import annotations

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/cmdb/src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))


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


class CmdbIdentityTests(unittest.TestCase):
    def test_ci_id_when_native_identity_replayed_is_deterministic(self) -> None:
        from scripts.phase2.identity import derive_ci_id

        self.assertEqual(UUID("ec059315-8c4d-57a0-a4d0-77a1a71bd7e9"), derive_ci_id("synthetic", "device-1"))
