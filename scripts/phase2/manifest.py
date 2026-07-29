"""Immutable, fail-closed run manifests for synthetic Phase 2 inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Mapping, TypedDict

from .errors import ManifestDriftError


class StoredSource(TypedDict):
    """Canonical JSON representation of one source fixture."""

    name: str
    fixture_path: str
    sha256: str


class StoredManifest(TypedDict):
    """Canonical JSON representation of a complete run manifest."""

    run_id: str
    fixed_clock: str
    sources: list[StoredSource]
    source_count: int
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """One fixture included in an immutable pipeline run."""

    name: str
    fixture_path: str
    sha256: str

    def to_json(self) -> StoredSource:
        """Return canonical JSON-compatible source data."""
        return {
            "name": self.name,
            "fixture_path": self.fixture_path,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Immutable identity and source set for one fixed-clock pipeline run."""

    run_id: str
    fixed_clock: str
    sources: tuple[SourceSpec, ...]
    source_count: int = field(init=False)
    manifest_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_count", len(self.sources))
        object.__setattr__(self, "manifest_sha256", self.compute_sha256())

    def canonical_fields(self) -> dict[str, str | int | list[StoredSource]]:
        """Return fields covered by the manifest digest."""
        return {
            "run_id": self.run_id,
            "fixed_clock": self.fixed_clock,
            "sources": [source.to_json() for source in self.sources],
            "source_count": self.source_count,
        }

    def compute_sha256(self) -> str:
        """Compute SHA-256 over compact, key-sorted canonical manifest JSON."""
        canonical = json.dumps(
            self.canonical_fields(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def to_json(self) -> StoredManifest:
        """Return complete canonical JSON-compatible manifest data."""
        return {
            **self.canonical_fields(),
            "manifest_sha256": self.manifest_sha256,
        }

    def verify_stored(self, stored: Mapping[str, object]) -> None:
        """Reject every stored representation that differs from this manifest."""
        if dict(stored) != self.to_json():
            raise ManifestDriftError("stored manifest differs from immutable run manifest")
