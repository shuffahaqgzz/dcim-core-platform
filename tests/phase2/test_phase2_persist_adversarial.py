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
from scripts.phase2.migrate import MIGRATION_ID, MigrationError, apply, rollback
from scripts.phase2.run import run


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "fixtures/synthetic/events/p1-redfish-health.json"
CLOCK = "2026-07-29T00:00:00Z"


class AdversarialPersistenceTests(unittest.TestCase):
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
        try:
            rollback(MIGRATION_ID)
        except MigrationError as error:
            if str(error) != "migration is not applied":
                raise
        self.assertEqual(2, apply())

    def test_same_manifest_conflict_mutates_only_dispositions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixtures = Path(raw)
            original = json.loads(SOURCE.read_text(encoding="utf-8"))
            expected = json.loads(SOURCE.read_text(encoding="utf-8"))
            expected["observed_at"] = CLOCK
            expected["source"] = {
                "system": "redfish-synthetic",
                "instance": original["source"]["instance"],
                "connector": "redfish-fixture-adapter",
                "transport": "redfish",
                "native_event_id": original["source"]["native_event_id"],
            }
            expected_wire = json.dumps(
                expected,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode()
            expected_hash = hashlib.sha256(expected_wire).hexdigest()
            changed = json.loads(SOURCE.read_text(encoding="utf-8"))
            changed["payload"]["health"] = "Critical"
            changed["enrichment"]["asset_identity"] = "malformed"
            changed["enrichment"]["ci_identity"] = "malformed"
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
                        "same-manifest-conflict",
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
    'run_manifests', (SELECT count(*) FROM phase2.run_manifests),
    'dispositions', (SELECT count(*) FROM phase2.dispositions),
    'conflicts', (SELECT count(*) FROM phase2.dispositions
        WHERE reason = 'event_id_content_conflict'),
    'stored_envelope', (SELECT envelope FROM phase2.events),
    'stored_hash', (SELECT content_sha256 FROM phase2.events)
)::text;
"""
            )

        self.assertEqual(0, result)
        summary = json.loads(output.getvalue())
        self.assertEqual(1, summary["counts"]["accepted"])
        self.assertEqual(1, summary["counts"]["quarantined"])
        self.assertEqual(1, durable[0]["events"])
        self.assertEqual(1, durable[0]["assets"])
        self.assertEqual(1, durable[0]["cis"])
        self.assertEqual(1, durable[0]["aliases"])
        self.assertEqual(1, durable[0]["run_manifests"])
        self.assertEqual(2, durable[0]["dispositions"])
        self.assertEqual(1, durable[0]["conflicts"])
        self.assertEqual(expected, durable[0]["stored_envelope"])
        self.assertEqual(expected_hash, durable[0]["stored_hash"])

    def test_new_malformed_identity_commits_only_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixtures = Path(raw)
            candidate = json.loads(SOURCE.read_text(encoding="utf-8"))
            candidate["enrichment"]["asset_identity"] = "malformed"
            (fixtures / "01-invalid-identity.json").write_text(
                json.dumps(candidate), encoding="utf-8"
            )
            output = io.StringIO()
            with redirect_stdout(output):
                result = run(
                    [
                        "--run-id",
                        "new-malformed-identity",
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
    'reason', min(reason)
)::text
FROM phase2.dispositions;
"""
            )

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
                "reason": "identity_conflict",
            },
            durable[0],
        )

    def test_malformed_json_commits_one_null_event_quarantine(self) -> None:
        self._assert_json_boundary_quarantine(
            fixture_text='{"event_id":"not-finished"',
            expected_detail="json_syntax_error:fixture is not valid JSON",
            run_id="malformed-json",
        )

    def test_non_object_json_commits_one_null_event_quarantine(self) -> None:
        self._assert_json_boundary_quarantine(
            fixture_text='["not", "an", "object"]',
            expected_detail="json_root_not_object:fixture root must be a JSON object",
            run_id="non-object-json",
        )

    def _assert_json_boundary_quarantine(
        self,
        fixture_text: str,
        expected_detail: str,
        run_id: str,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixtures = Path(raw)
            (fixtures / "01-invalid.json").write_text(
                fixture_text, encoding="utf-8"
            )
            output = io.StringIO()
            with redirect_stdout(output):
                result = run(
                    [
                        "--run-id",
                        run_id,
                        "--fixtures-dir",
                        str(fixtures),
                        "--fixed-clock",
                        CLOCK,
                    ]
                )
            durable = db.query_json(
                f"""
SELECT json_build_object(
    'manifest_count', (SELECT count(*) FROM phase2.run_manifests
        WHERE run_id = '{run_id}'),
    'event_count', (SELECT count(*) FROM phase2.events),
    'disposition_count', count(*),
    'event_id_is_null', bool_and(event_id IS NULL),
    'reason', min(reason),
    'raw_id', min(lineage->>'raw_rejected_identifier'),
    'detail', min(lineage->>'validation_detail')
)::text
FROM phase2.dispositions
WHERE run_id = '{run_id}';
"""
            )

        self.assertEqual(0, result)
        self.assertEqual(
            {"received": 1, "accepted": 0, "quarantined": 1, "duplicate": 0},
            json.loads(output.getvalue())["counts"],
        )
        self.assertEqual(
            {
                "manifest_count": 1,
                "event_count": 0,
                "disposition_count": 1,
                "event_id_is_null": True,
                "reason": "schema_invalid",
                "raw_id": None,
                "detail": expected_detail,
            },
            durable[0],
        )


if __name__ == "__main__":
    unittest.main()
