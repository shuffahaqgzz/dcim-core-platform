"""Tests for foundation evidence summary generator."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.foundation_evidence_summary import (
    EVIDENCE_ALLOWLIST,
    load_evidence_files,
    summarize_evidence,
    validate_evidence_record,
)


VALID_FAST_EVIDENCE: dict[str, object] = {
    "schema_version": 2,
    "commit": "abc1234567890abcdef1234567890abcdef123456",
    "capability_profiles": ["data", "observability", "smoke"],
    "utc_timestamp": "2026-07-21T10:00:00Z",
    "duration_seconds": 42.5,
    "assertion_result": "pass",
    "synthetic_run_id": "synthetic-0123456789abcdef",
    "mode": "fast",
    "image_digests": {
        "grafana": "sha256:" + "a" * 64,
        "jmx-exporter-java-runtime": "sha256:" + "b" * 64,
        "kafka": "sha256:" + "c" * 64,
        "postgres": "sha256:" + "d" * 64,
        "postgres-exporter": "sha256:" + "e" * 64,
        "prometheus": "sha256:" + "f" * 64,
    },
}

VALID_RECOVERY_EVIDENCE: dict[str, object] = {
    **VALID_FAST_EVIDENCE,
    "mode": "recovery",
    "duration_seconds": 120.3,
    "synthetic_run_id": "synthetic-fedcba9876543210",
}


class EvidenceSummaryTests(unittest.TestCase):
    def test_valid_evidence_record_passes_validation(self) -> None:
        errors = validate_evidence_record(VALID_FAST_EVIDENCE)
        self.assertEqual([], errors)

    def test_evidence_with_prohibited_field_fails(self) -> None:
        record = {**VALID_FAST_EVIDENCE, "hostname": "dev-vm-01"}
        errors = validate_evidence_record(record)
        self.assertTrue(any("hostname" in error for error in errors))

    def test_evidence_missing_required_field_fails(self) -> None:
        record = dict(VALID_FAST_EVIDENCE)
        del record["commit"]
        errors = validate_evidence_record(record)
        self.assertTrue(any("commit" in error for error in errors))

    def test_evidence_with_wrong_schema_version_fails(self) -> None:
        record = {**VALID_FAST_EVIDENCE, "schema_version": 1}
        errors = validate_evidence_record(record)
        self.assertTrue(any("schema_version" in error for error in errors))

    def test_load_evidence_files_from_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence_dir = Path(directory) / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / "fast-synthetic-abc123.json").write_text(
                json.dumps(VALID_FAST_EVIDENCE), encoding="utf-8",
            )
            (evidence_dir / "recovery-synthetic-def456.json").write_text(
                json.dumps(VALID_RECOVERY_EVIDENCE), encoding="utf-8",
            )
            (evidence_dir / "not-evidence.txt").write_text("ignore", encoding="utf-8")

            records = load_evidence_files(evidence_dir)

            self.assertEqual(2, len(records))
            modes = {record["mode"] for record in records}
            self.assertEqual({"fast", "recovery"}, modes)

    def test_load_evidence_skips_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence_dir = Path(directory) / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / "fast-synthetic-bad.json").write_text(
                "not json", encoding="utf-8",
            )

            records = load_evidence_files(evidence_dir)
            self.assertEqual(0, len(records))

    def test_summarize_produces_public_safe_output(self) -> None:
        records = [VALID_FAST_EVIDENCE, VALID_RECOVERY_EVIDENCE]
        summary = summarize_evidence(records, "abc123")

        self.assertEqual("abc123", summary["commit"])
        self.assertEqual(2, len(summary["runs"]))
        self.assertTrue(all(
            run["assertion_result"] == "pass" for run in summary["runs"]
        ))
        self.assertIn("fast", [run["mode"] for run in summary["runs"]])
        self.assertIn("recovery", [run["mode"] for run in summary["runs"]])

        serialized = json.dumps(summary)
        for prohibited in ("hostname", "runtime_root", "environment",
                           "credential", "container", "password", "secret"):
            self.assertNotIn(prohibited, serialized.lower())

    def test_summarize_reports_failures(self) -> None:
        failed = {**VALID_FAST_EVIDENCE, "assertion_result": "fail"}
        summary = summarize_evidence([failed], "abc123")

        self.assertEqual("fail", summary["overall_result"])

    def test_summarize_all_pass(self) -> None:
        summary = summarize_evidence(
            [VALID_FAST_EVIDENCE, VALID_RECOVERY_EVIDENCE], "abc123",
        )
        self.assertEqual("pass", summary["overall_result"])

    def test_summarize_empty_records_fails(self) -> None:
        summary = summarize_evidence([], "abc123")
        self.assertEqual("fail", summary["overall_result"])
        self.assertEqual(0, len(summary["runs"]))

    def test_allowlist_contains_only_known_safe_fields(self) -> None:
        prohibited = {
            "hostname", "runtime_root", "environment", "credential",
            "container", "password", "secret", "token", "key",
        }
        self.assertEqual(set(), EVIDENCE_ALLOWLIST & prohibited)

    def test_summary_includes_image_digests_from_latest_run(self) -> None:
        summary = summarize_evidence(
            [VALID_FAST_EVIDENCE, VALID_RECOVERY_EVIDENCE], "abc123",
        )
        self.assertIn("image_digests", summary)
        self.assertEqual(6, len(summary["image_digests"]))

    def test_load_from_nonexistent_directory_returns_empty(self) -> None:
        records = load_evidence_files(Path("/nonexistent/path"))
        self.assertEqual(0, len(records))


if __name__ == "__main__":
    unittest.main()
