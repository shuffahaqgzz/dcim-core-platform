from __future__ import annotations

import os
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.phase2 import check, db


EXPECTED_STAGES = (
    "migrate-apply",
    "pipeline-run",
    "idempotency-replay",
    "rollback-reapply",
    "recovery",
    "capacity",
    "noc-verify",
    "unit-tests",
)


class Phase2CheckTests(unittest.TestCase):
    def test_run_reuses_one_commit_derived_run_id_across_eight_stages(self) -> None:
        # Given: eight observable stage actions and one fixed commit identity.
        calls: list[tuple[str, str]] = []

        def action(label: str):
            def record(run_id: str) -> None:
                calls.append((label, run_id))

            return record

        stages = tuple((label, action(label)) for label in EXPECTED_STAGES)
        output = StringIO()

        def clean_acceptance_state() -> None:
            calls.append(("acceptance-cleanup", ""))

        # When: the public orchestrator runs to completion.
        with (
            patch.object(check, "STAGES", stages),
            patch.object(check, "short_commit", return_value="0123456789ab"),
            patch.object(
                check,
                "clean_acceptance_state",
                side_effect=clean_acceptance_state,
                create=True,
            ),
            redirect_stdout(output),
        ):
            result = check.run()

        # Then: every stage passes once, in order, with one shared run ID.
        self.assertEqual(result, 0)
        self.assertEqual(
            calls,
            [
                *[
                    (label, "phase2-check-0123456789ab")
                    for label in EXPECTED_STAGES[:-1]
                ],
                ("acceptance-cleanup", ""),
                (EXPECTED_STAGES[-1], "phase2-check-0123456789ab"),
            ],
        )
        self.assertEqual(
            output.getvalue().splitlines(),
            [f"{label}: PASS" for label in EXPECTED_STAGES],
        )

    def test_main_labels_first_failure_without_false_pass_marker(self) -> None:
        # Given: a second stage that fails and a later stage that must not run.
        calls: list[str] = []

        def succeeds(_run_id: str) -> None:
            calls.append("first")

        def fails(_run_id: str) -> None:
            calls.append("second")
            raise check.CheckError("controlled failure")

        def forbidden(_run_id: str) -> None:
            calls.append("third")

        output = StringIO()
        error_output = StringIO()

        # When: the public CLI boundary reaches the recovery failure.
        with (
            patch.object(
                check,
                "STAGES",
                (
                    ("migrate-apply", succeeds),
                    ("recovery", fails),
                    ("unit-tests", forbidden),
                ),
            ),
            patch.object(check, "short_commit", return_value="abcdef012345"),
            redirect_stdout(output),
            redirect_stderr(error_output),
        ):
            result = check.main()

        # Then: the CLI emits a grep-friendly marker and stops before later work.
        self.assertEqual(result, 1)
        self.assertEqual(calls, ["first", "second"])
        self.assertEqual(output.getvalue().splitlines(), ["migrate-apply: PASS"])
        self.assertEqual(
            error_output.getvalue().splitlines(),
            ["recovery: FAIL: controlled failure"],
        )

    def test_main_labels_commit_identity_failure_before_first_stage(self) -> None:
        # Given: commit metadata is unavailable before the first stage starts.
        output = StringIO()
        error_output = StringIO()

        # When: the public CLI boundary resolves its run identity.
        with (
            patch.object(
                check, "short_commit", side_effect=check.CheckError("Git HEAD unavailable")
            ),
            redirect_stdout(output),
            redirect_stderr(error_output),
        ):
            result = check.main()

        # Then: the gate fails cleanly without emitting any stage PASS marker.
        self.assertEqual(result, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(
            error_output.getvalue().splitlines(),
            ["phase2-check: FAIL: Git HEAD unavailable"],
        )

    def test_rollback_reapply_reingests_and_proves_identical_replay(self) -> None:
        # Given: clean snapshots around a two-input replay after schema rebuild.
        summaries = [
            {"counts": {"received": 2, "accepted": 2, "quarantined": 0, "duplicate": 0}},
            {"counts": {"received": 2, "accepted": 0, "quarantined": 0, "duplicate": 2}},
        ]
        snapshots = iter((("authoritative",), ("authoritative",)))
        manifests = iter(("manifest-bytes", "manifest-bytes"))
        disposition_counts = iter((2, 4))

        # When: rollback/reapply runs through its public stage seam.
        with (
            patch.object(check.migrate, "rollback") as rollback,
            patch.object(check.migrate, "apply", return_value=2) as apply,
            patch.object(check.migrate, "verify", return_value=("events",)) as verify,
            patch.object(check, "pipeline_execute", side_effect=summaries) as execute,
            patch.object(
                check, "authoritative_snapshot", side_effect=snapshots
            ) as authoritative_snapshot,
            patch.object(
                check, "manifest_bytes", side_effect=manifests
            ) as manifest_bytes,
            patch.object(
                check, "disposition_count", side_effect=disposition_counts
            ) as disposition_count,
            patch.object(check, "source_count", return_value=2) as source_count,
        ):
            check.rollback_reapply("phase2-check-abcdef012345")

        # Then: m0001 is dropped, all migrations are restored, and the same run replays.
        rollback.assert_called_once_with(check.migrate.MIGRATION_ID)
        apply.assert_called_once_with(
            Path(os.environ["DCIM_RUNTIME_ROOT"]) / "dev-build" / "secrets"
        )
        verify.assert_called_once_with()
        self.assertEqual(
            execute.call_args_list[0].args[0],
            "phase2-check-abcdef012345",
        )
        self.assertEqual(
            execute.call_args_list[1].args[0], execute.call_args_list[0].args[0]
        )
        self.assertEqual(authoritative_snapshot.call_count, 2)
        self.assertEqual(manifest_bytes.call_count, 2)
        self.assertEqual(disposition_count.call_count, 2)
        source_count.assert_called_once_with("phase2-check-abcdef012345")

    def test_rollback_reapply_restores_schema_when_reingest_fails(self) -> None:
        # Given: rollback succeeds but the synthetic re-ingest fails mid-stage.
        calls: list[str] = []

        def apply(_role_password_dir: Path) -> int:
            calls.append("apply")
            return 2

        def verify() -> tuple[str, ...]:
            calls.append("verify")
            return ("events",)

        def fail_reingest(_run_id: str) -> db.JsonObject:
            calls.append("pipeline")
            raise check.CheckError("simulated re-ingest failure")

        # When: the destructive stage exits through its failure path.
        with (
            patch.object(check.migrate, "rollback") as rollback,
            patch.object(check.migrate, "apply", side_effect=apply),
            patch.object(check.migrate, "verify", side_effect=verify),
            patch.object(check, "pipeline_execute", side_effect=fail_reingest),
            self.assertRaisesRegex(check.CheckError, "simulated re-ingest failure"),
        ):
            check.rollback_reapply("phase2-check-abcdef012345")

        # Then: migration restoration runs before the original failure escapes.
        rollback.assert_called_once_with(check.migrate.MIGRATION_ID)
        self.assertEqual(
            calls,
            ["apply", "verify", "pipeline", "apply", "verify"],
        )

    def test_acceptance_cleanup_preserves_the_migrated_schema(self) -> None:
        # Given: an observable database boundary for acceptance teardown.
        with patch.object(check.db, "psql", return_value="") as psql:
            # When: acceptance state is cleaned before unit discovery.
            check.clean_acceptance_state()

        # Then: rows are truncated without dropping the Phase 2 schema.
        sql = psql.call_args.args[0]
        self.assertIn("TRUNCATE TABLE", sql)
        self.assertIn("phase2.run_manifests", sql)
        self.assertNotIn("DROP SCHEMA", sql)

    def test_migrate_apply_reapplies_before_verify(self) -> None:
        # Given: observable migration operations for an idempotency check.
        calls: list[str] = []

        def apply(_role_password_dir: Path) -> int:
            calls.append("apply")
            return 2

        def verify() -> tuple[str, ...]:
            calls.append("verify")
            return ("events",)

        # When: the migration stage runs.
        with (
            patch.object(check.migrate, "apply", side_effect=apply),
            patch.object(check.migrate, "verify", side_effect=verify),
        ):
            check.migrate_apply("phase2-check-abcdef012345")

        # Then: apply is immediately replayed before schema verification.
        self.assertEqual(calls, ["apply", "apply", "verify"])

    def test_unit_stage_only_runs_unittest_discovery(self) -> None:
        # Given: a successful programmatic unittest result.
        result = unittest.TestResult()

        # When: the unit-test stage is invoked.
        with (
            patch.object(
                check.unittest.defaultTestLoader,
                "discover",
                return_value=unittest.TestSuite(),
            ) as discover,
            patch.object(check.unittest.TextTestRunner, "run", return_value=result),
            patch.object(check.migrate, "apply") as migrate_apply,
            patch.object(check, "pipeline_execute") as pipeline_execute,
            patch.object(check, "noc_verify") as noc_verify,
        ):
            check.unit_tests("phase2-check-abcdef012345")

        # Then: stage 8 performs discovery only; earlier acceptance stages stay isolated.
        discover.assert_called_once_with(str(check.ROOT / "tests" / "phase2"), pattern="test_*.py")
        migrate_apply.assert_not_called()
        pipeline_execute.assert_not_called()
        noc_verify.assert_not_called()

    def test_unit_stage_rejects_hidden_skips(self) -> None:
        # Given: a successful suite result containing one skipped destructive test.
        result = unittest.TestResult()
        skipped_test = unittest.FunctionTestCase(lambda: None)
        result.addSkip(skipped_test, "shared Phase 2 data exists")

        # When: the unit-test stage evaluates the discovery result.
        with (
            patch.object(
                check.unittest.defaultTestLoader,
                "discover",
                return_value=unittest.TestSuite(),
            ),
            patch.object(check.unittest.TextTestRunner, "run", return_value=result),
            self.assertRaisesRegex(check.CheckError, "skipped 1 test"),
        ):
            check.unit_tests("phase2-check-abcdef012345")

        # Then: a green result cannot conceal an unexecuted test.
        self.assertTrue(result.wasSuccessful())


if __name__ == "__main__":
    unittest.main()
