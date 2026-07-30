"""Atomic claim protocol and immutable disposition result types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from .envelope import JsonObject, JsonValue
type ClaimResult = Literal["new", "duplicate", "conflict"]
type DispositionStatus = Literal["accepted", "quarantined", "duplicate"]
type ReasonCode = Literal[
    "schema_invalid",
    "payload_invalid",
    "identity_conflict",
    "event_id_content_conflict",
]


class ClaimStore(Protocol):
    """Atomically classifies a validated event ID and canonical content hash."""

    def try_claim(self, event_id: str, content_sha256: str) -> ClaimResult:
        """Claim an event ID using first-wins semantics."""
        ...


@dataclass(frozen=True, slots=True)
class Disposition:
    """Terminal classification and canonical persistence representation."""

    status: DispositionStatus
    reason: ReasonCode | None
    canonical: JsonObject | None
    content_sha256: str | None
