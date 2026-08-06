#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from pathlib import Path
import sys
import uuid

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.phase3 import default_token_file
from scripts.phase2 import db
from scripts.phase3.e2e_dashboard import dashboard
from scripts.phase3.e2e_latency import latency
from scripts.phase3.e2e_pipeline import drain, produce, zero_loss
from scripts.phase3.e2e_support import (
    DEFAULT_FIXED_CLOCK,
    E2EConfig,
    E2EFailure,
    E2EState,
    ROOT,
    StageFailure,
    _run_command,
    build_evidence,
    cleanup_files,
    cleanup_run,
    commit_sha,
    write_evidence,
    utc_now,
)


STAGE_NAMES = (
    "topic-verify",
    "produce",
    "drain",
    "zero-loss",
    "dashboard",
    "latency",
)


def _topic_verify(_state: E2EState) -> None:
    result = _run_command(
        [sys.executable, str(ROOT / "scripts/phase2/kafka_topics.py"), "--verify"],
        "topic verification",
    )
    if result.returncode != 0:
        raise E2EFailure("Kafka topic verification failed")


STAGES: tuple[tuple[str, Callable[[E2EState], None]], ...] = (
    ("topic-verify", _topic_verify),
    ("produce", produce),
    ("drain", drain),
    ("zero-loss", zero_loss),
    ("dashboard", dashboard),
    ("latency", latency),
)


def execute_stages(
    state: E2EState,
    *,
    actions: tuple[tuple[str, Callable[[E2EState], None]], ...] = STAGES,
) -> None:
    for number, (name, action) in enumerate(actions, start=1):
        state.completed_stages.append(name)
        try:
            action(state)
        except StageFailure:
            raise
        except E2EFailure as error:
            raise StageFailure(number, name, str(error)) from error
        except Exception as error:
            raise StageFailure(number, name, "unexpected stage failure") from error


def _default_output() -> Path:
    runtime_root = Path(os.environ.get("DCIM_RUNTIME_ROOT", "/run"))
    return runtime_root / "dev-build/evidence/e2e/evidence-e2e.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the bounded synthetic Phase 3 E2E flow.")
    parser.add_argument("--output", type=Path, default=_default_output())
    parser.add_argument("--fixtures-dir", type=Path, default=ROOT / "fixtures/synthetic/events")
    parser.add_argument("--token-file", type=Path, default=default_token_file())
    parser.add_argument("--fixed-clock", default=DEFAULT_FIXED_CLOCK)
    parser.add_argument("--idle-timeout-seconds", type=float, default=30.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    state = E2EState(
        config=E2EConfig(
            output=arguments.output,
            fixtures_dir=arguments.fixtures_dir,
            token_file=arguments.token_file,
            fixed_clock=arguments.fixed_clock,
            idle_timeout_seconds=arguments.idle_timeout_seconds,
        ),
        run_id=f"phase3-e2e-{uuid.uuid4()}",
    )
    failure: E2EFailure | None = None
    try:
        execute_stages(state)
    except E2EFailure as error:
        failure = error
    try:
        if state.stream_started:
            cleanup_run(state.run_id)
            state.cleanup_complete = True
        cleanup_files(state)
    except E2EFailure as error:
        if failure is None:
            failure = error
    if failure is not None:
        print(str(failure), file=sys.stderr)
        return 1
    try:
        evidence = build_evidence(state, commit_sha=commit_sha(), generated_at=utc_now())
        write_evidence(state, evidence)
    except E2EFailure as error:
        print(f"e2e: FAIL: {error}", file=sys.stderr)
        return 1
    print(
        f"e2e: PASS zero-loss={state.checks.get('zero_silent_loss')} "
        f"dashboard={state.checks.get('dashboard_visibility')} "
        f"p95-ms={state.latency.get('p95_ms')} evidence={arguments.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
