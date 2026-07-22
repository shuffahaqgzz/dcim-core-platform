from __future__ import annotations

import importlib.util
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/foundation_supply_chain.py"
SPEC = importlib.util.spec_from_file_location("foundation_supply_chain", SCRIPT)
assert SPEC and SPEC.loader
foundation_supply_chain = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = foundation_supply_chain
SPEC.loader.exec_module(foundation_supply_chain)


def license_disposition_manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "recipes_sha256": "a" * 64,
        "decision": {
            "owner": "synthetic-owner",
            "date": "2026-07-20",
            "issue": "#10",
            "scope": "synthetic dcim-build local Development only",
            "publication": False,
            "distribution": False,
            "od_06": "OPEN",
        },
        "dispositions": [
            {
                "component": component,
                "category": "unknown",
                "reviewed_count": 1,
                "inventory_sha256": "a" * 64,
                "disposition": "accepted-local-development-only",
            }
            for component in (
                "postgresql", "apache-kafka", "grafana-oss", "postgresql-exporter",
                "prometheus", "jmx-exporter-java-runtime",
            )
        ],
        "revalidation_triggers": [
            "license-inventory-change",
            "recipe-change",
            "publication-or-distribution-request",
            "od-06-status-change",
            "staging-production-or-handover-request",
        ],
    }


class FoundationSupplyChainTests(unittest.TestCase):
    def test_license_disposition_manifest_is_exact_and_fail_closed(self) -> None:
        manifest = license_disposition_manifest()
        foundation_supply_chain.validate_license_disposition_manifest(manifest, "a" * 64)

        publication_enabled = copy.deepcopy(manifest)
        publication_enabled["decision"]["publication"] = True
        with self.assertRaisesRegex(ValueError, "publication"):
            foundation_supply_chain.validate_license_disposition_manifest(
                publication_enabled, "a" * 64,
            )

        unknown_field = copy.deepcopy(manifest)
        unknown_field["decision"]["approval_note"] = "not governed"
        with self.assertRaisesRegex(ValueError, "fields"):
            foundation_supply_chain.validate_license_disposition_manifest(
                unknown_field, "a" * 64,
            )

    def test_reviewed_license_categories_require_exact_component_category_counts(self) -> None:
        dispositions = {
            "dispositions": [
                {
                    "component": "postgres",
                    "category": "restricted",
                    "reviewed_count": 2,
                    "inventory_sha256": "a" * 64,
                    "disposition": "accepted-local-development-only",
                },
                {
                    "component": "postgres",
                    "category": "unknown",
                    "reviewed_count": 1,
                    "inventory_sha256": "b" * 64,
                    "disposition": "accepted-local-development-only",
                },
            ],
        }
        reviewed = foundation_supply_chain.review_license_categories(
            dispositions,
            "postgres",
            {"notice": 4, "restricted": 2, "unknown": 1},
            {"restricted": "a" * 64, "unknown": "b" * 64},
        )
        self.assertEqual({"restricted": 2, "unknown": 1}, reviewed)

        with self.assertRaisesRegex(ValueError, "new or changed"):
            foundation_supply_chain.review_license_categories(
                dispositions,
                "postgres",
                {"notice": 4, "restricted": 2, "unknown": 1},
                {"restricted": "c" * 64, "unknown": "b" * 64},
            )

    def test_effective_images_substitute_only_approved_derived_components(self) -> None:
        inventory = {"images": [
            {"component": "PostgreSQL", "image": "official-postgres"},
            {"component": "Prometheus", "image": "official-prometheus"},
        ]}
        lock = {"schema_version": 2, "publication": False, "images": [
            {"component": "postgres", "image_id": "sha256:" + "a" * 64},
            {"component": "kafka", "image_id": "sha256:" + "b" * 64},
            {"component": "grafana", "image_id": "sha256:" + "c" * 64},
            {"component": "postgres-exporter", "image_id": "sha256:" + "d" * 64},
            {"component": "prometheus", "image_id": "sha256:" + "e" * 64},
        ]}
        images = foundation_supply_chain.effective_images(inventory, lock)
        self.assertEqual("sha256:" + "a" * 64, images[0]["image"])
        self.assertEqual("sha256:" + "e" * 64, images[1]["image"])

    def test_license_and_sbom_reports_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "license"):
            foundation_supply_chain.validate_license_report({"Results": []})
        with self.assertRaisesRegex(ValueError, "CycloneDX"):
            foundation_supply_chain.validate_sbom({"bomFormat": "CycloneDX", "components": []})

    def test_license_categories_and_sbom_inventory_are_recorded(self) -> None:
        categories = foundation_supply_chain.validate_license_report({
            "Results": [{"Licenses": [
                {"Name": "Apache-2.0", "Category": "notice"},
                {"Name": "AGPL-3.0-only", "Category": "restricted"},
            ]}],
        })
        self.assertEqual({"notice": 1, "restricted": 1}, categories)
        self.assertEqual(1, foundation_supply_chain.validate_sbom({
            "bomFormat": "CycloneDX", "components": [{"name": "synthetic"}],
        }))

    def test_unrecognized_license_categories_fail_closed(self) -> None:
        for category in ("forbidden", "", 7):
            with self.subTest(category=category):
                with self.assertRaisesRegex(ValueError, "category"):
                    foundation_supply_chain.validate_license_report({
                        "Results": [{"Licenses": [{
                            "Name": "Synthetic-License",
                            "Category": category,
                        }]}],
                    })

    def test_database_snapshot_rejects_duplicate_metadata_members(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "evidence"
            cache = root / "cache"
            (cache / "db").mkdir(parents=True)
            (cache / "java-db").mkdir(parents=True)
            (cache / "db/trivy.db").write_bytes(b"synthetic-db")
            (cache / "java-db/trivy-java.db").write_bytes(b"synthetic-java-db")
            (cache / "db/metadata.json").write_text(
                '{"UpdatedAt":"first","UpdatedAt":"second","NextUpdate":"later"}',
                encoding="utf-8",
            )
            (cache / "java-db/metadata.json").write_text(
                '{"UpdatedAt":"first","NextUpdate":"later"}',
                encoding="utf-8",
            )

            with mock.patch.object(foundation_supply_chain, "run_scan"):
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    foundation_supply_chain.database_snapshot(evidence, cache)

    def test_license_fingerprint_detects_package_version_change(self) -> None:
        report = {
            "Results": [{"Licenses": [{
                "Name": "Synthetic-1.0",
                "Category": "restricted",
                "PkgName": "synthetic-package",
                "PkgVersion": "1.0.0",
                "PkgIdentifier": "pkg:generic/synthetic-package@1.0.0",
                "FilePath": "/synthetic/package",
            }]}],
        }
        changed = copy.deepcopy(report)
        changed["Results"][0]["Licenses"][0]["PkgVersion"] = "2.0.0"
        self.assertNotEqual(
            foundation_supply_chain.license_category_fingerprints(report),
            foundation_supply_chain.license_category_fingerprints(changed),
        )

    def test_missing_results_cannot_pass(self) -> None:
        with self.assertRaisesRegex(ValueError, "Results"):
            foundation_supply_chain.blocking_counts({})

    def test_unrecognized_vulnerability_severities_fail_closed(self) -> None:
        for severity in (None, 7, "", " critical ", "BLOCKER"):
            with self.subTest(severity=severity):
                with self.assertRaisesRegex(ValueError, "severity"):
                    foundation_supply_chain.blocking_counts({
                        "Results": [{"Vulnerabilities": [{"Severity": severity}]}],
                    })

    def test_critical_finding_blocks_even_without_fix(self) -> None:
        report = {"Results": [{"Vulnerabilities": [{"Severity": "CRITICAL", "FixedVersion": ""}]}]}
        self.assertEqual((1, 0, 0), foundation_supply_chain.blocking_counts(report))

    def test_only_fixable_high_blocks(self) -> None:
        report = {
            "Results": [{"Vulnerabilities": [
                {"Severity": "HIGH", "FixedVersion": ""},
                {"Severity": "HIGH", "FixedVersion": "2.0"},
            ]}]
        }
        self.assertEqual((0, 1, 1), foundation_supply_chain.blocking_counts(report))

    def test_unfixable_high_requires_disposition(self) -> None:
        report = {"Results": [{"Vulnerabilities": [
            {"Severity": "HIGH", "FixedVersion": ""},
        ]}]}
        self.assertEqual((0, 0, 1), foundation_supply_chain.blocking_counts(report))

    def test_lower_severity_does_not_block(self) -> None:
        report = {"Results": [{"Vulnerabilities": [{"Severity": "MEDIUM", "FixedVersion": "2.0"}]}]}
        self.assertEqual((0, 0, 0), foundation_supply_chain.blocking_counts(report))


if __name__ == "__main__":
    unittest.main()
