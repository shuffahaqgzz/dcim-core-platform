#!/usr/bin/env python3
"""Bounded synthetic foundation smoke and recovery orchestrator."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

try:
    from scripts.protected_runtime import (
        ensure_protected_directory, external_runtime_root, protected_runtime_path,
        validate_compose_project_name,
    )
    from scripts.strict_json import load_object
except ModuleNotFoundError:
    from protected_runtime import (
        ensure_protected_directory, external_runtime_root, protected_runtime_path,
        validate_compose_project_name,
    )
    from strict_json import load_object


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "deploy/compose/dev-build/compose.yaml"
ACCEPTANCE_OVERRIDE_NAME = "acceptance-compose.override.yaml"
IMAGE_INVENTORY = ROOT / "deploy/compose/images.json"
IMAGE_RECIPES = ROOT / "deploy/compose/derived-images/recipes.json"
LICENSE_DISPOSITIONS = ROOT / "deploy/compose/derived-images/license-dispositions.json"
PROFILES = ("data", "observability", "smoke")
LONG_RUNNING = (
    "postgres", "kafka", "postgres-exporter", "kafka-jmx-exporter", "prometheus", "grafana",
)
MODE_LIMIT_SECONDS = {"fast": 300.0, "recovery": 900.0}
ACTIVE_DEADLINE: float | None = None


class SmokeFailure(RuntimeError):
    pass


def run(command: list[str], *, timeout: int, input_text: str | None = None) -> str:
    effective_timeout = float(timeout)
    if ACTIVE_DEADLINE is not None:
        remaining = ACTIVE_DEADLINE - time.monotonic()
        if remaining <= 0:
            raise SmokeFailure("mode deadline exceeded")
        effective_timeout = min(effective_timeout, max(1, math.ceil(remaining)))
    result = subprocess.run(
        command, cwd=ROOT, input=input_text, capture_output=True, text=True,
        timeout=effective_timeout, check=False,
    )
    if result.returncode:
        decisive = (result.stderr or result.stdout).strip().splitlines()
        detail = decisive[-1] if decisive else f"exit {result.returncode}"
        raise SmokeFailure(f"command failed: {command[0]} {command[1] if len(command) > 1 else ''}: {detail}")
    return result.stdout


def runtime_root(value: Path | None = None) -> Path:
    raw = os.environ.get("DCIM_RUNTIME_ROOT") if value is None else os.fspath(value)
    if not raw:
        raise SmokeFailure("DCIM_RUNTIME_ROOT is required")
    try:
        return external_runtime_root(Path(raw))
    except ValueError as error:
        raise SmokeFailure(str(error)) from error


def compose_override_path(root: Path, project: str) -> Path | None:
    raw = os.environ.get("DCIM_COMPOSE_OVERRIDE")
    if project == "dcim-build":
        if raw:
            raise SmokeFailure("Compose override is prohibited for normal lifecycle")
        return None
    if not raw:
        raise SmokeFailure("acceptance Compose override is required")
    try:
        override = protected_runtime_path(
            root, "dev-build", ACCEPTANCE_OVERRIDE_NAME,
        )
    except ValueError as error:
        raise SmokeFailure(str(error)) from error
    supplied = Path(os.path.abspath(os.fspath(Path(raw).expanduser())))
    if supplied != override:
        raise SmokeFailure("acceptance Compose override path mismatch")
    if not override.is_file() or override.is_symlink():
        raise SmokeFailure("acceptance Compose override is unavailable")
    return override


def compose_prefix() -> list[str]:
    root = runtime_root()
    project = compose_project_name()
    command = [
        "docker", "compose", "--env-file", str(root / "dev-build/runtime.env"),
        "--env-file", str(root / "dev-build/images.env"),
        "-f", str(COMPOSE_FILE),
    ]
    override = compose_override_path(root, project)
    if override is not None:
        command.extend(("-f", str(override)))
    for profile in PROFILES:
        command.extend(("--profile", profile))
    return command


def compose_project_name() -> str:
    value = os.environ.get("COMPOSE_PROJECT_NAME", "dcim-build")
    try:
        return validate_compose_project_name(value)
    except ValueError as error:
        raise SmokeFailure(str(error)) from error


def compose_container(service: str) -> str:
    return f"{compose_project_name()}-{service}-1"


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
    bounded_result = (
        "fail" if result == "pass" and duration > MODE_LIMIT_SECONDS[mode] else result
    )
    return {
        "schema_version": 2,
        "commit": safe_commit(),
        "capability_profiles": list(PROFILES),
        "utc_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "duration_seconds": round(duration, 3),
        "assertion_result": bounded_result,
        "synthetic_run_id": run_id,
        "mode": mode,
    }


def foundation_image_digests(root: Path) -> dict[str, str]:
    try:
        lock = load_object(
            protected_runtime_path(root, "dev-build", "derived-images-lock.json")
        )
        inventory = load_object(IMAGE_INVENTORY)
        if lock.get("schema_version") != 2 or lock.get("publication") is not False:
            raise ValueError("derived image lock policy mismatch")
        if lock.get("manifest_sha256") != hashlib.sha256(IMAGE_RECIPES.read_bytes()).hexdigest():
            raise ValueError("derived image lock recipe digest mismatch")
        if lock.get("license_dispositions_sha256") != hashlib.sha256(
            LICENSE_DISPOSITIONS.read_bytes()
        ).hexdigest():
            raise ValueError("derived image lock license disposition digest mismatch")
        locked_images = lock["images"]
        if not isinstance(locked_images, list) or len(locked_images) != 4:
            raise ValueError("derived image lock inventory mismatch")
        derived = {
            str(item["component"]): str(item["image_id"])
            for item in locked_images
            if isinstance(item, dict)
        }
        if set(derived) != {"postgres", "kafka", "grafana", "postgres-exporter"}:
            raise ValueError("derived image digest allowlist mismatch")
        if any(not re.fullmatch(r"sha256:[0-9a-f]{64}", value) for value in derived.values()):
            raise ValueError("derived image digest invalid")
        official = {
            str(item["component"]): str(item["image"]).rsplit("@", 1)[-1]
            for item in inventory["images"]
            if isinstance(item, dict)
        }
        official_references = {
            str(item["component"]): str(item["image"])
            for item in inventory["images"]
            if isinstance(item, dict)
        }
        running_contract = {
            "postgres": ("postgres", derived["postgres"], None),
            "kafka": ("kafka", derived["kafka"], None),
            "grafana": ("grafana", derived["grafana"], None),
            "postgres-exporter": (
                "postgres-exporter", derived["postgres-exporter"], None,
            ),
            "prometheus": (
                "prometheus", None, official_references["Prometheus"],
            ),
            "kafka-jmx-exporter": (
                "jmx-exporter-java-runtime", None,
                official_references["JMX exporter Java runtime"],
            ),
        }
        for service, (_, expected_id, expected_reference) in running_contract.items():
            inspected = run(
                [
                    "docker", "inspect", compose_container(service), "--format",
                    "{{.Image}}|{{.Config.Image}}",
                ],
                timeout=10,
            ).strip().split("|", 1)
            if len(inspected) != 2:
                raise ValueError(f"running image inspection invalid: {service}")
            actual_id, actual_reference = inspected
            if expected_id is not None and actual_id != expected_id:
                raise ValueError(f"running image ID mismatch: {service}")
            if expected_reference is not None and actual_reference != expected_reference:
                raise ValueError(f"running image reference mismatch: {service}")
        digests = {
            **derived,
            "prometheus": official["Prometheus"],
            "jmx-exporter-java-runtime": official["JMX exporter Java runtime"],
        }
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise SmokeFailure(f"image digest evidence unavailable: {error}") from error
    return dict(sorted(digests.items()))


def write_evidence(
    root: Path, mode: str, run_id: str, record: dict[str, object],
) -> Path:
    if not re.fullmatch(r"synthetic-[0-9a-f]{16,64}", run_id):
        raise SmokeFailure("synthetic run ID is invalid")
    enriched_record = {**record, "image_digests": foundation_image_digests(root)}
    try:
        directory = ensure_protected_directory(root, "dev-build", "evidence")
        path = directory / f"{mode}-{run_id}.json"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags, 0o600)
    except (OSError, ValueError) as error:
        raise SmokeFailure(f"protected evidence path rejected: {error}") from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(enriched_record, handle, sort_keys=True)
        handle.write("\n")
    return path


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


def assert_controlled_capacity_refusal() -> None:
    disposition = capacity_disposition(0.90)
    if disposition["writes_allowed"] or disposition["disposition"] != "refused-capacity-critical":
        raise SmokeFailure("controlled 90 percent capacity refusal failed")
    print("foundation-capacity: controlled_ninety_percent_refusal=PASS")


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


def postgres_verify_persisted(run_id: str) -> None:
    output = compose(
        "run", "--rm", "postgres-smoke", "psql", "-At", "-v", "ON_ERROR_STOP=1",
        "-c", f"SELECT run_id FROM foundation.smoke_events WHERE run_id = '{run_id}';",
        timeout=30,
    )
    if output.strip() != run_id:
        raise SmokeFailure("PostgreSQL persistence verification missing pre-restart run ID")


def kafka_topic_inventory() -> None:
    topics = compose(
        "exec", "-T", "kafka", "/opt/kafka/bin/kafka-topics.sh", "--bootstrap-server",
        "kafka:9092", "--list", timeout=20,
    ).splitlines()
    internal = sorted(topic for topic in topics if topic.startswith("__"))
    non_internal = sorted(topic for topic in topics if topic and not topic.startswith("__"))
    print(f"foundation-kafka: managed_internal_topics={len(internal)}")
    if non_internal != ["dcim.synthetic.smoke.v1"]:
        raise SmokeFailure(f"unexpected non-internal Kafka topics: {non_internal}")


def kafka_next_offset() -> int:
    output = compose(
        "exec", "-T", "kafka", "/opt/kafka/bin/kafka-get-offsets.sh",
        "--bootstrap-server", "kafka:9092", "--topic", "dcim.synthetic.smoke.v1",
        "--time", "-1", timeout=20,
    ).strip()
    match = re.fullmatch(r"dcim\.synthetic\.smoke\.v1:0:([0-9]+)", output)
    if not match:
        raise SmokeFailure("Kafka persistence offset metadata invalid")
    return int(match.group(1))


def kafka_consume_at_offset(run_id: str, offset: int) -> None:
    output = compose(
        "exec", "-T", "kafka", "/opt/kafka/bin/kafka-console-consumer.sh",
        "--bootstrap-server", "kafka:9092", "--topic", "dcim.synthetic.smoke.v1",
        "--partition", "0", "--offset", str(offset), "--max-messages", "1",
        "--timeout-ms", "10000", timeout=20,
    )
    if run_id not in output:
        raise SmokeFailure("Kafka persistence replay missing exact pre-restart run ID")


def ensure_kafka_topic() -> None:
    compose(
        "exec", "-T", "kafka", "/opt/kafka/bin/kafka-topics.sh", "--bootstrap-server",
        "kafka:9092", "--create", "--if-not-exists", "--topic",
        "dcim.synthetic.smoke.v1", "--partitions", "1", "--replication-factor", "1",
        "--config", "max.message.bytes=1048576", "--config", "retention.ms=86400000",
        "--config", "segment.bytes=268435456", timeout=30,
    )


def kafka_rejects_oversize_message() -> None:
    before = kafka_next_offset()
    payload = "x" * 1_048_577 + "\n"
    timeout = 30.0
    if ACTIVE_DEADLINE is not None:
        remaining = ACTIVE_DEADLINE - time.monotonic()
        if remaining <= 0:
            raise SmokeFailure("mode deadline exceeded")
        timeout = min(timeout, max(1, math.ceil(remaining)))
    subprocess.run(
        [
            *compose_prefix(), "exec", "-T", "kafka",
            "/opt/kafka/bin/kafka-console-producer.sh", "--bootstrap-server",
            "kafka:9092", "--topic", "dcim.synthetic.smoke.v1",
        ],
        cwd=ROOT,
        input=payload,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    time.sleep(5)
    after = kafka_next_offset()
    if after != before:
        raise SmokeFailure("Kafka oversize message above 1 MiB was accepted")


def kafka_round_trip(run_id: str) -> int:
    ensure_kafka_topic()
    kafka_topic_inventory()
    offset = kafka_next_offset()
    event = json.dumps({"kind": "synthetic-foundation-smoke", "run_id": run_id}, sort_keys=True)
    compose(
        "exec", "-T", "kafka", "/opt/kafka/bin/kafka-console-producer.sh",
        "--bootstrap-server", "kafka:9092", "--topic", "dcim.synthetic.smoke.v1",
        timeout=20, input_text=event + "\n",
    )
    kafka_consume_at_offset(run_id, offset)
    return offset


def kafka_verify_persisted(run_id: str, offset: int) -> None:
    kafka_topic_inventory()
    if kafka_next_offset() <= offset:
        raise SmokeFailure("Kafka persistence offset did not survive restart")
    kafka_consume_at_offset(run_id, offset)


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
        raise SmokeFailure("Kafka broker metric invalid")
    if query_scalar("kafka_controller_active_controller_count") != 1:
        raise SmokeFailure("Kafka active controller metric invalid")

    root = runtime_root()
    user = (root / "dev-build/secrets/grafana-admin-user").read_text(encoding="utf-8").strip()
    admin_value = (root / "dev-build/secrets/grafana-admin-password").read_text(encoding="utf-8").strip()
    authorization_value = base64.b64encode(f"{user}:{admin_value}".encode()).decode()
    base_url = grafana_url()
    for path in (
        "/api/health",
        "/api/datasources/uid/foundation-prometheus",
        "/api/datasources/proxy/uid/foundation-prometheus/api/v1/query?query=vector%281%29",
    ):
        request = Request(f"{base_url}{path}", headers={"Authorization": f"Basic {authorization_value}"})
        try:
            with urlopen(request, timeout=10) as response:
                if response.status != 200:
                    raise SmokeFailure(f"Grafana endpoint failed: {path}")
                if "/proxy/" in path:
                    payload = json.load(response)
                    if payload.get("status") != "success" or not payload.get("data", {}).get("result"):
                        raise SmokeFailure("Grafana Prometheus datasource query failed")
        except URLError as error:
            raise SmokeFailure(f"Grafana endpoint failed: {path}: {error.reason}") from error


def wait_for_observability(timeout: int = 60) -> None:
    deadline = time.monotonic() + timeout
    if ACTIVE_DEADLINE is not None:
        deadline = min(deadline, ACTIVE_DEADLINE)
    last_error: SmokeFailure | None = None
    while time.monotonic() < deadline:
        try:
            assert_observability()
            return
        except SmokeFailure as error:
            last_error = error
        time.sleep(5)
    if last_error is not None:
        raise SmokeFailure(f"observability did not converge: {last_error}") from last_error
    raise SmokeFailure("observability convergence deadline expired")


def grafana_url() -> str:
    address = run(
        [
            "docker", "inspect", compose_container("grafana"), "--format",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
        ],
        timeout=10,
    ).strip()
    if not address:
        raise SmokeFailure("Grafana internal bridge address unavailable")
    return f"http://{address}:3000"


def wait_for_alert(name: str, firing: bool, timeout: int = 60) -> None:
    deadline = time.monotonic() + timeout
    if ACTIVE_DEADLINE is not None:
        deadline = min(deadline, ACTIVE_DEADLINE)
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
    assert_controlled_capacity_refusal()
    assert_capacity()
    ensure_kafka_topic()
    kafka_rejects_oversize_message()
    postgres_round_trip(run_id)
    kafka_round_trip(run_id)
    assert_observability()
    controlled_alert_transition()


def recovery_smoke(run_id: str) -> None:
    assert_capacity()
    postgres_round_trip(run_id)
    kafka_offset = kafka_round_trip(run_id)
    compose("restart", "--timeout", "30", *LONG_RUNNING, timeout=90)
    compose("up", "-d", "--wait", "--wait-timeout", "180", *LONG_RUNNING, timeout=210)
    postgres_verify_persisted(run_id)
    kafka_verify_persisted(run_id, kafka_offset)
    wait_for_observability()

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
    global ACTIVE_DEADLINE
    run_id = "synthetic-" + secrets.token_hex(16)
    started = time.monotonic()
    ACTIVE_DEADLINE = started + MODE_LIMIT_SECONDS[mode]
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
    ACTIVE_DEADLINE = None
    if result == "pass" and duration > MODE_LIMIT_SECONDS[mode]:
        result = "fail"
        return_code = 1
        print(f"foundation-{mode}: mode deadline exceeded", file=sys.stderr)
    write_evidence(
        runtime_root(), mode, run_id, evidence_record(mode, run_id, duration, result),
    )
    print(f"foundation-{mode}: {result.upper()} ({duration:.1f}s)")
    return return_code


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    capacity = subparsers.add_parser("capacity")
    capacity.add_argument("--ratio", required=True, type=float)
    evidence = subparsers.add_parser("evidence")
    evidence.add_argument("--runtime-root", required=True, type=Path)
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
        try:
            record = evidence_record(
                arguments.mode, arguments.run_id, arguments.duration, arguments.result,
            )
            write_evidence(
                runtime_root(arguments.runtime_root), arguments.mode, arguments.run_id,
                record,
            )
        except SmokeFailure as error:
            print(f"foundation-evidence: {error}", file=sys.stderr)
            return 1
        return 0 if record["assertion_result"] == arguments.result else 1
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
