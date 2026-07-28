"""Phase 0 scaffold for the Asset Repository service."""


def describe() -> dict:
    """Return the static scaffold description."""
    return {
        "service": "asset-repository",
        "boundary": "stable physical/logical asset identity, lifecycle state, aliases, and public APIs",
        "status": "phase0-scaffold",
    }


def create_app() -> None:
    """Application factory placeholder. Not implemented in Phase 0."""
    raise NotImplementedError("create_app() is not implemented in Phase 0")
