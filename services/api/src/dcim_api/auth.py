"""Shared Development internal-token authentication policy."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from secrets import compare_digest


@dataclass(frozen=True, slots=True)
class AuthConfigurationError(RuntimeError):
    """Required authentication configuration is unavailable."""

    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class InternalTokenAuth:
    """Deny protected requests unless the configured token matches."""

    required: bool
    expected_value: str = ""

    def permits(self, candidate: str | None) -> bool:
        if not self.required:
            return True
        return candidate is not None and compare_digest(candidate, self.expected_value)


def load_internal_token_auth() -> InternalTokenAuth:
    """Load the shared token from a file when authentication is required."""
    required = os.environ.get("DCIM_AUTH_REQUIRED", "false").casefold() == "true"
    if not required:
        return InternalTokenAuth(required=False)
    path = Path(
        os.environ.get(
            "INTERNAL_API_TOKEN_FILE",
            "/run/secrets/internal-api-token",
        )
    )
    try:
        expected_value = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise AuthConfigurationError(
            "required internal-token file is unavailable"
        ) from error
    if not expected_value:
        raise AuthConfigurationError("required internal-token file is empty")
    return InternalTokenAuth(required=True, expected_value=expected_value)
