"""Typed Phase 2 pipeline failures."""


class Phase2Error(Exception):
    """Base class for Phase 2 pipeline failures."""


class ManifestDriftError(Phase2Error):
    """Raised when stored manifest data differs from its run manifest."""


class SilentLossError(Phase2Error):
    """Raised when received items lack a disposition."""


class KillSwitchEngaged(Phase2Error):
    """Raised when a Phase 2 source kill switch is engaged."""
