from __future__ import annotations

from collections.abc import Callable, Mapping
import json
import os
from pathlib import Path
import subprocess
from typing import Final, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CONTAINER_PROJECT: Final = "dcim-build"
DEFAULT_TIMEOUT_SECONDS: Final = 10.0


class SmokeFailure(RuntimeError):
    pass


class HttpClient(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        internal_token: str | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> tuple[int, bytes]: ...


class UrllibClient:
    def __init__(self, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout

    def request(
        self,
        method: str,
        url: str,
        *,
        internal_token: str | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> tuple[int, bytes]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(url, method=method, data=body)
        if internal_token is not None:
            request.add_header("X-Internal-Token", internal_token)
        if body is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urlopen(request, timeout=self._timeout) as response:
                return response.status, response.read()
        except HTTPError as error:
            return error.code, error.read()
        except URLError as error:
            raise SmokeFailure("service connection failed") from error


AddressResolver = Callable[[str], str]


def inspect_address(service: str) -> str:
    result = subprocess.run(
        [
            "docker", "inspect", "-f",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}",
            f"{CONTAINER_PROJECT}-{service}-1",
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    addresses = result.stdout.split() if result.returncode == 0 else []
    if not addresses:
        raise SmokeFailure(f"{service}: no reachable container address")
    return addresses[0]


def read_token(path: Path) -> str:
    try:
        credential = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise SmokeFailure("internal token file is unavailable") from error
    if not credential:
        raise SmokeFailure("internal token file is empty")
    return credential


def default_token_file() -> Path:
    runtime_root = os.environ.get("DCIM_RUNTIME_ROOT")
    if runtime_root:
        return Path(runtime_root) / "dev-build" / "secrets" / "internal-api-token"
    return Path("/run/secrets/internal-api-token")
