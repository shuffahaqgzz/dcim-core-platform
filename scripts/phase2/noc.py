#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

# ─── How to run ───
# 1. Set DCIM_RUNTIME_ROOT to the protected synthetic runtime.
# 2. Run: python3 scripts/phase2/noc.py --run-id synthetic-run-001
# ──────────────────
"""Materialize and render the PostgreSQL-authoritative Phase 2 NOC view."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html import escape
import json
import os
from pathlib import Path
import sys
from typing import Final


ROOT: Final = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.protected_runtime import (
    ensure_protected_directory,
    external_runtime_root,
    write_protected_text,
)

from scripts.phase2 import db


CARD_KIND: Final = "event"
OUTPUT_PARTS: Final = ("dev-build", "noc")


@dataclass(frozen=True, slots=True)
class NocError(RuntimeError):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class Card:
    run_id: str
    kind: str
    subject_key: str
    payload: db.JsonObject
    generated_at: str

    def to_json(self) -> db.JsonObject:
        return {
            "generated_at": self.generated_at,
            "kind": self.kind,
            "payload": self.payload,
            "run_id": self.run_id,
            "subject_key": self.subject_key,
        }


def _card_from_row(row: db.JsonObject) -> Card:
    expected = {"run_id", "kind", "subject_key", "payload", "generated_at"}
    if set(row) != expected:
        raise NocError("persisted NOC card has an invalid row shape")
    run_id = row["run_id"]
    kind = row["kind"]
    subject_key = row["subject_key"]
    payload = row["payload"]
    generated_at = row["generated_at"]
    if not isinstance(run_id, str):
        raise NocError("persisted NOC card has an invalid run_id")
    if not isinstance(kind, str):
        raise NocError("persisted NOC card has an invalid kind")
    if not isinstance(subject_key, str):
        raise NocError("persisted NOC card has an invalid subject_key")
    if not isinstance(payload, dict):
        raise NocError("persisted NOC card has an invalid payload")
    if not isinstance(generated_at, str):
        raise NocError("persisted NOC card has an invalid generated_at")
    return Card(run_id, kind, subject_key, payload, generated_at)


def _canonical_json(value: list[db.JsonObject]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _literal(value: str) -> str:
    if "\x00" in value:
        raise NocError("PostgreSQL text cannot contain NUL")
    return "'" + value.replace("'", "''") + "'"


def _materialize_sql(run_id: str) -> str:
    run = _literal(run_id)
    return f"""
\\set QUIET 1
BEGIN;
CREATE TEMP TABLE phase2_noc_desired (
    run_id text NOT NULL,
    kind text NOT NULL,
    subject_key text NOT NULL,
    payload jsonb NOT NULL,
    generated_at timestamptz NOT NULL,
    PRIMARY KEY (run_id, kind, subject_key)
) ON COMMIT DROP;
INSERT INTO phase2_noc_desired
    (run_id, kind, subject_key, payload, generated_at)
SELECT event.run_id, '{CARD_KIND}', event.event_id::text,
    jsonb_build_object(
        'asset', CASE WHEN asset.asset_id IS NULL THEN 'null'::jsonb
            ELSE jsonb_build_object(
                'asset_id', asset.asset_id::text,
                'asset_type', asset.asset_type,
                'identity', asset.identity
            ) END,
        'ci', CASE WHEN ci.ci_id IS NULL THEN 'null'::jsonb
            ELSE jsonb_build_object(
                'ci_id', ci.ci_id::text,
                'ci_type', ci.ci_type,
                'identity', ci.source_system || ':' || ci.native_device_id
            ) END,
        'dispositions', jsonb_build_object(
            'accepted', disposition.accepted,
            'duplicate', disposition.duplicate,
            'quarantined', disposition.quarantined
        ),
        'envelope', event.envelope
    ),
    manifest.fixed_clock
FROM phase2.events AS event
JOIN phase2.run_manifests AS manifest ON manifest.run_id = event.run_id
LEFT JOIN LATERAL (
    SELECT candidate.ci_id, candidate.asset_id, candidate.source_system,
        candidate.native_device_id, candidate.ci_type
    FROM phase2.cis AS candidate
    WHERE candidate.source_system || ':' || candidate.native_device_id
        = event.envelope #>> '{{enrichment,ci_identity}}'
    ORDER BY candidate.ci_id
    LIMIT 1
) AS ci ON true
LEFT JOIN phase2.assets AS asset ON asset.asset_id = ci.asset_id
LEFT JOIN LATERAL (
    SELECT
        count(*) FILTER (WHERE ordered.status = 'accepted') AS accepted,
        count(*) FILTER (WHERE ordered.status = 'duplicate') AS duplicate,
        count(*) FILTER (WHERE ordered.status = 'quarantined') AS quarantined
    FROM (
        SELECT source.status
        FROM phase2.dispositions AS source
        WHERE source.run_id = event.run_id
          AND source.event_id = event.event_id
        ORDER BY source.disposition_id
    ) AS ordered
) AS disposition ON true
WHERE event.run_id = {run}
ORDER BY event.event_id;
INSERT INTO phase2.noc_cards
    (run_id, kind, subject_key, payload, generated_at)
SELECT run_id, kind, subject_key, payload, generated_at
FROM phase2_noc_desired
ORDER BY kind, subject_key
ON CONFLICT (run_id, kind, subject_key) DO UPDATE
SET payload = EXCLUDED.payload, generated_at = EXCLUDED.generated_at;
DELETE FROM phase2.noc_cards AS stored
WHERE stored.run_id = {run}
  AND NOT EXISTS (
      SELECT 1
      FROM phase2_noc_desired AS desired
      WHERE desired.run_id = stored.run_id
        AND desired.kind = stored.kind
        AND desired.subject_key = stored.subject_key
  );
SELECT (count(*) = 0) AS stale_free
FROM phase2.noc_cards AS stored
WHERE stored.run_id = {run}
  AND NOT EXISTS (
      SELECT 1
      FROM phase2_noc_desired AS desired
      WHERE desired.run_id = stored.run_id
        AND desired.kind = stored.kind
        AND desired.subject_key = stored.subject_key
  ) \\gset
\\if :stale_free
SELECT row_to_json(card)::text
FROM (
    SELECT run_id, kind, subject_key, payload, generated_at
    FROM phase2.noc_cards
    WHERE run_id = {run}
    ORDER BY kind, subject_key
) AS card
ORDER BY card.kind, card.subject_key;
COMMIT;
\\else
ROLLBACK;
SELECT 1 / 0;
\\endif
"""


def materialize(run_id: str) -> list[Card]:
    """Reconcile one run's persisted cards in exactly one transaction."""
    return [_card_from_row(row) for row in db.parse_json_rows(db.psql(_materialize_sql(run_id)))]


def _read_cards(run_id: str) -> list[Card]:
    rows = db.query_json(
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
    return [_card_from_row(row) for row in rows]


def render(run_id: str) -> tuple[Path, Path]:
    """Render files from ordered persisted cards and no other data source."""
    cards = [card.to_json() for card in _read_cards(run_id)]
    canonical = _canonical_json(cards)
    html = (
        "<!doctype html>\n<meta charset=\"utf-8\">\n"
        "<title>DCIM synthetic NOC</title>\n"
        "<style>body{font-family:monospace;margin:2rem}pre{white-space:pre-wrap}</style>\n"
        f"<main><h1>DCIM synthetic NOC</h1><pre id=\"cards\">{escape(canonical)}</pre></main>\n"
    )
    raw_root = os.environ.get("DCIM_RUNTIME_ROOT")
    if not raw_root:
        raise NocError("DCIM_RUNTIME_ROOT is required")
    root = external_runtime_root(Path(raw_root))
    ensure_protected_directory(root, *OUTPUT_PARTS)
    cards_path = write_protected_text(root, (*OUTPUT_PARTS, "cards.json"), canonical + "\n")
    html_path = write_protected_text(root, (*OUTPUT_PARTS, "index.html"), html)
    return cards_path, html_path


def generate(run_id: str) -> tuple[Path, Path]:
    materialize(run_id)
    return render(run_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--render-only", action="store_true", help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)
    try:
        paths = render(arguments.run_id) if arguments.render_only else generate(arguments.run_id)
    except (db.DatabaseCommandError, db.JsonExtractionError, NocError, OSError, ValueError) as error:
        print(f"NOC generation failed: {error}", file=sys.stderr)
        return 1
    print(_canonical_json([{"cards": str(paths[0]), "html": str(paths[1])}]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
