from __future__ import annotations

import os
from pathlib import Path
import unittest

from scripts.phase2 import db, migrate


class PostgreSqlMigrationRollbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        state_home = os.environ.get("XDG_STATE_HOME")
        default_root = (
            Path(state_home) if state_home else Path.home() / ".local/state"
        ) / "dcim-core-platform/runtime"
        os.environ.setdefault("DCIM_RUNTIME_ROOT", str(default_root))
        os.environ.setdefault("COMPOSE_PROJECT_NAME", "dcim-build")
        try:
            db.query_json("SELECT json_build_object('ready', true)::text;")
        except db.DatabaseCommandError as error:
            raise unittest.SkipTest(
                f"Compose PostgreSQL unavailable: {error}"
            ) from error
        migrate.apply(default_root / "dev-build/secrets")

    def test_rollback_when_schema_is_empty_reapplies_cleanly(self) -> None:
        rows = db.query_json(
            """
SELECT json_build_object(
    'run_manifests', (SELECT count(*) FROM phase2.run_manifests),
    'events', (SELECT count(*) FROM phase2.events),
    'dispositions', (SELECT count(*) FROM phase2.dispositions),
    'assets', (SELECT count(*) FROM phase2.assets),
    'cis', (SELECT count(*) FROM phase2.cis),
    'aliases', (SELECT count(*) FROM phase2.aliases),
    'noc_cards', (SELECT count(*) FROM phase2.noc_cards)
)::text;
"""
        )
        empty = {
            "run_manifests": 0,
            "events": 0,
            "dispositions": 0,
            "assets": 0,
            "cis": 0,
            "aliases": 0,
            "noc_cards": 0,
        }
        if rows != [empty]:
            self.skipTest("shared Phase 2 data exists; destructive rollback not safe")

        migrate.rollback(migrate.MIGRATION_ID)
        applied = migrate.apply(Path(os.environ["DCIM_RUNTIME_ROOT"]) / "dev-build/secrets")

        self.assertEqual(3, applied)
        self.assertEqual(migrate.EXPECTED_TABLES, migrate.verify())


if __name__ == "__main__":
    unittest.main()
