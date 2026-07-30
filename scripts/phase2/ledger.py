"""Disposition accounting that makes silent input loss fail closed."""

from __future__ import annotations

from typing import Literal, TypedDict

from .errors import Phase2Error, SilentLossError


DispositionStatus = Literal["received", "accepted", "quarantined", "duplicate"]


class LedgerJSON(TypedDict):
    """JSON-compatible disposition totals."""

    received: int
    accepted: int
    quarantined: int
    duplicate: int


class DispositionLedger:
    """Mutable accumulator for required per-input dispositions."""

    def __init__(self) -> None:
        self.received = 0
        self.accepted = 0
        self.quarantined = 0
        self.duplicate = 0

    def record(self, status: DispositionStatus) -> None:
        """Count one received input or one terminal disposition."""
        match status:
            case "received":
                self.received += 1
            case "accepted":
                self.accepted += 1
            case "quarantined":
                self.quarantined += 1
            case "duplicate":
                self.duplicate += 1
            case unreachable:
                raise Phase2Error(f"unsupported disposition status: {unreachable}")

    def assert_zero_silent_loss(self) -> None:
        """Raise when received count does not equal accounted dispositions."""
        accounted = self.accepted + self.quarantined + self.duplicate
        if self.received != accounted:
            raise SilentLossError("received inputs do not equal terminal dispositions")

    def to_json(self) -> LedgerJSON:
        """Return current ledger totals as JSON-compatible data."""
        return {
            "received": self.received,
            "accepted": self.accepted,
            "quarantined": self.quarantined,
            "duplicate": self.duplicate,
        }
