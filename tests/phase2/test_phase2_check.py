from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.phase2 import check


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

        # When: the public orchestrator runs to completion.
        with (
            patch.object(check, "STAGES", stages),
            patch.object(check, "short_commit", return_value="0123456789ab"),
            redirect_stdout(output),
        ):
            result = check.run()

        # Then: every stage passes once, in order, with one shared run ID.
        self.assertEqual(result, 0)
        self.assertEqual(
            calls,
            [
                (label, "phase2-check-0123456789ab")
                for label in EXPECTED_STAGES
            ],
        )
        self.assertEqual(
            output.getvalue().splitlines(),
            [f"{label}: PASS" for label in EXPECTED_STAGES],
        )

    def test_run_stops_at_first_failure_without_false_pass_marker(self) -> None:
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

        # When: the sequential orchestrator reaches the failure.
        with (
            patch.object(
                check,
                "STAGES",
                (("first", succeeds), ("second", fails), ("third", forbidden)),
            ),
            patch.object(check, "short_commit", return_value="abcdef012345"),
            redirect_stdout(output),
            self.assertRaisesRegex(check.CheckError, "controlled failure"),
        ):
            check.run()

        # Then: no later action or misleading PASS is emitted.
        self.assertEqual(calls, ["first", "second"])
        self.assertEqual(output.getvalue().splitlines(), ["first: PASS"])

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
            patch.object(check, "authoritative_snapshot", side_effect=snapshots),
            patch.object(check, "manifest_bytes", side_effect=manifests),
            patch.object(check, "disposition_count", side_effect=disposition_counts),
            patch.object(check, "source_count", return_value=2),
        ):
            check.rollback_reapply("phase2-check-abcdef012345")

        # Then: m0001 is dropped, all migrations are restored, and the same run replays.
        rollback.assert_called_once_with(check.migrate.MIGRATION_ID)
        apply.assert_called_once_with()
        verify.assert_called_once_with()
        self.assertEqual(
            execute.call_args_list[0].args[0],
            "phase2-check-abcdef012345",
        )
        self.assertEqual(execute.call_args_list[1].args[0], execute.call_args_list[0].args[0])

    def test_migrate_apply_reapplies_before_verify(self) -> None:
        # Given: observable migration operations for an idempotency check.
        calls: list[str] = []

        def apply() -> int:
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

    def test_unit_stage_surfaces_exact_planned_command(self) -> None:
        # Given: a successful programmatic unittest result.
        output = StringIO()
        result = unittest.TestResult()

        # When: the unit-test stage is invoked.
        with (
            patch.object(
                check.unittest.defaultTestLoader,
                "discover",
                return_value=unittest.TestSuite(),
            ) as discover,
            patch.object(check.unittest.TextTestRunner, "run", return_value=result),
            patch.object(check.migrate, "apply", return_value=0),
            patch.object(check.migrate, "verify", return_value=("events",)),
            patch.object(check, "pipeline_execute", side_effect=({}, {})),
            patch.object(check, "_baseline", return_value=check.ReplayBaseline((), "", 0, 0)),
            patch.object(check, "_assert_duplicate_replay"),
            patch.object(check, "noc_verify"),
            redirect_stdout(output),
        ):
            check.unit_tests("phase2-check-abcdef012345")

        # Then: the exact Makefile-equivalent command and discovery scope are used.
        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "unit-tests: command python3 -m unittest discover "
                "-s tests/phase2 -p 'test_*.py' -v"
            ],
        )
        discover.assert_called_once_with(str(check.ROOT / "tests" / "phase2"), pattern="test_*.py")

    def test_unit_stage_restores_acceptance_state_after_integration_tests(self) -> None:
        # Given: a successful suite whose integration tests may mutate shared state.
        result = unittest.TestResult()
        replay = {"counts": {"received": 6, "duplicate": 6}}
        baseline = check.ReplayBaseline(("authoritative",), "manifest", 6, 6)

        # When: the unit-test stage completes for the acceptance run.
        with (
            patch.object(
                check.unittest.defaultTestLoader,
                "discover",
                return_value=unittest.TestSuite(),
            ),
            patch.object(check.unittest.TextTestRunner, "run", return_value=result),
            patch.object(check.migrate, "rollback") as rollback,
            patch.object(check.migrate, "apply", return_value=0) as apply,
            patch.object(check.migrate, "verify", return_value=("events",)) as verify,
            patch.object(check, "pipeline_execute", side_effect=({"counts": {}}, replay)) as execute,
            patch.object(check, "_baseline", return_value=baseline) as capture_baseline,
            patch.object(check, "_assert_duplicate_replay") as assert_replay,
            patch.object(check, "rollback_reapply") as destructive_restore,
            patch.object(check, "noc_verify") as verify_noc,
        ):
            check.unit_tests("phase2-check-abcdef012345")

        # Then: final state is rebuilt without a second schema rollback.
        destructive_restore.assert_not_called()
        rollback.assert_not_called()
        apply.assert_called_once_with()
        verify.assert_called_once_with()
        self.assertEqual(
            [call.args for call in execute.call_args_list],
            [
                ("phase2-check-abcdef012345",),
                ("phase2-check-abcdef012345",),
            ],
        )
        capture_baseline.assert_called_once_with("phase2-check-abcdef012345")
        assert_replay.assert_called_once_with(replay, baseline)
        verify_noc.assert_called_once_with("phase2-check-abcdef012345")


if __name__ == "__main__":
    unittest.main()
