#!/usr/bin/env python3
"""Validate normalized dcim-build Compose JSON without persisting secrets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


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
ALLOWED_SERVICES = {
    "postgres", "kafka", "prometheus", "grafana", "postgres-exporter",
    "kafka-jmx-exporter", "postgres-smoke", "kafka-smoke", "observability-smoke",
}
LONG_RUNNING = {
    "postgres", "kafka", "prometheus", "grafana", "postgres-exporter",
    "kafka-jmx-exporter",
}
DUAL_HOMED = {"postgres-exporter", "kafka-jmx-exporter"}
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
SECRET_PATTERN = re.compile(r"(PASSWORD|PASS|TOKEN|SECRET|KEY)", re.IGNORECASE)


def network_names(service: dict[str, object]) -> set[str]:
    networks = service.get("networks", {})
    return set(networks if isinstance(networks, dict) else networks)


def validate_model(model: dict[str, object], derived_lock: dict[str, object]) -> list[str]:
    errors: list[str] = []
    try:
        inventory = json.loads(IMAGE_INVENTORY.read_text(encoding="utf-8"))
        approved_images = {item["component"]: item["image"] for item in inventory["images"]}
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        return [f"image inventory invalid: {error}"]
    try:
        if derived_lock.get("schema_version") != 1 or derived_lock.get("publication") is not False:
            raise ValueError("schema/publication policy mismatch")
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
        if value.get("network_mode") == "host" or value.get("pid") == "host" or value.get("ipc") == "host":
            errors.append(f"{name}: host namespace prohibited")
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
        if not value.get("healthcheck"):
            errors.append(f"{name}: health check required")
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
        if len(attached) > 1 and name not in DUAL_HOMED:
            errors.append(f"{name}: unexpected dual-homed service")
        if name in DUAL_HOMED:
            if attached != {"data", "observability"}:
                errors.append(f"{name}: exporter must attach to exact dual networks")
            if str(value.get("sysctls", {}).get("net.ipv4.ip_forward")) != "0":
                errors.append(f"{name}: IP forwarding must be disabled")

        if value.get("ports"):
            errors.append(f"{name}: unexpected published port")

        environment = value.get("environment", {}) or {}
        for key, environment_value in environment.items():
            if (
                SECRET_PATTERN.search(str(key))
                and not str(key).endswith("_FILE")
                and str(key) != "PGPASSFILE"
            ):
                errors.append(f"{name}: secret environment {key} prohibited")
            if "${" in str(environment_value):
                errors.append(f"{name}: unresolved environment placeholder prohibited")
        for mount in value.get("volumes", []) or []:
            source = mount.get("source", "") if isinstance(mount, dict) else str(mount).split(":", 1)[0]
            target = mount.get("target", "") if isinstance(mount, dict) else str(mount)
            source_text = str(source)
            target_text = str(target)
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
                    and source_path.as_posix().endswith(
                        "/dev-build/artifacts/jmx_prometheus_standalone-1.6.0.jar"
                    )
                    and ROOT not in source_path.parents
                )
                if (expected_source is None or source_path != expected_source.resolve()) and not runtime_artifact:
                    errors.append(f"{name}: bind source/target not allowlisted")

    if total_cpus > 10:
        errors.append(f"aggregate CPU limit exceeds 10 ({total_cpus:g})")
    if total_memory > 18 * 1024**3:
        errors.append(f"aggregate memory limit exceeds 18 GiB ({total_memory} bytes)")

    networks = model.get("networks", {})
    if set(networks) != {"data", "observability"}:
        errors.append("network allowlist mismatch")
    for name, value in networks.items():
        if name not in {"data", "observability"} or value.get("internal") is not True:
            errors.append(f"{name}: only approved internal networks permitted")
    volume_names = {value.get("name", name) for name, value in model.get("volumes", {}).items()}
    if volume_names != STATEFUL_VOLUMES:
        errors.append("persistent volume allowlist mismatch")
    if model.get("configs"):
        errors.append("top-level configs prohibited")
    secrets = model.get("secrets", {})
    if set(secrets) != SECRET_NAMES:
        errors.append("top-level secret allowlist mismatch")
    for name, secret in secrets.items():
        source = Path(str(secret.get("file", ""))).resolve() if isinstance(secret, dict) else Path()
        if (
            not isinstance(secret, dict)
            or secret.get("name") != f"dcim-build_{name}"
            or not source.as_posix().endswith(f"/dev-build/secrets/{name}")
            or ROOT in source.parents
        ):
            errors.append(f"{name}: top-level secret source prohibited")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--derived-lock", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        raw = sys.stdin.read() if arguments.input == "-" else Path(arguments.input).read_text(encoding="utf-8")
        model = json.loads(raw)
        derived_lock = json.loads(arguments.derived_lock.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"foundation-policy: invalid input: {error}", file=sys.stderr)
        return 2
    errors = validate_model(model, derived_lock)
    if errors:
        for error in errors:
            print(f"foundation-policy: {error}", file=sys.stderr)
        return 1
    print("foundation-policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
