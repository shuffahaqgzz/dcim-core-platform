from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/phase2/kafka_topics.py"
DOC = ROOT / "docs/architecture/kafka-topics-phase2.md"
COMPOSE = ROOT / "deploy/compose/dev-build/compose.yaml"
POLICY = ROOT / "scripts/foundation_policy.py"
TOPICS = (
    "dcim.raw.synthetic",
    "dcim.normalized.events",
    "dcim.enriched.events",
    "dcim.dlq.synthetic",
)
EXPECTED_RETENTION_MS = "2592000000"
EXPECTED_MAX_MESSAGE_BYTES = "1048576"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("kafka_topics", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("kafka topic module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def describe_output(*, mutated_topic: str | None = None) -> str:
    lines: list[str] = []
    for topic in TOPICS:
        retention = "1000" if topic == mutated_topic else EXPECTED_RETENTION_MS
        lines.append(
            f"Topic: {topic}\tPartitionCount: 1\tReplicationFactor: 1\t"
            f"Configs: cleanup.policy=delete,max.message.bytes={EXPECTED_MAX_MESSAGE_BYTES},"
            f"retention.ms={retention}"
        )
    return "\n".join(lines)


class KafkaTopicContractTests(unittest.TestCase):
    def test_topic_table_is_exactly_the_phase2_contract(self) -> None:
        # Given: the owner-approved four-topic Development contract.
        expected = tuple(
            (
                topic,
                1,
                1,
                EXPECTED_RETENTION_MS,
                EXPECTED_MAX_MESSAGE_BYTES,
            )
            for topic in TOPICS
        )

        # When: the public topic specification table is read.
        module = load_module()
        actual = tuple(
            (
                spec.name,
                spec.partitions,
                spec.replication_factor,
                spec.retention_ms,
                spec.max_message_bytes,
            )
            for spec in module.TOPIC_SPECS
        )

        # Then: no extra topic or setting can enter provisioning.
        self.assertEqual(expected, actual)

    def test_parser_accepts_descriptions_with_unrelated_configs(self) -> None:
        # Given: Kafka describe output for all four topics plus a broker default.
        output = describe_output()

        # When: the pure parser and validator consume the output.
        module = load_module()
        descriptions = module.parse_topic_descriptions(output)
        errors = module.validate_topic_descriptions(descriptions)

        # Then: each exact topic is represented and no contract error remains.
        self.assertEqual(TOPICS, tuple(item.name for item in descriptions))
        self.assertEqual((), errors)

    def test_validator_rejects_missing_extra_and_mutated_descriptions(self) -> None:
        # Given: output with a missing topic, an extra topic, and unsafe retention.
        output = describe_output(mutated_topic="dcim.normalized.events")
        output = output.replace(
            "Topic: dcim.dlq.synthetic",
            "Topic: dcim.unapproved.events",
        )

        # When: the pure validation seam evaluates it.
        module = load_module()
        errors = module.validate_topic_descriptions(
            module.parse_topic_descriptions(output)
        )

        # Then: every adversarial difference is binary-observable.
        self.assertTrue(any("dcim.normalized.events" in item and "retention.ms" in item for item in errors))
        self.assertTrue(any("missing" in item and "dcim.dlq.synthetic" in item for item in errors))
        self.assertTrue(any("unexpected" in item and "dcim.unapproved.events" in item for item in errors))

    def test_validator_rejects_partition_and_replication_mutations(self) -> None:
        # Given: a topic description with topology beyond the single-broker contract.
        output = describe_output().replace(
            "Topic: dcim.raw.synthetic\tPartitionCount: 1\tReplicationFactor: 1",
            "Topic: dcim.raw.synthetic\tPartitionCount: 2\tReplicationFactor: 2",
        )

        # When: the pure validation seam evaluates it.
        module = load_module()
        errors = module.validate_topic_descriptions(
            module.parse_topic_descriptions(output)
        )

        # Then: both topology mutations fail closed.
        self.assertTrue(any("partitions" in item for item in errors))
        self.assertTrue(any("replication factor" in item for item in errors))


class KafkaTopicCliTests(unittest.TestCase):
    def run_cli(self, *arguments: str, mutated_topic: str | None = None) -> tuple[subprocess.CompletedProcess[str], list[list[str]]]:
        with tempfile.TemporaryDirectory(prefix="kafka-topics-cli-") as temporary:
            temporary_path = Path(temporary)
            capture = temporary_path / "calls.jsonl"
            docker = temporary_path / "docker"
            docker.write_text(
                "#!/usr/bin/python3\n"
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "capture = Path(os.environ['KAFKA_TEST_CAPTURE'])\n"
                "with capture.open('a', encoding='utf-8') as stream:\n"
                "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "if '--describe' in sys.argv:\n"
                "    topic = sys.argv[sys.argv.index('--topic') + 1]\n"
                "    retention = '1000' if topic == os.environ.get('KAFKA_TEST_MUTATED') else '2592000000'\n"
                "    print(f'Topic: {topic}\\tPartitionCount: 1\\tReplicationFactor: 1\\tConfigs: max.message.bytes=1048576,retention.ms={retention}')\n",
                encoding="utf-8",
            )
            docker.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{temporary}{os.pathsep}{environment['PATH']}"
            environment["KAFKA_TEST_CAPTURE"] = str(capture)
            if mutated_topic is not None:
                environment["KAFKA_TEST_MUTATED"] = mutated_topic

            # When: the real CLI invokes a docker executable at its process boundary.
            result = subprocess.run(
                [sys.executable, str(SCRIPT), *arguments],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            calls = [json.loads(line) for line in capture.read_text(encoding="utf-8").splitlines()] if capture.exists() else []
            return result, calls

    def test_provision_creates_and_synchronizes_only_four_topics(self) -> None:
        # Given: a synthetic Docker/Kafka process boundary.
        required_prefix = ["exec", "-T", "kafka"]

        # When: provisioning runs.
        result, calls = self.run_cli()

        # Then: four create and four restore-capable alter calls carry exact settings.
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(8, len(calls))
        self.assertTrue(all("--project-name" in call and "dcim-build" in call for call in calls))
        self.assertTrue(all("--profile" in call and "data" in call for call in calls))
        self.assertTrue(all("-f" in call and str(COMPOSE) in call for call in calls))
        self.assertTrue(all(call[call.index("exec"):call.index("exec") + 3] == required_prefix for call in calls))
        create_topics = [call[call.index("--topic") + 1] for call in calls if "--create" in call]
        alter_topics = [call[call.index("--entity-name") + 1] for call in calls if "--alter" in call]
        self.assertEqual(list(TOPICS), create_topics)
        self.assertEqual(list(TOPICS), alter_topics)
        self.assertTrue(all("/opt/kafka/bin/kafka-topics.sh" in call for call in calls if "--create" in call))
        self.assertTrue(all("/opt/kafka/bin/kafka-configs.sh" in call for call in calls if "--alter" in call))
        self.assertTrue(all("--if-not-exists" in call for call in calls if "--create" in call))
        self.assertTrue(all("retention.ms=2592000000" in " ".join(call) for call in calls))
        self.assertTrue(all("max.message.bytes=1048576" in " ".join(call) for call in calls))

    def test_verify_describes_all_topics_and_exits_zero(self) -> None:
        # Given: conforming synthetic Kafka topic descriptions.

        # When: verification runs through the real CLI.
        result, calls = self.run_cli("--verify")

        # Then: all and only the four topics are described successfully.
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(4, len(calls))
        self.assertTrue(all("--describe" in call for call in calls))
        self.assertEqual(list(TOPICS), [call[call.index("--topic") + 1] for call in calls])

    def test_verify_exits_nonzero_for_retention_mutation(self) -> None:
        # Given: normalized topic retention has been mutated to one second.

        # When: verification runs through the real CLI.
        result, _calls = self.run_cli(
            "--verify",
            mutated_topic="dcim.normalized.events",
        )

        # Then: verification fails and identifies the unsafe config.
        self.assertNotEqual(0, result.returncode)
        self.assertIn("dcim.normalized.events", result.stderr)
        self.assertIn("retention.ms", result.stderr)


class KafkaTopicDocumentationTests(unittest.TestCase):
    def test_documented_table_matches_topic_contract(self) -> None:
        # Given: the architecture topic table.
        text = DOC.read_text(encoding="utf-8")

        # When: machine-consumed contract tokens are counted.
        topic_rows = [line for line in text.splitlines() if line.startswith("| `dcim.")]

        # Then: the four rows carry the same retention and size constants.
        self.assertEqual(4, len(topic_rows))
        self.assertEqual(set(TOPICS), {line.split("`")[1] for line in topic_rows})
        self.assertTrue(all(EXPECTED_RETENTION_MS in line for line in topic_rows))
        self.assertTrue(all(EXPECTED_MAX_MESSAGE_BYTES in line for line in topic_rows))

    def test_retention_is_synchronized_across_runtime_policy_and_doc(self) -> None:
        # Given: Compose, policy, and architecture contract sources.
        compose = COMPOSE.read_text(encoding="utf-8")
        policy = POLICY.read_text(encoding="utf-8")
        doc = DOC.read_text(encoding="utf-8")

        # When: exact retention tokens are inspected.
        values = (
            'KAFKA_LOG_RETENTION_HOURS: "720"' in compose,
            '"KAFKA_LOG_RETENTION_HOURS": "720"' in policy,
            "--storage.tsdb.retention.time=30d" in compose,
            '"--storage.tsdb.retention.time=30d"' in policy,
            "720 hours" in doc,
            "30 days" in doc,
        )

        # Then: all three sources agree on 30-day retention.
        self.assertEqual((True,) * 6, values)

    def test_temporary_format_disposition_is_explicit(self) -> None:
        # Given: the architecture contract document.
        text = DOC.read_text(encoding="utf-8").casefold()

        # When: the mandatory disposition tokens are inspected.
        required = (
            "temporary format disposition",
            "event-envelope v0.1.0",
            "json",
            "deliberate temporary development deviation",
            "research avro target",
            "schema-registry decision",
            "compatibility tests",
            "no avro conformance claim",
        )

        # Then: the document carries every governed migration token.
        self.assertTrue(all(token in text for token in required))


if __name__ == "__main__":
    unittest.main()
