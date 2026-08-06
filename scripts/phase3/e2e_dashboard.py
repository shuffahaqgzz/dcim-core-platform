from __future__ import annotations

import json
from collections.abc import Mapping

from scripts.phase2 import db, identity, noc
from scripts.phase3 import HttpClient, UrllibClient, inspect_address, read_token
from scripts.phase3.e2e_pipeline import fixture_rows
from scripts.phase3.e2e_support import E2EFailure, E2EState, integer


def _json_object(raw: bytes, context: str) -> dict[str, object]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise E2EFailure(f"{context} response is not valid JSON") from error
    if not isinstance(value, dict):
        raise E2EFailure(f"{context} response is not a JSON object")
    return value


def _gateway_upsert(
    client: HttpClient,
    base_url: str,
    internal_token: str,
    path: str,
    fallback: Mapping[str, object],
) -> dict[str, object]:
    status, body = client.request("GET", f"{base_url}{path}", internal_token=internal_token)
    if status == 200:
        payload = _json_object(body, "gateway lookup")
    elif status == 404:
        payload = dict(fallback)
    else:
        raise E2EFailure("gateway lookup failed")
    status, body = client.request(
        "POST",
        f"{base_url}{path.rsplit('/', 1)[0]}",
        internal_token=internal_token,
        payload=payload,
    )
    if status not in (200, 201):
        raise E2EFailure("gateway seed failed")
    return _json_object(body, "gateway seed")


def _seed(state: E2EState, client: HttpClient, base_url: str, internal_token: str) -> None:
    pairs: dict[tuple[str, str], None] = {}
    for row in fixture_rows(state):
        enrichment = row.get("enrichment")
        if not isinstance(enrichment, dict):
            raise E2EFailure("fixture identity enrichment is unavailable")
        asset_text = enrichment.get("asset_identity")
        ci_text = enrichment.get("ci_identity")
        if not isinstance(asset_text, str) or not isinstance(ci_text, str):
            raise E2EFailure("fixture identity enrichment is invalid")
        pairs[(asset_text, ci_text)] = None
    for asset_text, ci_text in sorted(pairs):
        manufacturer, separator, serial = asset_text.partition(":")
        source_system, ci_separator, native_device_id = ci_text.partition(":")
        if not separator or not ci_separator:
            raise E2EFailure("fixture identity enrichment is invalid")
        asset_identity = {"manufacturer": manufacturer, "serial_number": serial}
        asset_id = str(identity.derive_asset_id(asset_identity))
        asset = _gateway_upsert(
            client,
            base_url,
            internal_token,
            f"/api/v1/assets/{asset_id}",
            {
                "asset_id": asset_id,
                "identity": asset_identity,
                "asset_type": "synthetic-device",
                "aliases": [],
                "created_at": state.config.fixed_clock,
                "updated_at": state.config.fixed_clock,
            },
        )
        ci_id = str(identity.derive_ci_id(source_system, native_device_id))
        _ = _gateway_upsert(
            client,
            base_url,
            internal_token,
            f"/api/v1/cis/{ci_id}",
            {
                "ci_id": ci_id,
                "source_system": source_system,
                "native_device_id": native_device_id,
                "ci_type": "synthetic-ci",
                "aliases": [],
                "asset_id": asset.get("asset_id", asset_id),
                "created_at": state.config.fixed_clock,
                "updated_at": state.config.fixed_clock,
            },
        )


def dashboard(state: E2EState) -> None:
    rows = fixture_rows(state)
    baseline_rows = db.query_json(
        "SELECT row_to_json(result)::text FROM ("
        "SELECT count(*) AS count FROM phase2.noc_cards "
        "WHERE payload #>> '{envelope,priority}' = 'P1'"
        ") AS result;",
    )
    if len(baseline_rows) != 1:
        raise E2EFailure("dashboard baseline count is unavailable")
    baseline = integer(baseline_rows[0].get("count"), "dashboard baseline")
    state.dashboard["baseline_p1"] = baseline
    try:
        address = inspect_address("api")
        internal_token = read_token(state.config.token_file)
    except Exception as error:
        raise E2EFailure("gateway configuration is unavailable") from error
    client = UrllibClient()
    base_url = f"http://{address}:8000"
    _seed(state, client, base_url, internal_token)
    try:
        noc.generate(state.run_id)
    except Exception as error:
        raise E2EFailure("NOC materialization failed") from error
    status, body = client.request(
        "GET",
        f"{base_url}/api/v1/dashboard/noc-cards?priority=P1",
        internal_token=internal_token,
    )
    if status != 200:
        raise E2EFailure("dashboard P1 assertion request failed")
    try:
        cards = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise E2EFailure("dashboard P1 response is invalid") from error
    if not isinstance(cards, list):
        raise E2EFailure("dashboard P1 response is invalid")
    expected_ids = {str(row.get("event_id")) for row in rows if row.get("priority") == "P1"}
    visible_ids: set[str] = set()
    for card in cards:
        if not isinstance(card, dict) or card.get("run_id") != state.run_id:
            continue
        payload = card.get("payload")
        envelope = payload.get("envelope") if isinstance(payload, dict) else None
        event_id = envelope.get("event_id") if isinstance(envelope, dict) else None
        if isinstance(event_id, str):
            visible_ids.add(event_id)
    visible_count = len(expected_ids & visible_ids)
    if visible_count != len(expected_ids):
        raise E2EFailure("dashboard did not expose every expected P1 event")
    status, body = client.request(
        "GET", f"{base_url}/api/v1/dashboard/summary", internal_token=internal_token,
    )
    if status != 200:
        raise E2EFailure("dashboard summary assertion request failed")
    summary = _json_object(body, "dashboard summary")
    counts = summary.get("noc_cards")
    if not isinstance(counts, dict):
        raise E2EFailure("dashboard summary counts are unavailable")
    summary_p1 = integer(counts.get("P1"), "dashboard summary")
    expected_summary = baseline + len(expected_ids)
    if summary_p1 != expected_summary:
        raise E2EFailure("dashboard summary P1 count is incorrect")
    state.dashboard.update({"p1_visible": visible_count, "summary_p1": summary_p1, "expected_p1": expected_summary})
    state.checks["dashboard_visibility"] = True
