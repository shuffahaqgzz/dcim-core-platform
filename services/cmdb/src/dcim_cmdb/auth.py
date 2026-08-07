"""Development internal-token authentication policy."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from secrets import compare_digest


@dataclass(frozen=True, slots=True)
class AuthConfigurationError(RuntimeError):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class InternalTokenAuth:
    required: bool
    expected_value: str = ""

    def permits(self, candidate: str | None) -> bool:
        return not self.required or (
            candidate is not None and compare_digest(candidate, self.expected_value)
        )


def load_internal_token_auth() -> InternalTokenAuth:
    """Load the required shared token from its owner-only runtime file."""
    if os.environ.get("DCIM_AUTH_REQUIRED", "false").casefold() != "true":
        return InternalTokenAuth(required=False)
    try:
        expected_value = Path(os.environ.get("INTERNAL_API_TOKEN_FILE", "/run/secrets/internal-api-token")).read_text(encoding="utf-8").strip()
    except OSError as error:
        raise AuthConfigurationError("required internal-token file is unavailable") from error
    if not expected_value:
        raise AuthConfigurationError("required internal-token file is empty")
    return InternalTokenAuth(required=True, expected_value=expected_value)
