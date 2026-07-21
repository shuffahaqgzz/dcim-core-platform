#!/usr/bin/env python3
"""Validate normalized dcim-build Compose JSON without persisting secrets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

try:
    from scripts.protected_runtime import (
        external_runtime_root, protected_runtime_path, validate_compose_project_name,
    )
    from scripts.strict_json import load_object, loads_object
except ModuleNotFoundError:  # Direct script execution adds scripts/, not repository root.
    from protected_runtime import (
        external_runtime_root, protected_runtime_path, validate_compose_project_name,
    )
    from strict_json import load_object, loads_object


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_BIND_TARGETS = {
    "/docker-entrypoint-initdb.d/10-roles.sh": ROOT / "deploy/compose/dev-build/config/postgres/init-roles.sh",
    "/etc/jmx-exporter/kafka.yaml": ROOT / "deploy/compose/dev-build/config/kafka/jmx-exporter.yaml",
    "/etc/prometheus/prometheus.yml": ROOT / "deploy/compose/dev-build/config/prometheus/prometheus.yml",
    "/etc/prometheus/rules.yml": ROOT / "deploy/compose/dev-build/config/prometheus/rules.yml",
    "/etc/grafana/provisioning": ROOT / "deploy/compose/dev-build/config/grafana/provisioning",
    "/var/lib/grafana/dashboards": ROOT / "deploy/compose/dev-build/config/grafana/dashboards",
}
RUNTIME_ARTIFACT_TARGET = "/opt/jmx-exporter/jmx_prometheus_standalone-1.6.0.jar"
EXPECTED_USERS = {
    "postgres": "999:999", "postgres-smoke": "999:999",
    "kafka": "1000:1000", "kafka-smoke": "1000:1000",
    "postgres-exporter": "65534:65534", "kafka-jmx-exporter": "65534:65534",
    "prometheus": "65534:65534", "observability-smoke": "65534:65534",
    "grafana": "472:472",
}
EXPECTED_SECRETS = {
    "postgres": {
        ("postgres-superuser-password", "/run/secrets/postgres-superuser-password"),
        ("postgres-monitor-password", "/run/secrets/postgres-monitor-password"),
        ("postgres-smoke-password", "/run/secrets/postgres-smoke-password"),
    },
    "postgres-exporter": {
        ("postgres-monitor-password", "/run/secrets/postgres-monitor-password"),
    },
    "postgres-smoke": {
        ("postgres-smoke-password", "/run/secrets/postgres-smoke-password"),
    },
    "grafana": {
        ("grafana-admin-user", "/run/secrets/grafana-admin-user"),
        ("grafana-admin-password", "/run/secrets/grafana-admin-password"),
    },
}
SECRET_NAMES = {
    "postgres-superuser-password", "postgres-monitor-password", "postgres-smoke-password",
    "grafana-admin-user", "grafana-admin-password",
}
IMAGE_INVENTORY = ROOT / "deploy/compose/images.json"
IMAGE_RECIPES = ROOT / "deploy/compose/derived-images/recipes.json"
ALLOWED_SERVICES = {
    "postgres", "kafka", "prometheus", "grafana", "postgres-exporter",
    "kafka-jmx-exporter", "postgres-smoke", "kafka-smoke", "observability-smoke",
}
LONG_RUNNING = {
    "postgres", "kafka", "prometheus", "grafana", "postgres-exporter",
    "kafka-jmx-exporter",
}
DUAL_HOMED = {"postgres-exporter", "kafka-jmx-exporter"}
EXPECTED_EXPORTER_PROCESS = {
    "postgres-exporter": ((), ()),
    "kafka-jmx-exporter": (
        (
            "java", "-jar", "/opt/jmx-exporter/jmx_prometheus_standalone-1.6.0.jar",
            "5556", "/etc/jmx-exporter/kafka.yaml",
        ),
        (),
    ),
}
EXPECTED_PROMETHEUS_COMMAND = (
    "--config.file=/etc/prometheus/prometheus.yml",
    "--storage.tsdb.path=/prometheus",
    "--storage.tsdb.retention.time=7d",
    "--storage.tsdb.retention.size=20GB",
    "--web.enable-lifecycle",
)
EXPECTED_PROFILES = {
    "postgres": {"data"},
    "kafka": {"data"},
    "postgres-exporter": {"observability"},
    "kafka-jmx-exporter": {"observability"},
    "prometheus": {"observability"},
    "grafana": {"observability"},
    "postgres-smoke": {"smoke"},
    "kafka-smoke": {"smoke"},
    "observability-smoke": {"smoke"},
}
EXPECTED_NETWORKS = {
    "postgres": {"data"},
    "kafka": {"data"},
    "postgres-exporter": {"data", "observability"},
    "kafka-jmx-exporter": {"data", "observability"},
    "prometheus": {"observability"},
    "grafana": {"observability"},
    "postgres-smoke": {"data"},
    "kafka-smoke": {"data"},
    "observability-smoke": {"observability"},
}
IMAGE_COMPONENT_BY_SERVICE = {
    "postgres": "PostgreSQL",
    "postgres-smoke": "PostgreSQL",
    "kafka": "Apache Kafka",
    "kafka-smoke": "Apache Kafka",
    "prometheus": "Prometheus",
    "observability-smoke": "Prometheus",
    "grafana": "Grafana OSS",
    "postgres-exporter": "PostgreSQL exporter",
    "kafka-jmx-exporter": "JMX exporter Java runtime",
}
DERIVED_COMPONENT_BY_SERVICE = {
    "postgres": "postgres",
    "postgres-smoke": "postgres",
    "kafka": "kafka",
    "kafka-smoke": "kafka",
    "grafana": "grafana",
    "postgres-exporter": "postgres-exporter",
}
IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")
STATEFUL_VOLUMES = {
    "dcim-build-postgres-data", "dcim-build-kafka-data", "dcim-build-prometheus-data",
}
EXPECTED_VOLUME_MOUNTS = {
    "postgres": {("postgres-data", "/var/lib/postgresql/data", False)},
    "kafka": {("kafka-data", "/var/lib/kafka/data", False)},
    "prometheus": {("prometheus-data", "/prometheus", False)},
}
EXPECTED_KAFKA_ENVIRONMENT = {
    "KAFKA_NODE_ID": "1",
    "KAFKA_PROCESS_ROLES": "broker,controller",
    "KAFKA_LISTENERS": "CONTROLLER://:9093,PLAINTEXT://:9092",
    "KAFKA_ADVERTISED_LISTENERS": "PLAINTEXT://kafka:9092",
    "KAFKA_CONTROLLER_LISTENER_NAMES": "CONTROLLER",
    "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP": "CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT",
    "KAFKA_CONTROLLER_QUORUM_VOTERS": "1@kafka:9093",
    "KAFKA_INTER_BROKER_LISTENER_NAME": "PLAINTEXT",
    "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR": "1",
    "KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR": "1",
    "KAFKA_TRANSACTION_STATE_LOG_MIN_ISR": "1",
    "KAFKA_AUTO_CREATE_TOPICS_ENABLE": "false",
    "KAFKA_MESSAGE_MAX_BYTES": "1048576",
    "KAFKA_REPLICA_FETCH_MAX_BYTES": "1048576",
    "KAFKA_LOG_RETENTION_HOURS": "24",
    "KAFKA_LOG_SEGMENT_BYTES": "268435456",
    "KAFKA_LOG_DIRS": "/var/lib/kafka/data",
    "KAFKA_JMX_HOSTNAME": "kafka",
    "KAFKA_JMX_PORT": "9999",
}
def health_contract(test: list[str], start_period: str = "20s") -> dict[str, object]:
    return {
        "test": test,
        "interval": "10s",
        "timeout": "5s",
        "retries": 12,
        "start_period": start_period,
    }


EXPECTED_HEALTHCHECKS = {
    "postgres": health_contract([
        "CMD-SHELL", "pg_isready -U dcim_bootstrap -d dcim_foundation",
    ]),
    "kafka": health_contract([
        "CMD-SHELL",
        "/opt/kafka/bin/kafka-metadata-quorum.sh --bootstrap-server localhost:9092 describe --status >/dev/null",
    ], "40s"),
    "postgres-exporter": health_contract([
        "CMD", "wget", "--spider", "-q", "http://127.0.0.1:9187/metrics",
    ]),
    "kafka-jmx-exporter": health_contract([
        "CMD", "curl", "--fail", "--silent", "--output", "/dev/null",
        "http://127.0.0.1:5556/metrics",
    ]),
    "prometheus": health_contract([
        "CMD", "wget", "--spider", "-q", "http://127.0.0.1:9090/-/ready",
    ]),
    "grafana": health_contract([
        "CMD", "curl", "--fail", "--silent", "--output", "/dev/null",
        "http://127.0.0.1:3000/api/health",
    ]),
    "postgres-smoke": health_contract(["CMD", "psql", "-c", "SELECT 1"]),
    "kafka-smoke": health_contract([
        "CMD", "/opt/kafka/bin/kafka-topics.sh", "--bootstrap-server", "kafka:9092", "--list",
    ]),
    "observability-smoke": health_contract([
        "CMD", "promtool", "check", "rules", "/etc/prometheus/rules.yml",
    ]),
}
SECRET_PATTERN = re.compile(r"(PASSWORD|PASS|TOKEN|SECRET|KEY)", re.IGNORECASE)


def network_names(service: dict[str, object]) -> set[str]:
    networks = service.get("networks", {})
    return set(networks if isinstance(networks, dict) else networks)


def validate_model(
    model: dict[str, object],
    derived_lock: dict[str, object],
    license_dispositions_sha256: str,
    runtime_root: Path,
    project_name: str = "dcim-build",
) -> list[str]:
    errors: list[str] = []
    try:
        validate_compose_project_name(project_name)
    except ValueError as error:
        errors.append(str(error))
    if model.get("name") != project_name:
        errors.append(f"Compose project name must be {project_name}")
    try:
        inventory = load_object(IMAGE_INVENTORY)
        approved_images = {item["component"]: item["image"] for item in inventory["images"]}
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        return [f"image inventory invalid: {error}"]
    try:
        if derived_lock.get("schema_version") != 2 or derived_lock.get("publication") is not False:
            raise ValueError("schema/publication policy mismatch")
        if derived_lock.get("manifest_sha256") != hashlib.sha256(IMAGE_RECIPES.read_bytes()).hexdigest():
            raise ValueError("recipe manifest digest mismatch")
        if derived_lock.get("license_dispositions_sha256") != license_dispositions_sha256:
            raise ValueError("license disposition digest mismatch")
        derived_images = {
            item["component"]: item["image_id"] for item in derived_lock["images"]
        }
        if set(derived_images) != {"postgres", "kafka", "grafana", "postgres-exporter"}:
            raise ValueError("derived component allowlist mismatch")
        if any(not isinstance(image, str) or not IMAGE_ID.fullmatch(image) for image in derived_images.values()):
            raise ValueError("invalid derived image ID")
    except (KeyError, TypeError, ValueError) as error:
        return [f"derived image lock invalid: {error}"]
    services = model.get("services", {})
    if not isinstance(services, dict):
        return ["services must be an object"]
    unexpected = set(services) - ALLOWED_SERVICES
    missing = ALLOWED_SERVICES - set(services)
    if unexpected:
        errors.append(f"unexpected or prohibited services: {sorted(unexpected)}")
    if missing:
        errors.append(f"missing required services: {sorted(missing)}")

    total_cpus = 0.0
    total_memory = 0

    for name, value in services.items():
        if not isinstance(value, dict):
            errors.append(f"{name}: service must be an object")
            continue
        image = value.get("image", "")
        derived_component = DERIVED_COMPONENT_BY_SERVICE.get(name)
        if derived_component:
            immutable = isinstance(image, str) and bool(IMAGE_ID.fullmatch(image))
            expected_image = derived_images.get(derived_component)
        else:
            immutable = isinstance(image, str) and bool(re.search(r":[^@]+@sha256:[0-9a-f]{64}$", image))
            expected_image = approved_images.get(IMAGE_COMPONENT_BY_SERVICE.get(name, ""))
        if not immutable:
            errors.append(f"{name}: image must use exact version and immutable digest")
        if image != expected_image:
            errors.append(f"{name}: image inventory allowlist mismatch")
        profiles = value.get("profiles", [])
        if set(profiles) != EXPECTED_PROFILES.get(name, set()):
            errors.append(f"{name}: exact profile membership required")
        if value.get("privileged"):
            errors.append(f"{name}: privileged mode prohibited")
        if any(value.get(field) for field in ("network_mode", "pid", "ipc")):
            errors.append(f"{name}: external namespace prohibited")
        if value.get("devices") or value.get("cap_add") or value.get("device_cgroup_rules"):
            errors.append(f"{name}: device or added capability prohibited")
        if value.get("group_add"):
            errors.append(f"{name}: supplemental groups prohibited")
        if value.get("use_api_socket") or value.get("configs") or value.get("volumes_from"):
            errors.append(f"{name}: alternate host mount channel prohibited")
        if any(value.get(field) for field in ("userns_mode", "uts", "cgroup", "cgroup_parent")):
            errors.append(f"{name}: host-adjacent namespace or cgroup setting prohibited")
        if set(value.get("cap_drop", [])) != {"ALL"}:
            errors.append(f"{name}: all capabilities must be dropped")
        if set(value.get("security_opt", [])) != {"no-new-privileges:true"}:
            errors.append(f"{name}: exact no-new-privileges security option required")
        if value.get("read_only") is not True:
            errors.append(f"{name}: read-only root filesystem required")
        for entry in value.get("tmpfs", []) or []:
            if not str(entry).startswith("/"):
                errors.append(f"{name}: invalid tmpfs mount target")
        if str(value.get("user")) != EXPECTED_USERS.get(name):
            errors.append(f"{name}: exact reviewed UID:GID required")
        service_secrets = {
            (str(item.get("source")), str(item.get("target")))
            for item in (value.get("secrets", []) or []) if isinstance(item, dict)
        }
        if service_secrets != EXPECTED_SECRETS.get(name, set()):
            errors.append(f"{name}: service secret allowlist mismatch")
        if value.get("healthcheck") != EXPECTED_HEALTHCHECKS.get(name):
            errors.append(f"{name}: health contract mismatch")
        limits = value.get("deploy", {}).get("resources", {}).get("limits", {})
        if not limits.get("cpus") or not limits.get("memory"):
            errors.append(f"{name}: CPU and memory limits required")
        else:
            try:
                total_cpus += float(limits["cpus"])
                total_memory += int(limits["memory"])
            except (TypeError, ValueError):
                errors.append(f"{name}: CPU and memory limits must be normalized numbers")
        logging = value.get("logging", {})
        options = logging.get("options", {}) if isinstance(logging, dict) else {}
        if logging.get("driver") != "json-file" or str(options.get("max-size")) != "10m" or str(options.get("max-file")) != "3":
            errors.append(f"{name}: bounded json-file logging required")
        if name in LONG_RUNNING and str(value.get("restart")) != "on-failure:3":
            errors.append(f"{name}: bounded restart policy required")
        if name not in LONG_RUNNING and value.get("restart") not in (None, "no"):
            errors.append(f"{name}: one-shot client must not restart")

        attached = network_names(value)
        if attached != EXPECTED_NETWORKS.get(name, set()):
            errors.append(f"{name}: network membership mismatch")
        if len(attached) > 1 and name not in DUAL_HOMED:
            errors.append(f"{name}: unexpected dual-homed service")
        if name in DUAL_HOMED:
            if attached != {"data", "observability"}:
                errors.append(f"{name}: exporter must attach to exact dual networks")
            if str(value.get("sysctls", {}).get("net.ipv4.ip_forward")) != "0":
                errors.append(f"{name}: IP forwarding must be disabled")
            process = (
                tuple(str(item) for item in (value.get("command") or [])),
                tuple(str(item) for item in (value.get("entrypoint") or [])),
            )
            if process != EXPECTED_EXPORTER_PROCESS[name]:
                errors.append(f"{name}: reviewed exporter process mismatch")
        if name == "prometheus" and (
            tuple(str(item) for item in (value.get("command") or []))
            != EXPECTED_PROMETHEUS_COMMAND
            or value.get("entrypoint") not in (None, [])
        ):
            errors.append("prometheus: Prometheus runtime contract mismatch")

        if value.get("ports"):
            errors.append(f"{name}: unexpected published port")

        environment = value.get("environment", {}) or {}
        if name == "kafka":
            fixed_environment = {
                key: str(environment.get(key, "")) for key in EXPECTED_KAFKA_ENVIRONMENT
            }
            cluster_id = str(environment.get("CLUSTER_ID", ""))
            if (
                set(environment) != {*EXPECTED_KAFKA_ENVIRONMENT, "CLUSTER_ID"}
                or fixed_environment != EXPECTED_KAFKA_ENVIRONMENT
                or not re.fullmatch(r"[A-Za-z0-9_-]{22}", cluster_id)
            ):
                errors.append("kafka: Kafka runtime contract mismatch")
        for key, environment_value in environment.items():
            if (
                SECRET_PATTERN.search(str(key))
                and not str(key).endswith("_FILE")
                and str(key) != "PGPASSFILE"
            ):
                errors.append(f"{name}: secret environment {key} prohibited")
            if "${" in str(environment_value):
                errors.append(f"{name}: unresolved environment placeholder prohibited")
        volume_mounts: set[tuple[str, str, bool]] = set()
        for mount in value.get("volumes", []) or []:
            source = mount.get("source", "") if isinstance(mount, dict) else str(mount).split(":", 1)[0]
            target = mount.get("target", "") if isinstance(mount, dict) else str(mount)
            source_text = str(source)
            target_text = str(target)
            if isinstance(mount, dict) and mount.get("type") == "volume":
                volume_mounts.add((source_text, target_text, bool(mount.get("read_only"))))
            if any(
                marker in source_text or marker in target_text
                for marker in ("docker.sock", "/proc/", "/sys/", "/dev/")
            ):
                errors.append(f"{name}: Docker socket mount prohibited")
            if isinstance(mount, dict) and mount.get("type") == "bind":
                if not mount.get("read_only"):
                    errors.append(f"{name}: writable bind mount prohibited ({source})")
                expected_source = ALLOWED_BIND_TARGETS.get(target_text)
                source_path = Path(source_text).resolve()
                runtime_artifact = (
                    target_text == RUNTIME_ARTIFACT_TARGET
                    and source_path == protected_runtime_path(
                        runtime_root,
                        "dev-build", "artifacts", "jmx_prometheus_standalone-1.6.0.jar",
                    ).resolve()
                )
                if (expected_source is None or source_path != expected_source.resolve()) and not runtime_artifact:
                    errors.append(f"{name}: bind source/target not allowlisted")
        if volume_mounts != EXPECTED_VOLUME_MOUNTS.get(name, set()):
            errors.append(f"{name}: volume mount allowlist mismatch")

    if total_cpus > 10:
        errors.append(f"aggregate CPU limit exceeds 10 ({total_cpus:g})")
    if total_memory > 18 * 1024**3:
        errors.append(f"aggregate memory limit exceeds 18 GiB ({total_memory} bytes)")

    networks = model.get("networks", {})
    if set(networks) != {"data", "observability"}:
        errors.append("network allowlist mismatch")
    expected_network_names = {
        "data": f"{project_name}-data",
        "observability": f"{project_name}-observability",
    }
    for name, value in networks.items():
        if name not in {"data", "observability"} or value.get("internal") is not True:
            errors.append(f"{name}: only approved internal networks permitted")
        if value.get("name") != expected_network_names.get(name):
            errors.append(f"{name}: network runtime name mismatch")
    expected_stateful_volumes = {
        f"{project_name}-postgres-data",
        f"{project_name}-kafka-data",
        f"{project_name}-prometheus-data",
    }
    volume_names = {value.get("name", name) for name, value in model.get("volumes", {}).items()}
    if project_name == "dcim-build" and volume_names != STATEFUL_VOLUMES:
        errors.append("persistent volume allowlist mismatch")
    elif project_name != "dcim-build" and volume_names != expected_stateful_volumes:
        errors.append("persistent volume allowlist mismatch")
    if model.get("configs"):
        errors.append("top-level configs prohibited")
    secrets = model.get("secrets", {})
    if set(secrets) != SECRET_NAMES:
        errors.append("top-level secret allowlist mismatch")
    for name, secret in secrets.items():
        source = Path(str(secret.get("file", ""))).resolve() if isinstance(secret, dict) else Path()
        expected_source = protected_runtime_path(
            runtime_root, "dev-build", "secrets", name,
        ).resolve()
        if (
            not isinstance(secret, dict)
            or secret.get("name") != f"{project_name}_{name}"
            or source != expected_source
        ):
            errors.append(f"{name}: top-level secret source prohibited")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--derived-lock", required=True, type=Path)
    parser.add_argument("--license-dispositions", required=True, type=Path)
    parser.add_argument("--project-name", default="dcim-build")
    arguments = parser.parse_args()
    try:
        raw = sys.stdin.read() if arguments.input == "-" else Path(arguments.input).read_text(encoding="utf-8")
        model = loads_object(raw, "normalized Compose model")
        selected_runtime_root = external_runtime_root(arguments.runtime_root)
        expected_lock = protected_runtime_path(
            selected_runtime_root, "dev-build", "derived-images-lock.json",
        ).resolve()
        if arguments.derived_lock.expanduser().resolve() != expected_lock:
            raise ValueError("derived image lock must match selected runtime root")
        derived_lock = load_object(expected_lock)
        license_dispositions_sha256 = hashlib.sha256(
            arguments.license_dispositions.read_bytes()
        ).hexdigest()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"foundation-policy: invalid input: {error}", file=sys.stderr)
        return 2
    errors = validate_model(
        model, derived_lock, license_dispositions_sha256, selected_runtime_root,
        arguments.project_name,
    )
    if errors:
        for error in errors:
            print(f"foundation-policy: {error}", file=sys.stderr)
        return 1
    print("foundation-policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
