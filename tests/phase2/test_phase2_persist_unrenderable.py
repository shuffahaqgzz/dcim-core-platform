from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from scripts.phase2 import db
from scripts.phase2.db import DatabaseCommandError
from scripts.phase2.identity_sql import (
    IdentityRejected,
    PreparedIdentity,
    prepare_identity,
    render_identity_dml,
)
from scripts.phase2.migrate import MIGRATION_ID, MigrationError, apply, rollback
from scripts.phase2.run import run


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "fixtures/synthetic/events/p1-redfish-health.json"
CLOCK = "2026-07-29T00:00:00Z"


class UnrenderableIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        state_home = os.environ.get("XDG_STATE_HOME")
        runtime = (
            Path(state_home) if state_home else Path.home() / ".local/state"
        ) / "dcim-core-platform/runtime"
        os.environ.setdefault("DCIM_RUNTIME_ROOT", str(runtime))
        os.environ.setdefault("COMPOSE_PROJECT_NAME", "dcim-build")
        try:
            rows = db.query_json(
                "SELECT json_build_object('reachable', true)::text;"
            )
        except DatabaseCommandError as error:
            raise unittest.SkipTest(
                f"PostgreSQL integration unavailable: {error}"
            ) from error
        if rows != [{"reachable": True}]:
            raise unittest.SkipTest("PostgreSQL integration probe returned invalid data")

    def setUp(self) -> None:
        self._reset_schema()

    def test_nul_identity_conflicts_classify_from_hash_only(self) -> None:
        mutations = (
            ("asset", "enrichment", "asset_identity", "SyntheticVendor:SER\u0000"),
            ("ci", "enrichment", "ci_identity", "synthetic-system:device\u0000"),
            ("alias", "source", "instance", "synthetic-device\u0000"),
        )
        for label, section, field, value in mutations:
            with self.subTest(label=label):
                self._reset_schema()
                durable, summary = self._run_conflict(section, field, value)
                self.assertEqual(
                    {"received": 2, "accepted": 1, "quarantined": 1, "duplicate": 0},
                    summary["counts"],
                )
                self.assertEqual(1, durable["events"])
                self.assertEqual(1, durable["assets"])
                self.assertEqual(1, durable["cis"])
                self.assertEqual(1, durable["aliases"])
                self.assertEqual(1, durable["manifests"])
                self.assertEqual(2, durable["dispositions"])
                self.assertEqual(1, durable["conflicts"])
                self.assertEqual(durable["expected_hash"], durable["stored_hash"])

    def test_new_nul_identity_commits_only_identity_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixtures = Path(raw)
            candidate = json.loads(SOURCE.read_text(encoding="utf-8"))
            candidate["enrichment"]["ci_identity"] = "synthetic-system:device\u0000"
            (fixtures / "01-new-invalid.json").write_text(
                json.dumps(candidate), encoding="utf-8"
            )
            output = io.StringIO()
            with redirect_stdout(output):
                result = run(
                    [
                        "--run-id",
                        "new-nul-identity",
                        "--fixtures-dir",
                        str(fixtures),
                        "--fixed-clock",
                        CLOCK,
                    ]
                )
            durable = db.query_json(
                """
SELECT json_build_object(
    'events', (SELECT count(*) FROM phase2.events),
    'assets', (SELECT count(*) FROM phase2.assets),
    'cis', (SELECT count(*) FROM phase2.cis),
    'aliases', (SELECT count(*) FROM phase2.aliases),
    'manifests', (SELECT count(*) FROM phase2.run_manifests),
    'dispositions', count(*),
    'identity_conflicts', count(*) FILTER (WHERE reason = 'identity_conflict')
)::text FROM phase2.dispositions;
"""
            )[0]

        self.assertEqual(0, result)
        self.assertEqual(
            {"received": 1, "accepted": 0, "quarantined": 1, "duplicate": 0},
            json.loads(output.getvalue())["counts"],
        )
        self.assertEqual(
            {
                "events": 0,
                "assets": 0,
                "cis": 0,
                "aliases": 0,
                "manifests": 1,
                "dispositions": 1,
                "identity_conflicts": 1,
            },
            durable,
        )

    def test_identity_preparation_is_total_and_quoting_is_safe(self) -> None:
        candidate = json.loads(SOURCE.read_text(encoding="utf-8"))
        candidate["enrichment"]["asset_identity"] = "Véndor O'Brien:SER:EXTRA"
        candidate["enrichment"]["ci_identity"] = "Système:device:extra"
        candidate["source"]["instance"] = "host'o"
        prepared = prepare_identity(candidate, CLOCK)
        self.assertIsInstance(prepared, PreparedIdentity)
        if isinstance(prepared, PreparedIdentity):
            sql = render_identity_dml(prepared)
            self.assertIn("O''Brien", sql)
            self.assertIn("host''o", sql)
            self.assertIn("SER:EXTRA", sql)
            self.assertIn("device:extra", sql)

        rejected_values = (
            ("enrichment", "asset_identity", ":serial"),
            ("enrichment", "asset_identity", "vendor:"),
            ("enrichment", "ci_identity", ":device"),
            ("enrichment", "ci_identity", "system:"),
            ("enrichment", "asset_identity", "vendor:serial\u0000"),
            ("enrichment", "ci_identity", "system:device\u0000"),
            ("source", "instance", "host\u0000"),
            ("source", "instance", "host\ud800"),
        )
        for section, field, value in rejected_values:
            with self.subTest(section=section, field=field, value_length=len(value)):
                rejected = json.loads(SOURCE.read_text(encoding="utf-8"))
                rejected[section][field] = value
                self.assertIsInstance(
                    prepare_identity(rejected, CLOCK),
                    IdentityRejected,
                )
        missing_identity = json.loads(SOURCE.read_text(encoding="utf-8"))
        missing_identity["enrichment"].pop("asset_identity")
        missing_identity["enrichment"].pop("ci_identity")
        missing_identity["source"]["instance"] = "host\u0000"
        self.assertIsInstance(
            prepare_identity(missing_identity, CLOCK),
            IdentityRejected,
        )

    def _run_conflict(
        self,
        section: str,
        field: str,
        value: str,
    ) -> tuple[dict[str, int | str], dict[str, str | dict[str, int]]]:
        with tempfile.TemporaryDirectory() as raw:
            fixtures = Path(raw)
            original = json.loads(SOURCE.read_text(encoding="utf-8"))
            changed = json.loads(SOURCE.read_text(encoding="utf-8"))
            changed["payload"]["health"] = "Critical"
            changed[section][field] = value
            (fixtures / "01-original.json").write_text(
                json.dumps(original), encoding="utf-8"
            )
            (fixtures / "02-conflict.json").write_text(
                json.dumps(changed), encoding="utf-8"
            )
            output = io.StringIO()
            with redirect_stdout(output):
                result = run(
                    [
                        "--run-id",
                        f"nul-{section}-{field}",
                        "--fixtures-dir",
                        str(fixtures),
                        "--fixed-clock",
                        CLOCK,
                    ]
                )
            durable = db.query_json(
                """
SELECT json_build_object(
    'events', (SELECT count(*) FROM phase2.events),
    'assets', (SELECT count(*) FROM phase2.assets),
    'cis', (SELECT count(*) FROM phase2.cis),
    'aliases', (SELECT count(*) FROM phase2.aliases),
    'manifests', (SELECT count(*) FROM phase2.run_manifests),
    'dispositions', (SELECT count(*) FROM phase2.dispositions),
    'conflicts', (SELECT count(*) FROM phase2.dispositions
        WHERE reason = 'event_id_content_conflict'),
    'stored_hash', (SELECT content_sha256 FROM phase2.events)
)::text;
"""
            )[0]

        expected = json.loads(SOURCE.read_text(encoding="utf-8"))
        expected["observed_at"] = CLOCK
        expected["source"] = {
            "system": "redfish-synthetic",
            "instance": original["source"]["instance"],
            "connector": "redfish-fixture-adapter",
            "transport": "redfish",
            "native_event_id": original["source"]["native_event_id"],
        }
        wire = json.dumps(
            expected,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
        durable["expected_hash"] = hashlib.sha256(wire).hexdigest()
        self.assertEqual(0, result)
        return durable, json.loads(output.getvalue())

    def _reset_schema(self) -> None:
        try:
            rollback(MIGRATION_ID)
        except MigrationError as error:
            if str(error) != "migration is not applied":
                raise
        self.assertEqual(1, apply())


if __name__ == "__main__":
    unittest.main()
