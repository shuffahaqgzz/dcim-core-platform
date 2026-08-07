#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.9.2"]
# ///

# ─── How to run ───
# 1. Bootstrap and start the protected synthetic foundation.
# 2. Install the exact Phase 2 dependency with: make phase2-deps
# 3. Run: python3 scripts/phase2/check.py
# ─────────────────
"""Run the sequential synthetic Phase 2 acceptance gate."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Final, override, TypeAlias
import unittest


ROOT: Final = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase2 import capacity, db, migrate, noc, recovery  # noqa: E402
from scripts.phase2.errors import Phase2Error  # noqa: E402


FIXTURES_DIR: Final = ROOT / "fixtures/synthetic/events"
FIXED_CLOCK: Final = "2026-07-30T00:00:00Z"
SHORT_COMMIT_LENGTH: Final = 12
COMMIT_PATTERN: Final = re.compile(r"[0-9a-f]{40}\Z")
AUTHORITATIVE_TABLES: Final = ("events", "assets", "cis", "aliases")
NORMALIZED_TOPIC: Final = "dcim.normalized.events"
DLQ_TOPIC: Final = "dcim.dlq.synthetic"

StageAction: TypeAlias = Callable[[str], None]
Stage: TypeAlias = tuple[str, StageAction]


@dataclass(frozen=True, slots=True)
class CheckError(RuntimeError):
    """One Phase 2 gate invariant failed."""

    reason: str

    @override
    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class StageFailure(RuntimeError):
    label: str
    reason: str

    @override
    def __str__(self) -> str:
        return f"{self.label}: FAIL: {self.reason}"


@dataclass(frozen=True, slots=True)
class ReplayBaseline:
    authoritative: tuple[str, ...]
    manifest: str
    dispositions: int
    sources: int


def _git_directories() -> tuple[Path, Path]:
    marker = ROOT / ".git"
    if marker.is_dir():
        return marker, marker
    try:
        prefix, raw_path = marker.read_text(encoding="utf-8").strip().split(": ", 1)
    except (OSError, ValueError) as error:
        raise CheckError("Git metadata is unavailable") from error
    if prefix != "gitdir":
        raise CheckError("Git worktree metadata is invalid")
    worktree_git = (ROOT / raw_path).resolve()
    common_marker = worktree_git / "commondir"
    try:
        common_git = (worktree_git / common_marker.read_text(encoding="utf-8").strip()).resolve()
    except OSError:
        common_git = worktree_git
    return worktree_git, common_git


def _packed_ref(common_git: Path, reference: str) -> str:
    try:
        lines = (common_git / "packed-refs").read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise CheckError("Git reference is unavailable") from error
    suffix = f" {reference}"
    for line in lines:
        if line.endswith(suffix):
            return line.split(" ", 1)[0]
    raise CheckError("Git reference is unavailable")


def short_commit() -> str:
    """Return the current 12-character commit identity without executing Git."""
    candidate = os.environ.get("GITHUB_SHA", "").lower()
    if not COMMIT_PATTERN.fullmatch(candidate):
        worktree_git, common_git = _git_directories()
        try:
            head = (worktree_git / "HEAD").read_text(encoding="utf-8").strip()
        except OSError as error:
            raise CheckError("Git HEAD is unavailable") from error
        if head.startswith("ref: "):
            reference = head.removeprefix("ref: ")
            try:
                candidate = (common_git / reference).read_text(encoding="utf-8").strip()
            except OSError:
                candidate = _packed_ref(common_git, reference)
        else:
            candidate = head
    if not COMMIT_PATTERN.fullmatch(candidate):
        raise CheckError("Git HEAD is not a full commit SHA")
    return candidate[:SHORT_COMMIT_LENGTH]


def pipeline_execute(run_id: str) -> db.JsonObject:
    """Run one batch through the Pydantic-backed pipeline module."""
    from scripts.phase2 import run as pipeline

    return pipeline.execute(run_id, FIXTURES_DIR, FIXED_CLOCK)


def authoritative_snapshot() -> tuple[str, ...]:
    """Return deterministic bytes for every authoritative Phase 2 table."""
    return tuple(
        db.psql(
            "SELECT coalesce(json_agg(row_to_json(item) "
            "ORDER BY row_to_json(item)::text), '[]'::json)::text "
            f'FROM phase2."{table}" AS item;'
        )
        for table in AUTHORITATIVE_TABLES
    )


def manifest_bytes(run_id: str) -> str:
    """Return byte-stable immutable manifest columns for one run."""
    return db.psql(
        "SELECT row_to_json(item)::text FROM (SELECT run_id, fixed_clock, "
        "source_count, manifest_sha256, created_at FROM phase2.run_manifests "
        f"WHERE run_id = {db.literal(run_id)}) AS item;"
    )


def _single_integer(sql: str, key: str) -> int:
    rows = db.query_json(sql)
    if len(rows) != 1:
        raise CheckError(f"{key} query returned unexpected rows")
    value = rows[0].get(key)
    if type(value) is not int:
        raise CheckError(f"{key} query returned an invalid value")
    return value


def disposition_count(run_id: str) -> int:
    return _single_integer(
        "SELECT json_build_object('dispositions', count(*))::text "
        f"FROM phase2.dispositions WHERE run_id = {db.literal(run_id)};",
        "dispositions",
    )


def source_count(run_id: str) -> int:
    return _single_integer(
        "SELECT json_build_object('sources', source_count)::text "
        f"FROM phase2.run_manifests WHERE run_id = {db.literal(run_id)};",
        "sources",
    )


def _baseline(run_id: str) -> ReplayBaseline:
    manifest = manifest_bytes(run_id)
    if not manifest:
        raise CheckError("manifest row is missing")
    return ReplayBaseline(
        authoritative_snapshot(),
        manifest,
        disposition_count(run_id),
        source_count(run_id),
    )


def _assert_duplicate_replay(summary: db.JsonObject, baseline: ReplayBaseline) -> None:
    counts = summary.get("counts")
    expected = {
        "received": baseline.sources,
        "accepted": 0,
        "quarantined": 0,
        "duplicate": baseline.sources,
    }
    if counts != expected:
        raise CheckError("replay did not disposition every input as duplicate")
    if authoritative_snapshot() != baseline.authoritative:
        raise CheckError("authoritative tables changed during replay")
    if disposition_count(str(summary.get("run_id"))) != baseline.dispositions + baseline.sources:
        raise CheckError("replay disposition growth did not equal received inputs")
    if manifest_bytes(str(summary.get("run_id"))) != baseline.manifest:
        raise CheckError("immutable manifest row changed during replay")


def migrate_apply(_run_id: str) -> None:
    role_password_dir = Path(os.environ["DCIM_RUNTIME_ROOT"]) / "dev-build" / "secrets"
    _ = migrate.apply(role_password_dir)
    _ = migrate.apply(role_password_dir)
    _ = migrate.verify()


def pipeline_run(run_id: str) -> None:
    _ = pipeline_execute(run_id)


def idempotency_replay(run_id: str) -> None:
    baseline = _baseline(run_id)
    _assert_duplicate_replay(pipeline_execute(run_id), baseline)


def rollback_reapply(run_id: str) -> None:
    role_password_dir = Path(os.environ["DCIM_RUNTIME_ROOT"]) / "dev-build" / "secrets"
    migrate.rollback(migrate.MIGRATION_ID)
    stage_complete = False
    try:
        _ = migrate.apply(role_password_dir)
        _ = migrate.verify()
        _ = pipeline_execute(run_id)
        baseline = _baseline(run_id)
        _assert_duplicate_replay(pipeline_execute(run_id), baseline)
        stage_complete = True
    finally:
        if not stage_complete:
            _ = migrate.apply(role_password_dir)
            _ = migrate.verify()


def recovery_check(_run_id: str) -> None:
    _ = recovery.verify_recovery()


def capacity_check(_run_id: str) -> None:
    if capacity.run([]) != 0:
        raise CheckError("capacity admission failed")


def noc_verify(run_id: str) -> None:
    first = noc.generate(run_id)
    first_bytes = tuple(path.read_bytes() for path in first)
    second = noc.generate(run_id)
    if first_bytes != tuple(path.read_bytes() for path in second):
        raise CheckError("NOC generation is not byte-identical")


def clean_acceptance_state() -> None:
    _ = db.psql(
        "TRUNCATE TABLE phase2.noc_cards, phase2.workflow_drafts, phase2.dispositions, phase2.events, "
        "phase2.ci_relationships, phase2.aliases, phase2.cis, phase2.assets, phase2.run_manifests "
        "RESTART IDENTITY;"
    )


def unit_tests(_run_id: str) -> None:
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests" / "phase2"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        raise CheckError(f"unit test discovery skipped {len(result.skipped)} test(s)")
    if not result.wasSuccessful():
        raise CheckError("unit test discovery failed")


def _run_json_command(arguments: list[str]) -> db.JsonObject:
    script = Path(arguments[1]).name
    command_arguments = arguments[2:]
    output = StringIO()
    with redirect_stdout(output):
        match script:
            case "run.py":
                from scripts.phase2 import run as pipeline

                result = pipeline.run(command_arguments)
            case "stream.py":
                from scripts.phase2 import stream

                result = stream.main(command_arguments)
            case _:
                raise CheckError(f"unsupported Phase 2 command: {script}")
    if result != 0:
        raise CheckError(f"command failed: {script}")
    try:
        value = json.loads(output.getvalue())
    except json.JSONDecodeError as error:
        raise CheckError("command did not return JSON") from error
    if not isinstance(value, dict):
        raise CheckError("command returned a non-object JSON summary")
    return value


def topic_provision(_run_id: str) -> None:
    from scripts.phase2 import kafka_topics

    if kafka_topics.main([]) != 0:
        raise CheckError("Kafka topic provisioning failed")


def topic_verify(_run_id: str) -> None:
    from scripts.phase2 import kafka_topics

    if kafka_topics.main(["--verify"]) != 0:
        raise CheckError("Kafka topic verification failed")


def _stream_evidence_dir(run_id: str) -> Path:
    path = Path(os.environ["DCIM_RUNTIME_ROOT"]) / "dev-build" / "evidence" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _publish_sentinels(source_run_id: str) -> None:
    from scripts.phase2.kafka_producer import KafkaEnvelopeProducer

    producer = KafkaEnvelopeProducer()
    headers = {"source_run_id": source_run_id, "reason": "foreign_sentinel"}
    payload = json.dumps({"sentinel": source_run_id}, sort_keys=True).encode("utf-8")
    producer.produce_envelope(NORMALIZED_TOPIC, None, payload, headers)
    producer.produce_envelope(DLQ_TOPIC, None, payload, headers)
    producer.flush(30)


def _capture_end_offsets(topic: str) -> dict[str, int]:
    from scripts.phase2 import stream

    return stream.capture_end_offsets(topic)


def _expected_event_ids() -> tuple[str, ...]:
    from contracts.python.dcim_contracts.envelope import Envelope
    from pydantic import ValidationError
    from scripts.phase2.runner_input import adapt_input

    accepted: list[str] = []
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        try:
            candidate = adapt_input(path, FIXTURES_DIR, FIXED_CLOCK)
            accepted.append(Envelope.model_validate(candidate, strict=True).event_id)
        except (Phase2Error, ValidationError):
            continue
    return tuple(accepted)


def _event_counts(event_ids: tuple[str, ...]) -> tuple[int, ...]:
    return tuple(
        _single_integer(
            "SELECT json_build_object('events', count(*))::text FROM phase2.events "
            f"WHERE event_id = {db.literal(event_id)}::uuid;",
            "events",
        )
        for event_id in event_ids
    )


def stream_roundtrip(run_id: str) -> None:
    stream_run_id = f"stream-{run_id}-{time.time_ns()}"
    evidence_dir = _stream_evidence_dir(stream_run_id)
    start_offsets = evidence_dir / "start-offsets.json"
    replay_offsets = evidence_dir / "replay-offsets.json"
    _publish_sentinels(f"sentinel-{time.time_ns()}")
    start_offsets.write_text(
        json.dumps(_capture_end_offsets(NORMALIZED_TOPIC), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    event_ids = _expected_event_ids()
    fixture_count = len(tuple(FIXTURES_DIR.glob("*.json")))
    accepted_count = len(event_ids)
    invalid_count = fixture_count - accepted_count
    producer = _run_json_command([
        sys.executable, str(ROOT / "scripts/phase2/run.py"), "--mode", "stream",
        "--run-id", stream_run_id, "--fixtures-dir", str(FIXTURES_DIR),
        "--fixed-clock", FIXED_CLOCK,
    ])
    if producer != {"received": fixture_count, "published": accepted_count, "dlq": invalid_count}:
        raise CheckError("stream producer ledger is not balanced")
    first = _run_json_command([
        sys.executable, str(ROOT / "scripts/phase2/stream.py"), "--run-id", stream_run_id,
        "--start-offsets", str(start_offsets), "--max-messages", str(accepted_count),
        "--idle-timeout-seconds", "30",
    ])
    expected_first = {"received": accepted_count, "accepted": accepted_count, "quarantined": 0, "duplicate": 0}
    if first.get("ledger") != expected_first or _event_counts(event_ids) != (1,) * accepted_count:
        raise CheckError("first stream pass did not persist every accepted event exactly once")
    offsets = first.get("offsets")
    if not isinstance(offsets, dict):
        raise CheckError("first stream pass did not record replay offsets")
    ranges: dict[str, list[int]] = {}
    for partition, value in offsets.items():
        if not isinstance(partition, str) or not isinstance(value, dict):
            raise CheckError("first stream pass returned invalid replay offsets")
        first_offset = value.get("first")
        last_offset = value.get("last")
        if type(first_offset) is not int or type(last_offset) is not int:
            raise CheckError("first stream pass returned invalid replay boundaries")
        ranges[partition] = [first_offset, last_offset]
    replay_offsets.write_text(json.dumps(ranges, sort_keys=True) + "\n", encoding="utf-8")
    before_replay = _event_counts(event_ids)
    replay = _run_json_command([
        sys.executable, str(ROOT / "scripts/phase2/stream.py"), "--run-id", stream_run_id,
        "--group-id", f"dcim-phase2-replay-{time.time_ns()}", "--from-offsets", str(replay_offsets),
        "--max-messages", str(accepted_count), "--idle-timeout-seconds", "30",
    ])
    expected_replay = {"received": accepted_count, "accepted": 0, "quarantined": 0, "duplicate": accepted_count}
    if replay.get("ledger") != expected_replay or _event_counts(event_ids) != before_replay:
        raise CheckError("stream replay did not produce only duplicate dispositions")
    dlq = _run_json_command([
        sys.executable, str(ROOT / "scripts/phase2/stream.py"), "--run-id", stream_run_id,
        "--topic", DLQ_TOPIC, "--group-id", f"dcim-phase2-dlq-{time.time_ns()}",
        "--count-only", "--max-messages", str(invalid_count), "--idle-timeout-seconds", "30",
    ])
    if dlq.get("count") != invalid_count or dlq.get("missing_reason_count") != 0:
        raise CheckError("stream DLQ count or reason headers did not match rejected fixtures")


def latency_assert(run_id: str) -> None:
    from scripts.phase2 import latency

    evidence = _stream_evidence_dir(run_id) / "kafka-latency.json"
    result = latency.main([
        "--leg", "kafka",
        "--count", "50", "--seed", "42", "--assert", "--output", str(evidence),
    ])
    if result != 0:
        raise CheckError(f"Kafka latency assertion failed; evidence={evidence}")
    print(f"latency-evidence: {evidence}")


STAGES: tuple[Stage, ...] = (
    ("topic-provision", topic_provision),
    ("migrate-apply", migrate_apply),
    ("pipeline-run", pipeline_run),
    ("idempotency-replay", idempotency_replay),
    ("rollback-reapply", rollback_reapply),
    ("recovery", recovery_check),
    ("capacity", capacity_check),
    ("noc-verify", noc_verify),
    ("unit-tests", unit_tests),
    ("topic-verify", topic_verify),
    ("stream-roundtrip", stream_roundtrip),
    ("latency-assert", latency_assert),
)


def _run_stage(label: str, action: StageAction, run_id: str) -> None:
    try:
        action(run_id)
    except (
        CheckError,
        Phase2Error,
        capacity.CapacityError,
        db.DatabaseCommandError,
        db.JsonExtractionError,
        migrate.MigrationError,
        noc.NocError, recovery.RecoveryError, OSError, ValueError,
    ) as error:
        raise StageFailure(label, str(error)) from error
    print(f"{label}: PASS")


def run() -> int:
    run_id = f"phase2-check-{short_commit()}"
    for label, action in STAGES[:-1]:
        if label == "unit-tests":
            try:
                clean_acceptance_state()
            except db.DatabaseCommandError as error:
                raise StageFailure("phase2-check", f"acceptance cleanup failed: {error}") from error
        _run_stage(label, action, run_id)
    try:
        clean_acceptance_state()
    except db.DatabaseCommandError as error:
        raise StageFailure("phase2-check", f"acceptance cleanup failed: {error}") from error
    label, action = STAGES[-1]
    _run_stage(label, action, run_id)
    return 0


def main() -> int:
    try:
        return run()
    except StageFailure as error:
        print(error, file=sys.stderr)
        return 1
    except CheckError as error:
        print(f"phase2-check: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
