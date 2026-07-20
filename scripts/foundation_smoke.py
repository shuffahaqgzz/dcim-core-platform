#!/usr/bin/env python3
"""Bounded synthetic foundation smoke and recovery orchestrator."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "deploy/compose/dev-build/compose.yaml"
PROFILES = ("data", "observability", "smoke")
LONG_RUNNING = (
    "postgres", "kafka", "postgres-exporter", "kafka-jmx-exporter", "prometheus", "grafana",
)


class SmokeFailure(RuntimeError):
    pass


def run(command: list[str], *, timeout: int, input_text: str | None = None) -> str:
    result = subprocess.run(
        command, cwd=ROOT, input=input_text, capture_output=True, text=True,
        timeout=timeout, check=False,
    )
    if result.returncode:
        decisive = (result.stderr or result.stdout).strip().splitlines()
        detail = decisive[-1] if decisive else f"exit {result.returncode}"
        raise SmokeFailure(f"command failed: {command[0]} {command[1] if len(command) > 1 else ''}: {detail}")
    return result.stdout


def runtime_root() -> Path:
    raw = os.environ.get("DCIM_RUNTIME_ROOT")
    if not raw:
        raise SmokeFailure("DCIM_RUNTIME_ROOT is required")
    root = Path(raw).expanduser().resolve()
    try:
        root.relative_to(ROOT)
    except ValueError:
        return root
    raise SmokeFailure("DCIM_RUNTIME_ROOT must resolve outside repository")


def compose_prefix() -> list[str]:
    root = runtime_root()
    command = [
        "docker", "compose", "--env-file", str(root / "dev-build/runtime.env"),
        "--env-file", str(root / "dev-build/images.env"),
        "-f", str(COMPOSE_FILE),
    ]
    for profile in PROFILES:
        command.extend(("--profile", profile))
    return command


def compose(*arguments: str, timeout: int = 180, input_text: str | None = None) -> str:
    return run([*compose_prefix(), *arguments], timeout=timeout, input_text=input_text)


def capacity_disposition(ratio: float) -> dict[str, object]:
    allowed = ratio < 0.90
    return {
        "logical_storage_ratio": round(ratio, 6),
        "writes_allowed": allowed,
        "disposition": "accepted" if allowed else "refused-capacity-critical",
    }


def safe_commit() -> str:
    try:
        return run(["git", "rev-parse", "HEAD"], timeout=5).strip()
    except SmokeFailure:
        return "unknown"


def evidence_record(mode: str, run_id: str, duration: float, result: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "commit": safe_commit(),
        "capability_profiles": list(PROFILES),
        "utc_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "duration_seconds": round(duration, 3),
        "assertion_result": result,
        "synthetic_run_id": run_id,
        "mode": mode,
    }


def write_evidence(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(record, handle, sort_keys=True)
        handle.write("\n")


def prometheus_api(endpoint: str) -> dict[str, object]:
    output = compose(
        "exec", "-T", "prometheus", "wget", "-qO-",
        f"http://127.0.0.1:9090{endpoint}", timeout=20,
    )
    payload = json.loads(output)
    if payload.get("status") != "success":
        raise SmokeFailure("Prometheus API returned non-success status")
    return payload


def query_scalar(expression: str) -> float:
    payload = prometheus_api(f"/api/v1/query?query={quote(expression, safe='{}\"=,')}")
    results = payload["data"]["result"]
    if not results:
        return 0.0
    return float(results[0]["value"][1])


def assert_capacity() -> None:
    ratio = query_scalar("sum(kafka_log_size_bytes) / 42949672960")
    disposition = capacity_disposition(ratio)
    if not disposition["writes_allowed"]:
        raise SmokeFailure("refused-capacity-critical: logical storage at or above 90 percent")


def postgres_round_trip(run_id: str) -> None:
    sql = (
        "CREATE TABLE IF NOT EXISTS foundation.smoke_events "
        "(run_id text PRIMARY KEY, observed_at timestamptz NOT NULL DEFAULT now()); "
        f"INSERT INTO foundation.smoke_events(run_id) VALUES ('{run_id}') "
        "ON CONFLICT (run_id) DO NOTHING; "
        f"SELECT run_id FROM foundation.smoke_events WHERE run_id = '{run_id}';"
    )
    output = compose(
        "run", "--rm", "postgres-smoke", "psql", "-At", "-v", "ON_ERROR_STOP=1",
        "-c", sql, timeout=30,
    )
    if run_id not in output.splitlines():
        raise SmokeFailure("PostgreSQL synthetic round trip missing exact run ID")


def kafka_round_trip(run_id: str) -> None:
    compose(
        "exec", "-T", "kafka", "/opt/kafka/bin/kafka-topics.sh", "--bootstrap-server",
        "kafka:9092", "--create", "--if-not-exists", "--topic",
        "dcim.synthetic.smoke.v1", "--partitions", "1", "--replication-factor", "1",
        "--config", "max.message.bytes=1048576", "--config", "retention.ms=86400000",
        "--config", "segment.bytes=268435456", timeout=30,
    )
    topics = compose(
        "exec", "-T", "kafka", "/opt/kafka/bin/kafka-topics.sh", "--bootstrap-server",
        "kafka:9092", "--list", timeout=20,
    ).splitlines()
    non_internal = sorted(topic for topic in topics if topic and not topic.startswith("__"))
    if non_internal != ["dcim.synthetic.smoke.v1"]:
        raise SmokeFailure(f"unexpected non-internal Kafka topics: {non_internal}")
    event = json.dumps({"kind": "synthetic-foundation-smoke", "run_id": run_id}, sort_keys=True)
    compose(
        "exec", "-T", "kafka", "/opt/kafka/bin/kafka-console-producer.sh",
        "--bootstrap-server", "kafka:9092", "--topic", "dcim.synthetic.smoke.v1",
        timeout=20, input_text=event + "\n",
    )
    output = compose(
        "exec", "-T", "kafka", "/opt/kafka/bin/kafka-console-consumer.sh",
        "--bootstrap-server", "kafka:9092", "--topic", "dcim.synthetic.smoke.v1",
        "--from-beginning", "--max-messages", "100", "--timeout-ms", "10000",
        timeout=20,
    )
    if run_id not in output:
        raise SmokeFailure("Kafka synthetic replay missing exact run ID")


def assert_observability() -> None:
    targets = prometheus_api("/api/v1/targets")
    active = targets["data"]["activeTargets"]
    expected = {"prometheus", "postgres-exporter", "kafka-jmx-exporter", "grafana"}
    healthy = {item["labels"]["job"] for item in active if item.get("health") == "up"}
    if not expected.issubset(healthy):
        raise SmokeFailure(f"Prometheus targets not healthy: {sorted(expected - healthy)}")
    rules = prometheus_api("/api/v1/rules")
    names = {
        rule["name"] for group in rules["data"]["groups"] for rule in group.get("rules", [])
    }
    required_rules = {
        "FoundationTargetDown", "PostgreSQLExporterBackendDown", "KafkaBrokerNotActive",
        "KafkaStorageSeventyPercent", "KafkaStorageEightyFivePercent", "KafkaStorageNinetyPercent",
    }
    if not required_rules.issubset(names):
        raise SmokeFailure("Prometheus required rules missing")
    if query_scalar('up{job="postgres-exporter"}') != 1 or query_scalar("pg_up") != 1:
        raise SmokeFailure("PostgreSQL exporter backend health failed")
    if query_scalar('up{job="kafka-jmx-exporter"}') != 1:
        raise SmokeFailure("Kafka JMX exporter scrape health failed")
    if query_scalar("kafka_server_broker_state") <= 0:
        raise SmokeFailure("Kafka broker/controller metric invalid")

    root = runtime_root()
    user = (root / "dev-build/secrets/grafana-admin-user").read_text(encoding="utf-8").strip()
    admin_value = (root / "dev-build/secrets/grafana-admin-password").read_text(encoding="utf-8").strip()
    authorization_value = base64.b64encode(f"{user}:{admin_value}".encode()).decode()
    base_url = grafana_url()
    for path in ("/api/health", "/api/datasources/uid/foundation-prometheus"):
        request = Request(f"{base_url}{path}", headers={"Authorization": f"Basic {authorization_value}"})
        try:
            with urlopen(request, timeout=10) as response:
                if response.status != 200:
                    raise SmokeFailure(f"Grafana endpoint failed: {path}")
        except URLError as error:
            raise SmokeFailure(f"Grafana endpoint failed: {path}: {error.reason}") from error


def grafana_url() -> str:
    address = run(
        [
            "docker", "inspect", "dcim-build-grafana-1", "--format",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
        ],
        timeout=10,
    ).strip()
    if not address:
        raise SmokeFailure("Grafana internal bridge address unavailable")
    return f"http://{address}:3000"


def wait_for_alert(name: str, firing: bool, timeout: int = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        payload = prometheus_api("/api/v1/alerts")
        found = any(
            alert["labels"].get("alertname") == name and alert.get("state") == "firing"
            for alert in payload["data"]["alerts"]
        )
        if found == firing:
            return
        time.sleep(5)
    raise SmokeFailure(f"controlled alert transition timed out: {name} firing={firing}")


def controlled_alert_transition() -> None:
    compose("stop", "--timeout", "30", "postgres-exporter", timeout=40)
    try:
        wait_for_alert("FoundationTargetDown", True)
    finally:
        compose("up", "-d", "--wait", "--wait-timeout", "60", "postgres-exporter", timeout=90)
    wait_for_alert("FoundationTargetDown", False)


def fast_smoke(run_id: str) -> None:
    assert_capacity()
    postgres_round_trip(run_id)
    kafka_round_trip(run_id)
    assert_observability()
    controlled_alert_transition()


def recovery_smoke(run_id: str) -> None:
    assert_capacity()
    postgres_round_trip(run_id)
    kafka_round_trip(run_id)
    compose("restart", "--timeout", "30", *LONG_RUNNING, timeout=90)
    compose("up", "-d", "--wait", "--wait-timeout", "180", *LONG_RUNNING, timeout=210)
    postgres_round_trip(run_id)
    kafka_round_trip(run_id)
    assert_observability()

    dump = compose(
        "exec", "-T", "postgres", "pg_dump", "-U", "dcim_bootstrap", "-d",
        "dcim_foundation", "--schema=foundation", "--no-owner", timeout=60,
    )
    restore_db = "foundation_restore_" + run_id.rsplit("-", 1)[-1][:12]
    compose(
        "exec", "-T", "postgres", "psql", "-U", "dcim_bootstrap", "-d", "postgres",
        "-v", "ON_ERROR_STOP=1", "-c", f"DROP DATABASE IF EXISTS {restore_db};",
        timeout=30,
    )
    compose(
        "exec", "-T", "postgres", "psql", "-U", "dcim_bootstrap", "-d", "postgres",
        "-v", "ON_ERROR_STOP=1", "-c", f"CREATE DATABASE {restore_db};",
        timeout=30,
    )
    try:
        compose(
            "exec", "-T", "postgres", "psql", "-U", "dcim_bootstrap", "-d", restore_db,
            "-v", "ON_ERROR_STOP=1", timeout=60, input_text=dump,
        )
        checksum_sql = (
            "SELECT count(*) || ':' || md5(coalesce(string_agg(run_id, ',' ORDER BY run_id), '')) "
            "FROM foundation.smoke_events;"
        )
        original = compose(
            "exec", "-T", "postgres", "psql", "-At", "-U", "dcim_bootstrap", "-d",
            "dcim_foundation", "-c", checksum_sql, timeout=20,
        ).strip()
        restored = compose(
            "exec", "-T", "postgres", "psql", "-At", "-U", "dcim_bootstrap", "-d",
            restore_db, "-c", checksum_sql, timeout=20,
        ).strip()
        if not original or original != restored:
            raise SmokeFailure("PostgreSQL restore logical checksum mismatch")
    finally:
        compose(
            "exec", "-T", "postgres", "psql", "-U", "dcim_bootstrap", "-d", "postgres",
            "-c", f"DROP DATABASE IF EXISTS {restore_db};", timeout=30,
        )


def execute_mode(mode: str) -> int:
    run_id = "synthetic-" + secrets.token_hex(16)
    started = time.monotonic()
    result = "pass"
    try:
        if mode == "fast":
            fast_smoke(run_id)
        else:
            recovery_smoke(run_id)
    except (SmokeFailure, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        result = "fail"
        print(f"foundation-{mode}: {error}", file=sys.stderr)
        return_code = 1
    else:
        return_code = 0
    duration = time.monotonic() - started
    path = runtime_root() / "dev-build/evidence" / f"{mode}-{run_id}.json"
    write_evidence(path, evidence_record(mode, run_id, duration, result))
    print(f"foundation-{mode}: {result.upper()} ({duration:.1f}s)")
    return return_code


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    capacity = subparsers.add_parser("capacity")
    capacity.add_argument("--ratio", required=True, type=float)
    evidence = subparsers.add_parser("evidence")
    evidence.add_argument("--output", required=True, type=Path)
    evidence.add_argument("--mode", choices=("fast", "recovery"), required=True)
    evidence.add_argument("--run-id", required=True)
    evidence.add_argument("--duration", required=True, type=float)
    evidence.add_argument("--result", choices=("pass", "fail"), required=True)
    subparsers.add_parser("fast")
    subparsers.add_parser("recovery")
    subparsers.add_parser("grafana-url")
    arguments = parser.parse_args()

    if arguments.command == "capacity":
        disposition = capacity_disposition(arguments.ratio)
        print(json.dumps(disposition, sort_keys=True))
        return 0 if disposition["writes_allowed"] else 1
    if arguments.command == "evidence":
        write_evidence(
            arguments.output,
            evidence_record(arguments.mode, arguments.run_id, arguments.duration, arguments.result),
        )
        return 0
    if arguments.command == "grafana-url":
        try:
            print(grafana_url())
        except SmokeFailure as error:
            print(f"foundation-grafana-url: {error}", file=sys.stderr)
            return 1
        return 0
    return execute_mode(arguments.command)


if __name__ == "__main__":
    raise SystemExit(main())
