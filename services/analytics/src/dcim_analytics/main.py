"""Phase 0 scaffold for the Analytics service."""


def describe() -> dict:
    """Return the static scaffold description."""
    return {
        "service": "analytics",
        "boundary": "transparent Development analytics for health, capacity, freshness, completeness, and quality",
        "status": "phase0-scaffold",
    }


def create_app() -> None:
    """Application factory placeholder. Not implemented in Phase 0."""
    raise NotImplementedError("create_app() is not implemented in Phase 0")
