from __future__ import annotations

from dataclasses import dataclass
from typing import cast
from urllib.response import addinfourl
from urllib.request import urlopen


CORE_SERVICES = ("asset-repository", "cmdb")
CORE_PATHS = ("/health", "/ready")


@dataclass(frozen=True)
class Check:
    service: str
    path: str


def core_checks() -> tuple[Check, ...]:
    return tuple(Check(service, path) for service in CORE_SERVICES for path in CORE_PATHS)


def check_core_services(*, timeout: float = 5.0) -> None:
    for check in core_checks():
        response = cast(addinfourl, urlopen(f"http://{check.service}:8000{check.path}", timeout=timeout))
        with response:
            status = response.status
        if status == 200:
            continue
        raise RuntimeError(f"{check.service}{check.path} returned {status}")
