"""Tests for foundation evidence summary generator."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.foundation_evidence_summary import (
    EVIDENCE_ALLOWLIST,
    acceptance_errors,
    load_evidence_files,
    load_evidence_files_with_error_categories,
    load_evidence_files_with_errors,
    parse_required_modes,
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

    def test_load_evidence_reports_invalid_public_unsafe_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence_dir = Path(directory) / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / "fast-synthetic-abc123.json").write_text(
                json.dumps(VALID_FAST_EVIDENCE), encoding="utf-8",
            )
            (evidence_dir / "raw-leak.json").write_text(
                json.dumps({**VALID_FAST_EVIDENCE, "hostname": "synthetic-host"}),
                encoding="utf-8",
            )

            records, errors = load_evidence_files_with_errors(evidence_dir)

            self.assertEqual(1, len(records))
            self.assertTrue(any("raw-leak.json" in error for error in errors))
            self.assertTrue(any("hostname" in error for error in errors))

    def test_load_evidence_categorizes_legacy_schema_as_non_safety_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence_dir = Path(directory) / "evidence"
            evidence_dir.mkdir()
            legacy = dict(VALID_FAST_EVIDENCE)
            legacy["schema_version"] = 1
            del legacy["image_digests"]
            (evidence_dir / "fast-legacy.json").write_text(
                json.dumps(legacy), encoding="utf-8",
            )

            records, schema_errors, safety_errors = load_evidence_files_with_error_categories(
                evidence_dir,
            )

            self.assertEqual([], records)
            self.assertTrue(any("schema_version" in error for error in schema_errors))
            self.assertEqual([], safety_errors)

    def test_summarize_produces_public_safe_output(self) -> None:
        records = [VALID_FAST_EVIDENCE, VALID_RECOVERY_EVIDENCE]
        summary = summarize_evidence(records, str(VALID_FAST_EVIDENCE["commit"]))

        self.assertEqual(str(VALID_FAST_EVIDENCE["commit"]), summary["commit"])
        self.assertEqual(2, len(summary["runs"]))
        self.assertTrue(all(
            run["assertion_result"] == "pass" for run in summary["runs"]
        ))
        self.assertTrue(all(
            run["source_commit"] == str(VALID_FAST_EVIDENCE["commit"])
            for run in summary["runs"]
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
            [VALID_FAST_EVIDENCE, VALID_RECOVERY_EVIDENCE],
            str(VALID_FAST_EVIDENCE["commit"]),
        )
        self.assertEqual("pass", summary["overall_result"])

    def test_summarize_marks_stale_source_commit_as_failure(self) -> None:
        summary = summarize_evidence(
            [VALID_FAST_EVIDENCE],
            "different-commit",
        )

        self.assertEqual("different-commit", summary["commit"])
        self.assertEqual("fail", summary["overall_result"])
        self.assertEqual(
            str(VALID_FAST_EVIDENCE["commit"]),
            summary["runs"][0]["source_commit"],
        )

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
            [VALID_FAST_EVIDENCE, VALID_RECOVERY_EVIDENCE],
            str(VALID_FAST_EVIDENCE["commit"]),
        )
        self.assertIn("image_digests", summary)
        self.assertEqual(6, len(summary["image_digests"]))

    def test_load_from_nonexistent_directory_returns_empty(self) -> None:
        records = load_evidence_files(Path("/nonexistent/path"))
        self.assertEqual(0, len(records))

    def test_acceptance_gate_rejects_missing_required_modes(self) -> None:
        errors = acceptance_errors(
            [VALID_FAST_EVIDENCE],
            commit=str(VALID_FAST_EVIDENCE["commit"]),
            required_modes={"fast", "recovery"},
            require_pass=True,
            strict_commit=True,
        )

        self.assertTrue(any("recovery" in error for error in errors))

    def test_acceptance_gate_rejects_stale_commit_evidence(self) -> None:
        errors = acceptance_errors(
            [VALID_FAST_EVIDENCE, VALID_RECOVERY_EVIDENCE],
            commit="different-commit",
            required_modes={"fast", "recovery"},
            require_pass=True,
            strict_commit=True,
        )

        self.assertTrue(any("commit" in error for error in errors))

    def test_acceptance_gate_rejects_failing_evidence(self) -> None:
        failed = {**VALID_RECOVERY_EVIDENCE, "assertion_result": "fail"}
        errors = acceptance_errors(
            [VALID_FAST_EVIDENCE, failed],
            commit=str(VALID_FAST_EVIDENCE["commit"]),
            required_modes={"fast", "recovery"},
            require_pass=True,
            strict_commit=True,
        )

        self.assertTrue(any("non-passing" in error for error in errors))

    def test_required_modes_parser_rejects_unknown_modes(self) -> None:
        with self.assertRaises(ValueError):
            parse_required_modes("fast,production")

    def test_cli_strict_failure_does_not_write_summary_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_dir = root / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / "fast-synthetic-abc123.json").write_text(
                json.dumps(VALID_FAST_EVIDENCE), encoding="utf-8",
            )
            output = root / "summary.json"

            result = subprocess.run(
                [
                    "python3",
                    str(Path(__file__).resolve().parents[1] / "scripts/foundation_evidence_summary.py"),
                    "--evidence-dir", str(evidence_dir),
                    "--commit", str(VALID_FAST_EVIDENCE["commit"]),
                    "--output", str(output),
                    "--require-modes", "fast,recovery",
                    "--require-pass",
                    "--strict-commit",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertFalse(output.exists())

    def test_cli_strict_rejects_invalid_public_unsafe_evidence_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_dir = root / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / "fast-synthetic-abc123.json").write_text(
                json.dumps(VALID_FAST_EVIDENCE), encoding="utf-8",
            )
            (evidence_dir / "recovery-synthetic-def456.json").write_text(
                json.dumps(VALID_RECOVERY_EVIDENCE), encoding="utf-8",
            )
            (evidence_dir / "raw-leak.json").write_text(
                json.dumps({**VALID_FAST_EVIDENCE, "hostname": "synthetic-host"}),
                encoding="utf-8",
            )
            output = root / "summary.json"

            result = subprocess.run(
                [
                    "python3",
                    str(Path(__file__).resolve().parents[1] / "scripts/foundation_evidence_summary.py"),
                    "--evidence-dir", str(evidence_dir),
                    "--commit", str(VALID_FAST_EVIDENCE["commit"]),
                    "--output", str(output),
                    "--require-modes", "fast,recovery",
                    "--require-pass",
                    "--strict-commit",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertFalse(output.exists())
            self.assertIn("raw-leak.json", result.stderr)
            self.assertIn("hostname", result.stderr)

    def test_cli_non_strict_rejects_invalid_public_unsafe_evidence_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_dir = root / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / "fast-synthetic-abc123.json").write_text(
                json.dumps(VALID_FAST_EVIDENCE), encoding="utf-8",
            )
            (evidence_dir / "raw-leak.json").write_text(
                json.dumps({**VALID_FAST_EVIDENCE, "hostname": "synthetic-host"}),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python3",
                    str(Path(__file__).resolve().parents[1] / "scripts/foundation_evidence_summary.py"),
                    "--evidence-dir", str(evidence_dir),
                    "--commit", str(VALID_FAST_EVIDENCE["commit"]),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertIn("raw-leak.json", result.stderr)
            self.assertIn("hostname", result.stderr)

    def test_cli_non_strict_skips_public_safe_legacy_schema_evidence_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_dir = root / "evidence"
            evidence_dir.mkdir()
            legacy = dict(VALID_RECOVERY_EVIDENCE)
            legacy["schema_version"] = 1
            del legacy["image_digests"]
            (evidence_dir / "recovery-legacy.json").write_text(
                json.dumps(legacy), encoding="utf-8",
            )
            (evidence_dir / "fast-synthetic-abc123.json").write_text(
                json.dumps(VALID_FAST_EVIDENCE), encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python3",
                    str(Path(__file__).resolve().parents[1] / "scripts/foundation_evidence_summary.py"),
                    "--evidence-dir", str(evidence_dir),
                    "--commit", str(VALID_FAST_EVIDENCE["commit"]),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual("pass", summary["overall_result"])
            self.assertEqual(["fast"], [run["mode"] for run in summary["runs"]])

    def test_cli_strict_rejects_public_safe_legacy_schema_evidence_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_dir = root / "evidence"
            evidence_dir.mkdir()
            legacy = dict(VALID_FAST_EVIDENCE)
            legacy["schema_version"] = 1
            del legacy["image_digests"]
            (evidence_dir / "fast-legacy.json").write_text(
                json.dumps(legacy), encoding="utf-8",
            )
            (evidence_dir / "fast-synthetic-abc123.json").write_text(
                json.dumps(VALID_FAST_EVIDENCE), encoding="utf-8",
            )
            (evidence_dir / "recovery-synthetic-def456.json").write_text(
                json.dumps(VALID_RECOVERY_EVIDENCE), encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python3",
                    str(Path(__file__).resolve().parents[1] / "scripts/foundation_evidence_summary.py"),
                    "--evidence-dir", str(evidence_dir),
                    "--commit", str(VALID_FAST_EVIDENCE["commit"]),
                    "--require-modes", "fast,recovery",
                    "--require-pass",
                    "--strict-commit",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("fast-legacy.json", result.stderr)
            self.assertIn("schema_version", result.stderr)

    def test_cli_strict_ignores_generated_summary_and_acceptance_report_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_dir = root / "evidence"
            evidence_dir.mkdir()
            for name, record in (
                ("fast-synthetic-abc123.json", VALID_FAST_EVIDENCE),
                ("recovery-synthetic-def456.json", VALID_RECOVERY_EVIDENCE),
            ):
                (evidence_dir / name).write_text(json.dumps(record), encoding="utf-8")
            output = evidence_dir / "phase1-clean-acceptance-summary.json"

            first = subprocess.run(
                [
                    "python3",
                    str(Path(__file__).resolve().parents[1] / "scripts/foundation_evidence_summary.py"),
                    "--evidence-dir", str(evidence_dir),
                    "--commit", str(VALID_FAST_EVIDENCE["commit"]),
                    "--output", str(output),
                    "--require-modes", "fast,recovery",
                    "--require-pass",
                    "--strict-commit",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, first.returncode, first.stderr)

            (evidence_dir / "clean-runtime-acceptance.json").write_text(
                json.dumps({
                    "schema_version": 1,
                    "commit": str(VALID_FAST_EVIDENCE["commit"]),
                    "project_scope": "isolated synthetic dcim-build acceptance namespace",
                    "started_utc": "2026-07-21T10:00:00Z",
                    "finished_utc": "2026-07-21T10:01:00Z",
                    "result": "pass",
                    "steps": [{
                        "step": "foundation-stop",
                        "exit_code": 0,
                        "duration_seconds": 1.0,
                    }],
                }),
                encoding="utf-8",
            )

            second = subprocess.run(
                [
                    "python3",
                    str(Path(__file__).resolve().parents[1] / "scripts/foundation_evidence_summary.py"),
                    "--evidence-dir", str(evidence_dir),
                    "--commit", str(VALID_FAST_EVIDENCE["commit"]),
                    "--require-modes", "fast,recovery",
                    "--require-pass",
                    "--strict-commit",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, second.returncode, second.stderr)
            self.assertEqual("", second.stderr)

    def test_cli_rejects_unknown_generated_json_artifact_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_dir = root / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / "fast-synthetic-abc123.json").write_text(
                json.dumps(VALID_FAST_EVIDENCE), encoding="utf-8",
            )
            (evidence_dir / "custom-summary.json").write_text(
                json.dumps({
                    "schema_version": 1,
                    "commit": str(VALID_FAST_EVIDENCE["commit"]),
                    "overall_result": "pass",
                    "runs": [],
                }),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python3",
                    str(Path(__file__).resolve().parents[1] / "scripts/foundation_evidence_summary.py"),
                    "--evidence-dir", str(evidence_dir),
                    "--commit", str(VALID_FAST_EVIDENCE["commit"]),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("custom-summary.json", result.stderr)
            self.assertIn("unrecognized evidence JSON file", result.stderr)

    def test_cli_non_strict_exposes_stale_source_commit_without_rebinding_to_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_dir = root / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / "fast-synthetic-abc123.json").write_text(
                json.dumps({**VALID_FAST_EVIDENCE, "commit": "oldcommit"}),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python3",
                    str(Path(__file__).resolve().parents[1] / "scripts/foundation_evidence_summary.py"),
                    "--evidence-dir", str(evidence_dir),
                    "--commit", "newcommit",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual("newcommit", summary["commit"])
            self.assertEqual("fail", summary["overall_result"])
            self.assertEqual("oldcommit", summary["runs"][0]["source_commit"])


if __name__ == "__main__":
    unittest.main()
