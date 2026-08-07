#!/usr/bin/env python3
"""Phase 3 service smoke: health, readiness, metrics, and auth-boundary proof.

Runs on the Docker host against the five Development application services
through their in-plane container addresses (no published host ports exist).
The internal token is read from a protected file and is never written to
stdout, stderr, or the evidence document.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Final

if __package__ in (None, ""):
    script_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(script_root))

from scripts.phase3 import (
    AddressResolver,
    HttpClient,
    SmokeFailure,
    UrllibClient,
    default_token_file,
    inspect_address,
    read_token,
)


SERVICES: Final = ("asset-repository", "cmdb", "api", "analytics", "workflow")
API_PROBES: Final = {
    "asset-repository": "/api/v1/assets",
    "cmdb": "/api/v1/cis",
    "api": "/api/v1/dashboard/noc-cards",
    "analytics": "/api/v1/analytics/health",
    "workflow": "/api/v1/workflows/drafts",
}
ANALYTICS_ENDPOINTS: Final = (
    "/api/v1/analytics/health",
    "/api/v1/analytics/freshness",
    "/api/v1/analytics/capacity",
    "/api/v1/analytics/quality",
)
SMOKE_ASSET: Final = {
    "identity": {"manufacturer": "SmokeVendor", "serial_number": "SMOKE-SYNTHETIC-0001"},
    "asset_type": "synthetic-smoke",
    "aliases": [],
    "created_at": "2026-08-03T00:00:00Z",
    "updated_at": "2026-08-03T00:00:00Z",
}
SMOKE_DRAFT: Final = {
    "draft_type": "notification",
    "context": {"source": "service-smoke", "synthetic": True},
}
DEFAULT_TIMEOUT_SECONDS: Final = 10.0


def _json_object(raw: bytes, context: str) -> dict[str, object]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SmokeFailure(f"{context}: response is not valid JSON") from error
    if not isinstance(value, dict):
        raise SmokeFailure(f"{context}: response is not a JSON object")
    return value


def check_service(
    client: HttpClient,
    service: str,
    base_url: str,
) -> dict[str, object]:
    """Prove liveness, readiness, metrics, and the deny-by-default boundary."""
    result: dict[str, object] = {}
    status, _ = client.request("GET", f"{base_url}/health")
    if status == 200:
        result["health"] = status
    else:
        raise SmokeFailure(f"/health returned {status}")
    status, _ = client.request("GET", f"{base_url}/ready")
    if status != 200:
        raise SmokeFailure(f"/ready returned {status}")
    result["ready"] = status
    status, body = client.request("GET", f"{base_url}/metrics")
    if status != 200 or not body.strip():
        raise SmokeFailure(f"/metrics empty or status {status}")
    result["metrics_bytes"] = len(body)
    status, _ = client.request("GET", f"{base_url}{API_PROBES[service]}")
    if status != 403:
        raise SmokeFailure(f"unauthenticated /api/* probe returned {status}")
    result["auth_denial"] = status
    return result


def gateway_round_trip(client: HttpClient, base_url: str, internal_token: str) -> dict[str, object]:
    """Create then read one synthetic asset through the gateway facade."""
    create_status, create_body = client.request(
        "POST", f"{base_url}/api/v1/assets", internal_token=internal_token, payload=SMOKE_ASSET,
    )
    if create_status not in (200, 201):
        raise SmokeFailure(f"api: gateway asset create returned {create_status}")
    asset = _json_object(create_body, "api: gateway asset create")
    asset_id = asset.get("asset_id")
    if not isinstance(asset_id, str):
        raise SmokeFailure("api: gateway asset create returned no asset_id")
    get_status, get_body = client.request("GET", f"{base_url}/api/v1/assets/{asset_id}", internal_token=internal_token)
    if get_status != 200:
        raise SmokeFailure(f"api: gateway asset read returned {get_status}")
    fetched = _json_object(get_body, "api: gateway asset read")
    if fetched.get("asset_id") != asset_id:
        raise SmokeFailure("api: gateway asset read returned a different asset_id")
    return {"create_status": create_status, "get_status": get_status, "asset_id": asset_id}


def workflow_lifecycle(client: HttpClient, base_url: str, internal_token: str) -> dict[str, object]:
    """Drive one draft through creation, simulation, and terminal rejection."""
    create_status, create_body = client.request(
        "POST", f"{base_url}/api/v1/workflows/drafts", internal_token=internal_token, payload=SMOKE_DRAFT,
    )
    if create_status != 201:
        raise SmokeFailure(f"workflow: draft create returned {create_status}")
    draft = _json_object(create_body, "workflow: draft create")
    draft_id = draft.get("draft_id")
    if not isinstance(draft_id, str):
        raise SmokeFailure("workflow: draft create returned no draft_id")
    simulate_status, simulate_body = client.request(
        "POST",
        f"{base_url}/api/v1/workflows/drafts/{draft_id}/simulate",
        internal_token=internal_token,
        payload={"decision": "approve"},
    )
    if simulate_status != 200:
        raise SmokeFailure(f"workflow: draft simulate returned {simulate_status}")
    simulated = _json_object(simulate_body, "workflow: draft simulate")
    if simulated.get("status") != "simulated_approved":
        raise SmokeFailure("workflow: draft did not reach simulated_approved")
    terminal_status, _ = client.request(
        "POST",
        f"{base_url}/api/v1/workflows/drafts/{draft_id}/simulate",
        internal_token=internal_token,
        payload={"decision": "reject"},
    )
    if terminal_status != 409:
        raise SmokeFailure(f"workflow: terminal re-simulate returned {terminal_status}")
    return {
        "create_status": create_status,
        "simulate_status": simulate_status,
        "final_status": simulated["status"],
        "terminal_status": terminal_status,
        "draft_id": draft_id,
    }


def analytics_endpoints(client: HttpClient, base_url: str, internal_token: str) -> dict[str, object]:
    results: dict[str, object] = {}
    for endpoint in ANALYTICS_ENDPOINTS:
        status, body = client.request("GET", f"{base_url}{endpoint}", internal_token=internal_token)
        if status != 200:
            raise SmokeFailure(f"analytics: {endpoint} returned {status}")
        _json_object(body, f"analytics: {endpoint}")
        results[endpoint.rsplit("/", 1)[-1]] = status
    return results


def run_smoke(
    client: HttpClient,
    resolve: AddressResolver,
    internal_token: str,
    *,
    generated_at: str | None = None,
) -> dict[str, object]:
    """Run every smoke check and return the redacted evidence document."""
    addresses = {service: resolve(service) for service in SERVICES}
    evidence: dict[str, object] = {
        "generated_at": generated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "services": {},
    }
    services: dict[str, object] = {}
    for service in SERVICES:
        try:
            services[service] = check_service(client, service, f"http://{addresses[service]}:8000")
        except SmokeFailure as error:
            raise SmokeFailure(f"{service}: {error}") from error
    evidence["services"] = services
    evidence["healthy_services"] = sum(
        1 for result in services.values() if isinstance(result, dict) and result.get("health") == 200
    )
    evidence["auth_denials"] = sum(
        1 for result in services.values() if isinstance(result, dict) and result.get("auth_denial") == 403
    )
    evidence["gateway_round_trip"] = gateway_round_trip(
        client, f"http://{addresses['api']}:8000", internal_token,
    )
    evidence["workflow_lifecycle"] = workflow_lifecycle(
        client, f"http://{addresses['workflow']}:8000", internal_token,
    )
    evidence["analytics"] = analytics_endpoints(
        client, f"http://{addresses['analytics']}:8000", internal_token,
    )
    return evidence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token-file", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    token_file = arguments.token_file or default_token_file()
    try:
        credential = read_token(token_file)
        evidence = run_smoke(UrllibClient(arguments.timeout), inspect_address, credential)
    except SmokeFailure as error:
        print(f"service-smoke: FAIL: {error}", file=sys.stderr)
        return 1
    evidence["token_file"] = str(token_file)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    healthy = evidence.get("healthy_services")
    denials = evidence.get("auth_denials")
    print(f"service-smoke: PASS services={healthy}/5 auth-denials={denials}/5 evidence={arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
