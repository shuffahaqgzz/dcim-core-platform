from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from scripts.phase2.errors import ManifestDriftError
from scripts.phase2.manifest import RunManifest, SourceSpec


ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "fixtures" / "synthetic" / "events"


class RunManifestTests(unittest.TestCase):
    def source(self, filename: str) -> SourceSpec:
        fixture = EVENTS / filename
        with fixture.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        return SourceSpec(
            name=fixture.stem,
            fixture_path=str(fixture.relative_to(ROOT)),
            sha256=digest,
        )

    def manifest(self) -> RunManifest:
        return RunManifest(
            run_id="phase2-synthetic-run-001",
            fixed_clock="2026-07-29T00:00:00Z",
            sources=(
                self.source("p1-redfish-health.json"),
                self.source("p2-nas-capacity.json"),
            ),
        )

    def test_compute_sha256_when_manifest_has_real_fixtures(self) -> None:
        manifest = self.manifest()

        self.assertEqual(2, manifest.source_count)
        self.assertEqual(manifest.manifest_sha256, manifest.compute_sha256())
        self.assertEqual(64, len(manifest.manifest_sha256))

    def test_verify_stored_when_canonical_fields_round_trip(self) -> None:
        manifest = self.manifest()
        stored = {
            "run_id": manifest.run_id,
            "fixed_clock": manifest.fixed_clock,
            "sources": [
                {
                    "name": source.name,
                    "fixture_path": source.fixture_path,
                    "sha256": source.sha256,
                }
                for source in manifest.sources
            ],
            "source_count": manifest.source_count,
            "manifest_sha256": manifest.manifest_sha256,
        }

        manifest.verify_stored(stored)

    def test_verify_stored_when_manifest_hash_is_tampered_raises_drift(self) -> None:
        manifest = self.manifest()
        tampered_hash = "0" + manifest.manifest_sha256[1:]
        stored = {
            "run_id": manifest.run_id,
            "fixed_clock": manifest.fixed_clock,
            "sources": [
                {
                    "name": source.name,
                    "fixture_path": source.fixture_path,
                    "sha256": source.sha256,
                }
                for source in manifest.sources
            ],
            "source_count": manifest.source_count,
            "manifest_sha256": tampered_hash,
        }

        with self.assertRaises(ManifestDriftError):
            manifest.verify_stored(stored)
