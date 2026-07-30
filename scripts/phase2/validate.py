"""Canonical envelope validation, hashing, and atomic disposition."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import assert_never

from pydantic import ValidationError

from contracts.python.dcim_contracts.disposition import (
    ClaimStore,
    Disposition,
    JsonValue,
    ReasonCode,
)
from contracts.python.dcim_contracts.envelope import Envelope

from .ledger import DispositionLedger


class DispositionEngine:
    """Validates each candidate before one atomic claim and terminal ledger entry."""

    def __init__(self, store: ClaimStore, ledger: DispositionLedger) -> None:
        self._store = store
        self._ledger = ledger

    def handle(self, candidate: Mapping[str, JsonValue]) -> Disposition:
        """Validate, canonically hash, claim, and classify one candidate."""
        self._ledger.record("received")
        try:
            validated = Envelope.model_validate(candidate, strict=True)
        except ValidationError as error:
            reason: ReasonCode = (
                "payload_invalid"
                if any(item["type"] == "payload_invalid" for item in error.errors())
                else "schema_invalid"
            )
            self._ledger.record("quarantined")
            return Disposition(
                status="quarantined",
                reason=reason,
                canonical=None,
                content_sha256=None,
            )

        canonical = validated.model_dump(mode="json", round_trip=True)
        content = json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        content_sha256 = hashlib.sha256(content).hexdigest()
        claim = self._store.try_claim(validated.event_id, content_sha256)

        match claim:
            case "new":
                self._ledger.record("accepted")
                return Disposition(
                    status="accepted",
                    reason=None,
                    canonical=canonical,
                    content_sha256=content_sha256,
                )
            case "duplicate":
                self._ledger.record("duplicate")
                return Disposition(
                    status="duplicate",
                    reason=None,
                    canonical=canonical,
                    content_sha256=content_sha256,
                )
            case "conflict":
                self._ledger.record("quarantined")
                return Disposition(
                    status="quarantined",
                    reason="event_id_content_conflict",
                    canonical=canonical,
                    content_sha256=content_sha256,
                )
            case unreachable:
                assert_never(unreachable)
