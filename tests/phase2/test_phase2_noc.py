from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from scripts.phase2 import db, noc


CLOCK = "2026-07-29T12:34:56Z"


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _json_literal(value: db.JsonObject) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return f"{_literal(canonical)}::jsonb"


def _default_runtime_root() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home) if state_home else Path.home() / ".local/state"
    return base / "dcim-core-platform/runtime"


def _persisted(run_id: str) -> list[db.JsonObject]:
    return db.query_json(
        f"""
SELECT row_to_json(card)::text
FROM (
    SELECT run_id, kind, subject_key, payload, generated_at
    FROM phase2.noc_cards
    WHERE run_id = {_literal(run_id)}
    ORDER BY kind, subject_key
) AS card
ORDER BY card.kind, card.subject_key;
"""
    )


class NocPostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("DCIM_RUNTIME_ROOT", str(_default_runtime_root()))
        os.environ.setdefault("COMPOSE_PROJECT_NAME", "dcim-build")
        try:
            probe = db.query_json(
                "SELECT json_build_object('schema', "
                "to_regclass('phase2.noc_cards') IS NOT NULL)::text;"
            )
        except db.DatabaseCommandError as error:
            raise unittest.SkipTest(f"Compose PostgreSQL unavailable: {error}") from error
        if probe != [{"schema": True}]:
            raise unittest.SkipTest("Phase 2 schema is unavailable")

    def setUp(self) -> None:
        unique_suffix = uuid.uuid4().hex
        self.run_id = f"noc-test-{unique_suffix}"
        self.cross_run_id = f"{self.run_id}-other"
        self.source_system = f"synthetic-noc-{self.run_id}"
        self.native_device_id = f"device-{self.run_id}"
        self.ci_identity = f"{self.source_system}:{self.native_device_id}"
        self.event_ids = (
            str(uuid.uuid4()),
            str(uuid.uuid4()),
        )
        self.asset_id = str(uuid.uuid4())
        self.ci_id = str(uuid.uuid4())
        self.temporary = tempfile.TemporaryDirectory()
        self.output_root = Path(self.temporary.name)
        self.render_root = patch.object(noc, "external_runtime_root", return_value=self.output_root)
        self.render_root.start()
        self._seed()

    def tearDown(self) -> None:
        try:
            db.psql(
                f"""
BEGIN;
DELETE FROM phase2.noc_cards WHERE run_id = {_literal(self.run_id)};
DELETE FROM phase2.dispositions WHERE run_id IN ({_literal(self.run_id)}, {_literal(self.cross_run_id)});
DELETE FROM phase2.events WHERE run_id = {_literal(self.run_id)};
DELETE FROM phase2.cis WHERE ci_id = {_literal(self.ci_id)}::uuid;
DELETE FROM phase2.assets WHERE asset_id = {_literal(self.asset_id)}::uuid;
DELETE FROM phase2.run_manifests WHERE run_id = {_literal(self.cross_run_id)};
DELETE FROM phase2.run_manifests WHERE run_id = {_literal(self.run_id)};
COMMIT;
"""
            )
        finally:
            self.render_root.stop()
            self.temporary.cleanup()

    def _envelope(self, event_id: str, ci_identity: str | None) -> db.JsonObject:
        enrichment: db.JsonObject = {
            "validation_status": "accepted",
            "lineage": [{"at": CLOCK, "result": "accepted", "step": "synthetic-test"}],
            "quality_flags": [],
        }
        if ci_identity is not None:
            enrichment["ci_identity"] = ci_identity
        return {
            "correlation_id": str(uuid.uuid5(uuid.NAMESPACE_URL, event_id)),
            "enrichment": enrichment,
            "event_id": event_id,
            "event_type": "server.health.degraded",
            "observed_at": CLOCK,
            "occurred_at": CLOCK,
            "payload": {"component": "SyntheticUnit", "health": "Warning", "message": "Synthetic"},
            "priority": "P1",
            "schema_version": "0.1.0",
            "source": {
                "connector": "synthetic-test",
                "instance": "noc-test.example.invalid",
                "native_event_id": event_id,
                "system": "synthetic-noc",
                "transport": "fixture",
            },
        }

    def _seed(self) -> None:
        identity: db.JsonObject = {
            "manufacturer": "Example",
            "serial_number": self.run_id,
        }
        first = self._envelope(self.event_ids[0], self.ci_identity)
        second = self._envelope(self.event_ids[1], None)
        db.psql(
            f"""
BEGIN;
INSERT INTO phase2.run_manifests
    (run_id, fixed_clock, source_count, manifest_sha256, created_at)
VALUES ({_literal(self.run_id)}, {_literal(CLOCK)}::timestamptz, 2,
    'synthetic-manifest', {_literal(CLOCK)}::timestamptz);
INSERT INTO phase2.run_manifests
    (run_id, fixed_clock, source_count, manifest_sha256, created_at)
VALUES ({_literal(self.cross_run_id)}, {_literal(CLOCK)}::timestamptz, 0,
    'synthetic-other-manifest', {_literal(CLOCK)}::timestamptz);
INSERT INTO phase2.assets
    (asset_id, identity, asset_type, created_at, updated_at)
VALUES ({_literal(self.asset_id)}::uuid, {_json_literal(identity)},
    'synthetic-device', {_literal(CLOCK)}::timestamptz, {_literal(CLOCK)}::timestamptz);
INSERT INTO phase2.cis
    (ci_id, asset_id, source_system, native_device_id, ci_type, created_at, updated_at)
VALUES ({_literal(self.ci_id)}::uuid, {_literal(self.asset_id)}::uuid,
    {_literal(self.source_system)}, {_literal(self.native_device_id)}, 'synthetic-ci',
    {_literal(CLOCK)}::timestamptz, {_literal(CLOCK)}::timestamptz);
INSERT INTO phase2.events
    (event_id, run_id, envelope, content_sha256, ingested_at)
VALUES
    ({_literal(self.event_ids[0])}::uuid, {_literal(self.run_id)}, {_json_literal(first)},
        'synthetic-first', {_literal(CLOCK)}::timestamptz),
    ({_literal(self.event_ids[1])}::uuid, {_literal(self.run_id)}, {_json_literal(second)},
        'synthetic-second', {_literal(CLOCK)}::timestamptz);
INSERT INTO phase2.dispositions
    (event_id, run_id, status, reason, lineage, decided_at)
VALUES
    ({_literal(self.event_ids[0])}::uuid, {_literal(self.run_id)}, 'accepted', NULL, '{{}}', {_literal(CLOCK)}),
    ({_literal(self.event_ids[0])}::uuid, {_literal(self.run_id)}, 'duplicate', NULL, '{{}}', {_literal(CLOCK)}),
    ({_literal(self.event_ids[0])}::uuid, {_literal(self.run_id)}, 'duplicate', NULL, '{{}}', {_literal(CLOCK)}),
    ({_literal(self.event_ids[0])}::uuid, {_literal(self.run_id)}, 'quarantined', 'synthetic', '{{}}', {_literal(CLOCK)}),
    ({_literal(self.event_ids[1])}::uuid, {_literal(self.run_id)}, 'accepted', NULL, '{{}}', {_literal(CLOCK)}),
    ({_literal(self.event_ids[0])}::uuid, {_literal(self.cross_run_id)}, 'duplicate', NULL, '{{}}', {_literal(CLOCK)});
COMMIT;
"""
        )

    def test_two_generations_are_semantically_and_byte_identical(self) -> None:
        first_paths = noc.generate(self.run_id)
        self.assertTrue(all(path.is_relative_to(self.output_root) for path in first_paths))
        first_rows = _persisted(self.run_id)
        first_files = tuple(path.read_bytes() for path in first_paths)

        second_paths = noc.generate(self.run_id)
        second_rows = _persisted(self.run_id)
        second_files = tuple(path.read_bytes() for path in second_paths)

        self.assertEqual(first_rows, second_rows)
        self.assertEqual(2, len(second_rows))
        self.assertEqual(first_files, second_files)
        by_subject = {row["subject_key"]: row for row in second_rows}
        first_payload = by_subject[self.event_ids[0]]["payload"]
        second_payload = by_subject[self.event_ids[1]]["payload"]
        self.assertEqual(
            {"accepted": 1, "duplicate": 2, "quarantined": 1},
            first_payload["dispositions"],
        )
        self.assertIsNotNone(first_payload["asset"])
        self.assertIsNotNone(first_payload["ci"])
        self.assertIsNone(second_payload["asset"])
        self.assertIsNone(second_payload["ci"])
        clock_match = db.query_json(
            f"""
SELECT json_build_object(
    'matches', bool_and(card.generated_at = manifest.fixed_clock)
)::text
FROM phase2.noc_cards AS card
JOIN phase2.run_manifests AS manifest ON manifest.run_id = card.run_id
WHERE card.run_id = {_literal(self.run_id)}
ORDER BY bool_and(card.generated_at = manifest.fixed_clock);
"""
        )
        self.assertEqual([{"matches": True}], clock_match)

    def test_jsonb_key_order_shuffle_is_byte_identical(self) -> None:
        paths = noc.generate(self.run_id)
        before = tuple(path.read_bytes() for path in paths)
        envelope = self._envelope(self.event_ids[0], self.ci_identity)
        shuffled = json.dumps(dict(reversed(list(envelope.items()))), separators=(",", ":"))

        db.psql(
            f"UPDATE phase2.events SET envelope = {_literal(shuffled)}::jsonb "
            f"WHERE event_id = {_literal(self.event_ids[0])}::uuid;"
        )
        noc.generate(self.run_id)

        self.assertEqual(before, tuple(path.read_bytes() for path in paths))

    def test_render_only_uses_persisted_rows_and_overwrites_file_tamper(self) -> None:
        noc.generate(self.run_id)
        db.psql(
            "UPDATE phase2.noc_cards SET payload = "
            "jsonb_build_object('tampered_in_postgres', true) "
            f"WHERE run_id = {_literal(self.run_id)} "
            f"AND subject_key = {_literal(self.event_ids[0])};"
        )

        cards_path, _ = noc.render(self.run_id)
        expected = _persisted(self.run_id)
        authoritative = cards_path.read_bytes()
        self.assertEqual(expected, json.loads(authoritative))
        cards_path.write_text('[{"tampered_file":true}]\n', encoding="utf-8")
        noc.render(self.run_id)

        self.assertEqual(authoritative, cards_path.read_bytes())

    def test_deleted_source_removes_stale_persisted_and_rendered_card(self) -> None:
        noc.generate(self.run_id)

        db.psql(
            "DELETE FROM phase2.events "
            f"WHERE event_id = {_literal(self.event_ids[1])}::uuid;"
        )
        cards_path, _ = noc.generate(self.run_id)

        persisted = _persisted(self.run_id)
        self.assertEqual([self.event_ids[0]], [row["subject_key"] for row in persisted])
        self.assertEqual(persisted, json.loads(cards_path.read_bytes()))


class NocUnavailableTests(unittest.TestCase):
    def test_missing_postgres_returns_nonzero_without_using_stale_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            stale = root / "dev-build/noc/cards.json"
            stale.parent.mkdir(parents=True)
            stale.write_text('[{"stale":true}]\n', encoding="utf-8")
            before = stale.read_bytes()
            with (
                patch.dict(os.environ, {"DCIM_RUNTIME_ROOT": raw}, clear=True),
                patch.object(db, "psql", side_effect=db.DatabaseCommandError("unavailable")),
            ):
                result = noc.main(["--run-id", "synthetic-missing-postgres"])
            after = stale.read_bytes()

        self.assertEqual(1, result)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
