from __future__ import annotations

import sys

from scripts.phase3.e2e_support import (
    E2EFailure,
    E2EState,
    ROOT,
    _run_command,
    integer,
    read_json_object,
)


def latency(state: E2EState) -> None:
    if state.work_dir is None:
        raise E2EFailure("E2E work directory is unavailable")
    output = state.work_dir / "latency.json"
    offsets = state.work_dir / "start-offsets.json"
    state.temporary_files.extend((output, offsets))
    result = _run_command(
        [
            sys.executable,
            str(ROOT / "scripts/phase2/latency.py"),
            "--leg",
            "kafka",
            "--count",
            "50",
            "--seed",
            "42",
            "--assert",
            "--output",
            str(output),
            "--fixtures-dir",
            str(state.config.fixtures_dir),
        ],
        "Kafka latency",
    )
    if result.returncode != 0:
        raise E2EFailure("Kafka latency assertion failed")
    report = read_json_object(output, "Kafka latency")
    distribution = report.get("dashboard_latency_ns")
    if not isinstance(distribution, dict):
        raise E2EFailure("Kafka latency distribution is unavailable")
    p95_ns = integer(distribution.get("p95"), "Kafka latency")
    p95_ms = p95_ns / 1_000_000
    if p95_ms >= 5000:
        raise E2EFailure("Kafka latency p95 is not below 5000 ms")
    state.latency = {"leg": "kafka", "count": 50, "seed": 42, "p95_ms": p95_ms}
    state.checks["latency_p95_below_5000_ms"] = True
    state.checks["latency_cleanup"] = True
