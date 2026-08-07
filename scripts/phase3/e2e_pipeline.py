from __future__ import annotations

import json
from pathlib import Path
import sys

from scripts.phase2 import db, stream
from scripts.phase3.e2e_support import E2EFailure, E2EState, ROOT, integer, parse_object


NORMALIZED_TOPIC = "dcim.normalized.events"


def fixture_rows(state: E2EState) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(state.config.fixtures_dir.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise E2EFailure("synthetic fixture inventory is invalid") from error
        if not isinstance(value, dict):
            raise E2EFailure("synthetic fixture inventory is invalid")
        rows.append(value)
    if not rows:
        raise E2EFailure("synthetic fixture inventory is empty")
    return rows


def _work_dir(state: E2EState) -> Path:
    if state.work_dir is None:
        state.work_dir = state.config.output.parent / f"work-{state.run_id}"
        state.work_dir.mkdir(parents=True, exist_ok=True)
    return state.work_dir


def produce(state: E2EState) -> None:
    state.stream_started = True
    work_dir = _work_dir(state)
    try:
        starts = stream.capture_end_offsets(NORMALIZED_TOPIC)
    except Exception as error:
        raise E2EFailure("Kafka watermark capture failed") from error
    offsets_path = work_dir / "start-offsets.json"
    offsets_path.write_text(json.dumps(starts, sort_keys=True) + "\n", encoding="utf-8")
    state.start_offsets = offsets_path
    state.temporary_files.append(offsets_path)
    result = _run(
        [
            sys.executable,
            str(ROOT / "scripts/phase2/run.py"),
            "--mode",
            "stream",
            "--run-id",
            state.run_id,
            "--fixtures-dir",
            str(state.config.fixtures_dir),
            "--fixed-clock",
            state.config.fixed_clock,
        ],
        "stream producer",
    )
    if result.returncode != 0:
        raise E2EFailure("stream producer failed")
    summary = parse_object(result.stdout, "stream producer")
    received = integer(summary.get("received"), "producer")
    published = integer(summary.get("published"), "producer")
    dlq = integer(summary.get("dlq"), "producer")
    if received != published + dlq or published < 1:
        raise E2EFailure("producer ledger is unbalanced")
    state.producer_ledger = {"received": received, "published": published, "dlq": dlq}


def drain(state: E2EState) -> None:
    if state.start_offsets is None:
        raise E2EFailure("consumer start offsets are unavailable")
    result = _run(
        [
            sys.executable,
            str(ROOT / "scripts/phase2/stream.py"),
            "--run-id",
            state.run_id,
            "--group-id",
            f"dcim-phase3-e2e-{state.run_id}",
            "--start-offsets",
            str(state.start_offsets),
            "--max-messages",
            str(state.producer_ledger["published"]),
            "--idle-timeout-seconds",
            str(state.config.idle_timeout_seconds),
        ],
        "consumer drain",
    )
    if result.returncode != 0:
        raise E2EFailure("bounded consumer drain failed")
    summary = parse_object(result.stdout, "consumer drain")
    ledger = summary.get("ledger")
    if not isinstance(ledger, dict):
        raise E2EFailure("consumer ledger is unavailable")
    state.consumer_ledger = {
        key: integer(ledger.get(key), "consumer")
        for key in ("received", "accepted", "quarantined", "duplicate")
    }


def zero_loss(state: E2EState) -> None:
    producer = state.producer_ledger
    consumer = state.consumer_ledger
    published = producer["published"]
    if consumer["received"] != published:
        raise E2EFailure("producer and consumer received counts differ")
    if consumer["received"] != sum(consumer[key] for key in ("accepted", "quarantined", "duplicate")):
        raise E2EFailure("consumer ledger is unbalanced")
    run = db.literal(state.run_id)
    rows = db.query_json(
        "SELECT json_build_object("
        f"'events', (SELECT count(*) FROM phase2.events WHERE run_id = {run}),"
        f"'dispositions', (SELECT count(*) FROM phase2.dispositions WHERE run_id = {run}),"
        f"'accepted', (SELECT count(*) FROM phase2.dispositions WHERE run_id = {run} AND status = 'accepted'),"
        f"'quarantined', (SELECT count(*) FROM phase2.dispositions WHERE run_id = {run} AND status = 'quarantined'),"
        f"'duplicate', (SELECT count(*) FROM phase2.dispositions WHERE run_id = {run} AND status = 'duplicate')"
        ")::text;",
    )
    expected = {
        "events": published,
        "dispositions": consumer["received"],
        "accepted": consumer["accepted"],
        "quarantined": consumer["quarantined"],
        "duplicate": consumer["duplicate"],
    }
    if rows != [expected]:
        raise E2EFailure("durable event counts do not match both ledgers")
    state.database_counts = expected
    state.checks["zero_silent_loss"] = True
    state.checks["producer_consumer_counts_match"] = True


def _run(command: list[str], label: str):
    from scripts.phase3.e2e_support import _run_command

    return _run_command(command, label)
