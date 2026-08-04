"""Typed Phase 2 pipeline failures."""

from dataclasses import dataclass
from typing import override


class Phase2Error(Exception):
    """Base class for Phase 2 pipeline failures."""


class ManifestDriftError(Phase2Error):
    """Raised when stored manifest data differs from its run manifest."""


class DispositionImbalanceError(Phase2Error):
    """Raised when received and terminal in-memory counts differ."""


class KillSwitchEngaged(Phase2Error):
    """Raised when a Phase 2 source kill switch is engaged."""


@dataclass(frozen=True, slots=True)
class ConnectorCeilingError(Phase2Error):
    """Raised when a connector ceiling violates its accepted ADR bound."""

    connector: str
    parameter: str
    value: int
    bound: str
    limit: int

    @override
    def __str__(self) -> str:
        return (
            f"{self.connector} {self.parameter}={self.value} must be "
            f"{self.bound} {self.limit} seconds"
        )


class SqlRenderError(Phase2Error):
    """Raised when validated data cannot be represented safely as SQL."""
