"""Phase 0 scaffold for the CMDB service."""


def describe() -> dict:
    """Return the static scaffold description."""
    return {
        "service": "cmdb",
        "boundary": "configuration-item identity, relationships, history, and context",
        "status": "phase0-scaffold",
    }


def create_app() -> None:
    """Application factory placeholder. Not implemented in Phase 0."""
    raise NotImplementedError("create_app() is not implemented in Phase 0")
