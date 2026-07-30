from __future__ import annotations

import importlib.util
import inspect
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "phase2_evidence_receipt.py"
SCHEMA = ROOT / "schemas" / "phase2-evidence-receipt.schema.json"
SPEC = importlib.util.spec_from_file_location("phase2_evidence_receipt", SCRIPT)
assert SPEC and SPEC.loader
RECEIPT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RECEIPT
SPEC.loader.exec_module(RECEIPT)


def _make_plan() -> str:
    return (
        "# Plan\n"
        "`BEGIN AUTHORITY_ROOTS_V1`\n"
        "repository=example\n"
        "`END AUTHORITY_ROOTS_V1`\n"
        "`BEGIN ORIGINAL_PATCH_INVENTORY_V1`\n"
        "original commits\n"
        "`END ORIGINAL_PATCH_INVENTORY_V1`\n"
        "`BEGIN PHASE2_TODO_PATH_AUTHORITY_V1`\n"
        "todo paths\n"
        "`END PHASE2_TODO_PATH_AUTHORITY_V1`\n"
        "`BEGIN LEGACY_FAILURE_INVENTORY_V1`\n"
        "legacy\n"
        "`END LEGACY_FAILURE_INVENTORY_V1`\n"
        "`BEGIN ORACLE_CONTRACT_V1`\n"
        "contract\n"
        "`END ORACLE_CONTRACT_V1`\n"
        "`BEGIN REMEDIATION_ALLOWLIST_V1`\n"
        "allowlist\n"
        "`END REMEDIATION_ALLOWLIST_V1`\n"
    )


def _write_synthetic_runtime(root: Path, cluster_id: str = "synthetic-cluster-id") -> None:
    plane = root / "dev-build"
    secrets = plane / "secrets"
    secrets.mkdir(parents=True)
    root.chmod(0o700)
    plane.chmod(0o700)
    secrets.chmod(0o700)
    runtime_environment = plane / "runtime.env"
    runtime_environment.write_text(
        "COMPOSE_PROJECT_NAME=dcim-build\n"
        f"KAFKA_CLUSTER_ID={cluster_id}\n",
        encoding="utf-8",
    )
    runtime_environment.chmod(0o600)
    images_environment = plane / "images.env"
    images_environment.write_text("IMAGE_LOCK=synthetic\n", encoding="utf-8")
    images_environment.chmod(0o600)
    for name in RECEIPT.PROTECTED_SECRET_NAMES:
        protected_file = secrets / name
        protected_file.write_text(f"synthetic-{name}\n", encoding="utf-8")
        protected_file.chmod(0o400)


class Phase2EvidenceReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan_text = _make_plan()
        self.plan_bytes = self.plan_text.encode("utf-8")
        self.expected_sha256 = RECEIPT._hash_bytes(self.plan_bytes)

    def test_plan_authority_validates_block_digests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "plan.md"
            plan_path.write_bytes(self.plan_bytes)
            raw, blocks, digests = RECEIPT.validate_plan_authority(
                plan_path=plan_path,
                expected_sha256=self.expected_sha256,
                required_blocks=("AUTHORITY_ROOTS_V1", "ORACLE_CONTRACT_V1"),
            )
            self.assertEqual(raw, self.plan_bytes)
            self.assertIn("AUTHORITY_ROOTS_V1", blocks)
            self.assertIn("ORACLE_CONTRACT_V1", digests)

    def test_plan_authority_rejects_wrong_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "plan.md"
            plan_path.write_bytes(self.plan_bytes)
            with self.assertRaises(RECEIPT.PlanAuthorityError):
                RECEIPT.validate_plan_authority(
                    plan_path=plan_path,
                    expected_sha256="0" * 64,
                    required_blocks=("AUTHORITY_ROOTS_V1",),
                )

    def test_plan_authority_rejects_missing_final_lf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "plan.md"
            plan_path.write_bytes(self.plan_bytes[:-1])
            with self.assertRaises(RECEIPT.PlanAuthorityError):
                RECEIPT.validate_plan_authority(
                    plan_path=plan_path,
                    expected_sha256=RECEIPT._hash_bytes(self.plan_bytes[:-1]),
                )

    def test_plan_authority_rejects_malformed_marker_streams(self) -> None:
        malformed_plans = {
            "nested": (
                "`BEGIN AUTHORITY_ROOTS_V1`\n"
                "`BEGIN ORACLE_CONTRACT_V1`\n"
                "nested\n"
                "`END ORACLE_CONTRACT_V1`\n"
                "`END AUTHORITY_ROOTS_V1`\n"
            ),
            "duplicate_begin": (
                "`BEGIN AUTHORITY_ROOTS_V1`\n"
                "`BEGIN AUTHORITY_ROOTS_V1`\n"
                "body\n"
                "`END AUTHORITY_ROOTS_V1`\n"
            ),
            "end_before_begin": (
                "`END AUTHORITY_ROOTS_V1`\n"
                "`BEGIN AUTHORITY_ROOTS_V1`\n"
                "body\n"
                "`END AUTHORITY_ROOTS_V1`\n"
            ),
            "missing_end": "`BEGIN AUTHORITY_ROOTS_V1`\nbody\n",
            "missing_begin": "`END AUTHORITY_ROOTS_V1`\n",
        }

        for scenario, plan_text in malformed_plans.items():
            with self.subTest(scenario=scenario):
                with self.assertRaises(RECEIPT.PlanAuthorityError):
                    RECEIPT.extract_blocks(plan_text.encode("utf-8"))

    def test_duplicate_json_keys_are_rejected(self) -> None:
        data = '{"key": 1, "key": 2}'
        with self.assertRaises(RECEIPT.DuplicateKeyError):
            RECEIPT.load_json_with_duplicate_rejection(data)

    def test_marker_observation_records_pass_and_no_go_on_same_line(self) -> None:
        pass_observations, no_go_observations = RECEIPT._observe_markers(
            "heredoc_integrity=PASS NO-GO_PLAN_AUTHORITY",
            "stdout",
        )

        self.assertEqual(len(pass_observations), 1)
        self.assertEqual(len(no_go_observations), 1)

    def test_receipt_schema_is_valid_json(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(schema.get("additionalProperties", True))

    def test_process_disposition_is_computed_from_production_result(self) -> None:
        scenarios = (
            (RECEIPT.ProcessResult("", "", 0, None, "exited", None), [], "LOCAL_PASS"),
            (RECEIPT.ProcessResult("", "", 2, None, "exited", None), [], "NO-GO_PROCESS_OUTCOME"),
            (RECEIPT.ProcessResult("", "", -1, signal.SIGTERM, "signaled", None), [], "NO-GO_PROCESS_OUTCOME"),
            (RECEIPT.ProcessResult("", "", -1, None, "timed_out", None), [], "NO-GO_PROCESS_OUTCOME"),
            (
                RECEIPT.ProcessResult("", "", -1, None, "spawn_error", "FileNotFoundError"),
                [],
                "NO-GO_TOOLCHAIN_IDENTITY",
            ),
            (
                RECEIPT.ProcessResult("", "", 0, None, "exited", None),
                [{"marker": "NO-GO_PLAN_AUTHORITY", "channel": "stdout", "line": 1}],
                "NO-GO_PLAN_AUTHORITY",
            ),
        )

        for process_result, no_go_observations, expected in scenarios:
            with self.subTest(outcome=process_result.outcome, expected=expected):
                self.assertEqual(
                    RECEIPT.compute_process_disposition(process_result, no_go_observations),
                    expected,
                )

    def test_spawn_oracle_records_all_process_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = {
                "exited": "print('done')\n",
                "signaled": "import os, signal\nos.killpg(os.getpgrp(), signal.SIGTERM)\n",
                "timed_out": "import time\ntime.sleep(60)\n",
            }
            for expected, source in scripts.items():
                material = RECEIPT._prepare_executor_material(source.encode("utf-8"))
                try:
                    result = RECEIPT._spawn_oracle(
                        executor=material,
                        env={},
                        timeout_ms=20 if expected == "timed_out" else 10_000,
                        subject_dir=root,
                    )
                    self.assertEqual(result.outcome, expected)
                finally:
                    RECEIPT._cleanup_executor_material(material)

            material = RECEIPT._prepare_executor_material(b"print('done')\n")
            try:
                spawn_error = RECEIPT._spawn_oracle(
                    executor=material,
                    env={},
                    timeout_ms=10_000,
                    subject_dir=root / "missing",
                )
                self.assertEqual(spawn_error.outcome, "spawn_error")
                self.assertEqual(spawn_error.spawn_error_class, "FileNotFoundError")
            finally:
                RECEIPT._cleanup_executor_material(material)

    def test_executor_boundary_uses_verified_descriptor_and_isolated_environment(self) -> None:
        source = (
            "import json, os\n"
            "print(json.dumps({'env': sorted(os.environ), 'new_session': os.getsid(0) == os.getpid()}))\n"
        ).encode("utf-8")
        material = RECEIPT._prepare_executor_material(source)
        try:
            result = RECEIPT._spawn_oracle(
                executor=material,
                env={"DCIM_EPOCH_ID": "synthetic"},
                timeout_ms=10_000,
                subject_dir=ROOT,
            )
            observation = json.loads(result.stdout)
            self.assertEqual(result.outcome, "exited")
            self.assertEqual(
                observation["env"],
                ["DCIM_EPOCH_ID", "LANG", "LC_ALL", "PATH", "TZ"],
            )
            self.assertTrue(observation["new_session"])
            self.assertEqual(RECEIPT._hash_bytes(os.pread(material.fd, len(source), 0)), material.digest)
        finally:
            RECEIPT._cleanup_executor_material(material)

    def test_executor_fallback_is_exclusive_private_and_unlinked_before_spawn(self) -> None:
        material = RECEIPT._prepare_executor_material(b"print('fallback')\n", use_memfd=False)
        storage_dir = material.storage_dir
        try:
            self.assertIsNotNone(storage_dir)
            self.assertEqual(oct(storage_dir.stat().st_mode & 0o777), "0o700")
            self.assertEqual(oct(os.fstat(material.fd).st_mode & 0o777), "0o600")
            self.assertEqual(material.executable_path, Path(f"/proc/self/fd/{material.fd}"))
            self.assertEqual(list(storage_dir.iterdir()), [])
        finally:
            RECEIPT._cleanup_executor_material(material)
        self.assertFalse(storage_dir.exists())

    def test_default_executor_material_is_exact_script_bytes(self) -> None:
        material = RECEIPT._prepare_executor_material()
        try:
            script_bytes = SCRIPT.read_bytes()
            self.assertEqual(material.size, len(script_bytes))
            self.assertEqual(material.digest, RECEIPT._hash_bytes(script_bytes))
            self.assertEqual(os.pread(material.fd, material.size, 0), script_bytes)
        finally:
            RECEIPT._cleanup_executor_material(material)

    def test_subject_state_captures_every_drift_dimension(self) -> None:
        before = RECEIPT.capture_subject_state(ROOT)

        self.assertRegex(before.commit_sha, r"^[0-9a-f]{40}$")
        self.assertRegex(before.tree_sha, r"^[0-9a-f]{40}$")
        self.assertIsInstance(before.parent_shas, tuple)
        self.assertRegex(before.index_status_sha256, r"^[0-9a-f]{64}$")
        self.assertRegex(before.worktree_status_sha256, r"^[0-9a-f]{64}$")

        changed_states = (
            replace(before, branch_ref="synthetic-branch"),
            replace(before, commit_sha="0" * 40),
            replace(before, tree_sha="1" * 40),
            replace(before, parent_shas=("2" * 40,)),
            replace(before, index_status_sha256="3" * 64),
            replace(before, worktree_status_sha256="4" * 64),
        )
        for after in changed_states:
            with self.subTest(after=after):
                self.assertEqual(
                    RECEIPT.apply_subject_drift_precedence(before, after, "LOCAL_PASS"),
                    "NO-GO_HEAD_DRIFT",
                )
        self.assertEqual(
            RECEIPT.apply_subject_drift_precedence(before, before, "NO-GO_PROCESS_OUTCOME"),
            "NO-GO_PROCESS_OUTCOME",
        )

    def test_receipt_publication_is_atomic_canonical_and_replay_safe(self) -> None:
        receipt = RECEIPT.Receipt(receipt_id="synthetic-receipt")
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "receipt.json"

            with mock.patch.object(Path, "write_text", side_effect=AssertionError("direct publication")):
                RECEIPT.publish_receipt(output_path, receipt)

            self.assertEqual(output_path.read_bytes(), receipt.canonical_json().encode("utf-8"))
            self.assertEqual(oct(output_path.stat().st_mode & 0o777), "0o600")
            self.assertEqual(list(output_path.parent.glob(".receipt.json.*.tmp")), [])
            with self.assertRaises(RECEIPT.ReceiptError):
                RECEIPT.publish_receipt(output_path, receipt)
            self.assertEqual(output_path.read_bytes(), receipt.canonical_json().encode("utf-8"))

    def test_runtime_binding_digest_derivation_has_no_authority_api(self) -> None:
        binding_sha256 = RECEIPT.compute_runtime_binding_sha256(
            runtime_env_sha256="1" * 64,
            images_env_sha256="2" * 64,
            kafka_identity_sha256="3" * 64,
            fixed_volumes=RECEIPT.EXPECTED_FIXED_VOLUMES,
        )
        mismatched_binding_sha256 = RECEIPT.compute_runtime_binding_sha256(
            runtime_env_sha256="1" * 64,
            images_env_sha256="2" * 64,
            kafka_identity_sha256="4" * 64,
            fixed_volumes=RECEIPT.EXPECTED_FIXED_VOLUMES,
        )

        self.assertRegex(binding_sha256, r"^[0-9a-f]{64}$")
        self.assertNotEqual(binding_sha256, mismatched_binding_sha256)
        for authority_name in (
            "RuntimeBindingClaim",
            "RuntimeIdentityAttestation",
            "verify_runtime_binding_attestation",
        ):
            self.assertFalse(hasattr(RECEIPT, authority_name))

    def test_pure_runtime_binding_digest_changes_with_fixed_volume_identity(self) -> None:
        runtime_env_sha256 = "1" * 64
        images_env_sha256 = "2" * 64
        kafka_identity_sha256 = "3" * 64
        expected_binding_sha256 = RECEIPT.compute_runtime_binding_sha256(
            runtime_env_sha256=runtime_env_sha256,
            images_env_sha256=images_env_sha256,
            kafka_identity_sha256=kafka_identity_sha256,
            fixed_volumes=RECEIPT.EXPECTED_FIXED_VOLUMES,
        )
        different_binding_sha256 = RECEIPT.compute_runtime_binding_sha256(
            runtime_env_sha256=runtime_env_sha256,
            images_env_sha256=images_env_sha256,
            kafka_identity_sha256=kafka_identity_sha256,
            fixed_volumes=RECEIPT.EXPECTED_FIXED_VOLUMES
            | {"dcim-build-extra-data"},
        )

        self.assertNotEqual(expected_binding_sha256, different_binding_sha256)

    def test_generator_does_not_accept_runtime_authority_parameters(self) -> None:
        parameters = inspect.signature(
            RECEIPT.generate_authority_bootstrap_receipt
        ).parameters

        self.assertTrue(
            {
                "runtime_root_approved",
                "runtime_claim",
                "runtime_attestation",
            }.isdisjoint(parameters)
        )
        with self.assertRaises(TypeError):
            RECEIPT.generate_authority_bootstrap_receipt(
                plan_path=Path("synthetic-plan.md"),
                expected_plan_sha256="0" * 64,
                subject_dir=ROOT,
                base_sha="0" * 40,
                attempt_epoch_id="synthetic-epoch",
                runtime_claim=object(),
            )

    def test_oracle_child_collects_runtime_binding_from_approved_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "plan.md"
            plan_path.write_bytes(self.plan_bytes)
            environment = {
                "DCIM_ORACLE_PLAN_PATH": str(plan_path),
                "DCIM_ORACLE_EXPECTED_SHA256": self.expected_sha256,
                "DCIM_RUNTIME_ROOT": str(root),
            }
            output = io.StringIO()
            observation = RECEIPT.RuntimeBindingObservation("a" * 64)

            with (
                mock.patch.dict(os.environ, environment, clear=True),
                mock.patch.object(
                    RECEIPT,
                    "collect_runtime_binding",
                    return_value=observation,
                ) as collect,
                redirect_stdout(output),
            ):
                exit_code = RECEIPT._oracle_child_main()

            self.assertEqual(exit_code, 0)
            collect.assert_called_once_with(root)
            self.assertIn("runtime_binding=PASS", output.getvalue().splitlines())

    def test_receipt_publication_persists_exact_runtime_binding_digest_from_oracle_stdout(self) -> None:
        expected_digest = "a" * 64
        oracle_stdout = (
            "heredoc_integrity=PASS\n"
            "authority_blocks=PASS\n"
            "runtime_preflight=PASS\n"
            "runtime_binding=PASS\n"
            f"runtime_binding_digest={expected_digest}\n"
        )
        toolchain = RECEIPT.ToolchainIdentity(
            "3.12.0", "4" * 64, "git synthetic", "make synthetic", "docker synthetic", "compose synthetic"
        )

        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "plan.md"
            output_path = Path(directory) / "receipt.json"
            plan_path.write_bytes(self.plan_bytes)
            with mock.patch.object(
                RECEIPT,
                "_spawn_oracle",
                return_value=RECEIPT.ProcessResult(oracle_stdout, "", 0, None, "exited", None),
            ):
                receipt = RECEIPT.generate_authority_bootstrap_receipt(
                    plan_path=plan_path,
                    expected_plan_sha256=self.expected_sha256,
                    subject_dir=ROOT,
                    base_sha="e20c8e3569cb171a23fb1e4a9c417074dfb0ae8a",
                    attempt_epoch_id="epoch-test-runtime-binding-digest",
                    toolchain_identity=toolchain,
                )
            RECEIPT.publish_receipt(output_path, receipt)

            published = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(receipt.computed_disposition, "LOCAL_PASS")
        self.assertEqual(published["runtime_binding_digest"], expected_digest)

    def test_receipt_fails_closed_when_runtime_binding_pass_lacks_valid_digest(self) -> None:
        oracle_stdout = (
            "heredoc_integrity=PASS\n"
            "authority_blocks=PASS\n"
            "runtime_preflight=PASS\n"
            "runtime_binding=PASS\n"
            "runtime_binding_digest=" + "A" * 64 + "\n"
        )
        toolchain = RECEIPT.ToolchainIdentity(
            "3.12.0", "4" * 64, "git synthetic", "make synthetic", "docker synthetic", "compose synthetic"
        )

        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "plan.md"
            plan_path.write_bytes(self.plan_bytes)
            with mock.patch.object(
                RECEIPT,
                "_spawn_oracle",
                return_value=RECEIPT.ProcessResult(oracle_stdout, "", 0, None, "exited", None),
            ):
                receipt = RECEIPT.generate_authority_bootstrap_receipt(
                    plan_path=plan_path,
                    expected_plan_sha256=self.expected_sha256,
                    subject_dir=ROOT,
                    base_sha="e20c8e3569cb171a23fb1e4a9c417074dfb0ae8a",
                    attempt_epoch_id="epoch-test-runtime-binding-missing-digest",
                    toolchain_identity=toolchain,
                )

        self.assertEqual(receipt.runtime_binding_digest, None)
        self.assertEqual(receipt.computed_disposition, "NO-GO_F3_INCOMPLETE_BINDING")

    def test_receipt_fails_closed_when_runtime_binding_pass_is_missing(self) -> None:
        oracle_stdout = (
            "heredoc_integrity=PASS\n"
            "authority_blocks=PASS\n"
            "runtime_preflight=PASS\n"
        )
        toolchain = RECEIPT.ToolchainIdentity(
            "3.12.0", "4" * 64, "git synthetic", "make synthetic", "docker synthetic", "compose synthetic"
        )

        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "plan.md"
            plan_path.write_bytes(self.plan_bytes)
            with mock.patch.object(
                RECEIPT,
                "_spawn_oracle",
                return_value=RECEIPT.ProcessResult(oracle_stdout, "", 0, None, "exited", None),
            ):
                receipt = RECEIPT.generate_authority_bootstrap_receipt(
                    plan_path=plan_path,
                    expected_plan_sha256=self.expected_sha256,
                    subject_dir=ROOT,
                    base_sha="e20c8e3569cb171a23fb1e4a9c417074dfb0ae8a",
                    attempt_epoch_id="epoch-test-runtime-binding-missing-marker",
                    toolchain_identity=toolchain,
                )

        self.assertEqual(receipt.runtime_binding_digest, None)
        self.assertEqual(receipt.computed_disposition, "NO-GO_F3_INCOMPLETE_BINDING")

    def test_runtime_collection_uses_read_only_existing_kafka_probe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_synthetic_runtime(root)

            calls: list[list[str]] = []
            compared_values: list[tuple[str, str]] = []

            def read_only_probe(argv: list[str], timeout: float = 30.0) -> tuple[str, int]:
                calls.append(argv)
                if argv[1:3] == ["volume", "ls"]:
                    return "\n".join(sorted(RECEIPT.EXPECTED_FIXED_VOLUMES)), 0
                if argv[1:3] == ["ps", "--format"]:
                    return "dcim-build-kafka-1", 0
                if argv[1:3] == ["inspect", "--format"]:
                    return "dcim-build-kafka-data", 0
                if argv[1:3] == ["exec", "dcim-build-kafka-1"]:
                    return "cluster.id=synthetic-cluster-id\n", 0
                return "", 1

            def compare_digests(left: str, right: str) -> bool:
                compared_values.append((left, right))
                return left == right

            with (
                mock.patch.object(RECEIPT, "_run", side_effect=read_only_probe),
                mock.patch.object(
                    RECEIPT.hmac,
                    "compare_digest",
                    side_effect=compare_digests,
                ),
            ):
                observation = RECEIPT.collect_runtime_binding(root)

            self.assertIsNotNone(observation)
            if observation is None:
                self.fail("runtime observation unexpectedly absent")
            self.assertRegex(observation.binding_sha256, r"^[0-9a-f]{64}$")
            self.assertNotIn("synthetic-cluster-id", repr(observation))
            self.assertEqual(len(compared_values), 1)
            for digest in compared_values[0]:
                self.assertRegex(digest, r"^[0-9a-f]{64}$")
                self.assertNotEqual(digest, "synthetic-cluster-id")
            self.assertFalse(any(call[1:2] == ["run"] for call in calls))

    def test_runtime_collection_accepts_expected_named_and_anonymous_volumes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_synthetic_runtime(root)
            volumes = "\n".join(
                sorted(RECEIPT.EXPECTED_FIXED_VOLUMES | {"0" * 64, "1" * 64})
            )

            def read_only_probe(argv: list[str], timeout: float = 30.0) -> tuple[str, int]:
                if argv[1:3] == ["volume", "ls"]:
                    return volumes, 0
                if argv[1:3] == ["ps", "--format"]:
                    return "dcim-build-kafka-1", 0
                if argv[1:3] == ["inspect", "--format"]:
                    return "dcim-build-kafka-data", 0
                if argv[1:3] == ["exec", "dcim-build-kafka-1"]:
                    return "cluster.id=synthetic-cluster-id\n", 0
                return "", 1

            with mock.patch.object(RECEIPT, "_run", side_effect=read_only_probe):
                observation = RECEIPT.collect_runtime_binding(root)

            self.assertIsNotNone(observation)
            if observation is None:
                self.fail("runtime observation unexpectedly absent")
            self.assertRegex(observation.binding_sha256, r"^[0-9a-f]{64}$")

    def test_runtime_collection_fails_closed_when_root_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing_root = Path(directory) / "missing"

            observation = RECEIPT.collect_runtime_binding(missing_root)

            self.assertIsNone(observation)

    def test_runtime_collection_fails_closed_when_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_synthetic_runtime(root)
            (root / "dev-build" / "images.env").unlink()

            observation = RECEIPT.collect_runtime_binding(root)

            self.assertIsNone(observation)

    def test_runtime_collection_fails_closed_when_docker_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_synthetic_runtime(root)

            with mock.patch.object(RECEIPT, "_run", return_value=("", -1)):
                observation = RECEIPT.collect_runtime_binding(root)

            self.assertIsNone(observation)

    def test_runtime_collection_fails_closed_on_volume_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_synthetic_runtime(root)
            volumes = "\n".join(
                sorted(RECEIPT.EXPECTED_FIXED_VOLUMES | {"dcim-build-extra-data"})
            )

            with mock.patch.object(RECEIPT, "_run", return_value=(volumes, 0)):
                observation = RECEIPT.collect_runtime_binding(root)

            self.assertIsNone(observation)

    def test_runtime_collection_fails_closed_on_kafka_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_synthetic_runtime(root)

            def mismatched_probe(argv: list[str], timeout: float = 30.0) -> tuple[str, int]:
                if argv[1:3] == ["volume", "ls"]:
                    return "\n".join(sorted(RECEIPT.EXPECTED_FIXED_VOLUMES)), 0
                if argv[1:3] == ["ps", "--format"]:
                    return "dcim-build-kafka-1", 0
                if argv[1:3] == ["inspect", "--format"]:
                    return "dcim-build-kafka-data", 0
                if argv[1:3] == ["exec", "dcim-build-kafka-1"]:
                    return "cluster.id=different-synthetic-cluster\n", 0
                return "", 1

            with mock.patch.object(RECEIPT, "_run", side_effect=mismatched_probe):
                observation = RECEIPT.collect_runtime_binding(root)

            self.assertIsNone(observation)

    def test_generate_without_approved_attestation_fails_closed(self) -> None:
        """Regression: Git subject capture must not preempt this fail-closed attestation result."""
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "plan.md"
            plan_path.write_bytes(self.plan_bytes)
            with mock.patch.dict(os.environ, {}, clear=True):
                receipt = RECEIPT.generate_authority_bootstrap_receipt(
                    plan_path=plan_path,
                    expected_plan_sha256=self.expected_sha256,
                    subject_dir=ROOT,
                    base_sha="e20c8e3569cb171a23fb1e4a9c417074dfb0ae8a",
                    attempt_epoch_id="epoch-test-002",
                    timeout_ms=10_000,
                    toolchain_identity=RECEIPT.ToolchainIdentity(
                        "3.12.0",
                        "4" * 64,
                        "git synthetic",
                        "make synthetic",
                        "docker synthetic",
                        "compose synthetic",
                    ),
                )
            self.assertEqual(
                receipt.computed_disposition,
                "NO-GO_DOCKER_REQUIRED_FOR_HANDOFF",
            )

    def test_cli_generate_fails_on_bad_sha(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "plan.md"
            plan_path.write_bytes(self.plan_bytes)
            tool_directory = Path(directory) / "bin"
            tool_directory.mkdir()
            synthetic_docker = tool_directory / "docker"
            synthetic_docker.write_text(
                "#!/bin/sh\n"
                'if [ "$1" = "info" ]; then echo "server=synthetic"; exit 0; fi\n'
                'if [ "$1" = "compose" ]; then echo "Docker Compose synthetic"; exit 0; fi\n'
                "exit 1\n",
                encoding="utf-8",
            )
            synthetic_docker.chmod(0o700)
            environment = os.environ.copy()
            environment["PATH"] = f"{tool_directory}{os.pathsep}{environment['PATH']}"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "generate",
                    "--plan",
                    str(plan_path),
                    "--expected-sha256",
                    "0" * 64,
                    "--subject-dir",
                    str(ROOT),
                    "--base-sha",
                    "e20c8e3569cb171a23fb1e4a9c417074dfb0ae8a",
                    "--epoch",
                    "epoch-test-003",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                env=environment,
            )
            self.assertEqual(result.returncode, 97)


if __name__ == "__main__":
    unittest.main()
