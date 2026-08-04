from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re
import tempfile
from typing import assert_never
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_SAFETY = ROOT / "docs/workflow-safety-gates.md"
STAGE_1 = (
    "**Stage 1: Dry-run default.** All workflows default to producing notifications, "
    "ticket drafts, recommendations, or mock actions only. This is the **only "
    "available mode** in Phases 0 through 5."
)
STAGE_2 = (
    "**Stage 2: Recommendation.** The engine computes a recommended action set with "
    "blast-radius declaration and rollback plan per step. No action executes. The "
    "recommendation is advisory only."
)
PROHIBITED_IMPORTS = {
    "ansible",
    "netmiko",
    "nornir",
    "paramiko",
    "pysnmp",
    "scrapli",
}
PROHIBITED_HTTP_METHODS = {"delete", "patch", "post", "put"}
PROHIBITED_TEXT = re.compile(r"\bSNMP\s+SET\b|\bHTTP\s+(?:POST|PATCH|PUT|DELETE)\b", re.IGNORECASE)
PROHIBITED_ENTRYPOINT = re.compile(
    r"^(?:(?:automate|execute|apply|mutate)_(?:infrastructure|device|network|power|firmware|snmp)"
    r"|(?:infrastructure|device|network|power|firmware|snmp)_(?:automate|execute|apply|mutate))(?:_|$)"
)
SUBPROCESS_ALLOWED_PATHS: frozenset[Path] = frozenset({
    Path("scripts/phase2/db.py"),
    Path("scripts/phase2/kafka_topics.py"),
})


@dataclass(frozen=True, slots=True)
class Violation:
    path: Path
    reason: str


def _python_files(root: Path) -> tuple[Path, ...]:
    directories = (root / "scripts/phase2", root / "connectors")
    return tuple(
        path for directory in directories for path in sorted(directory.rglob("*.py")) if "__pycache__" not in path.parts
    )


def _import_roots(node: ast.Import | ast.ImportFrom) -> tuple[str, ...]:
    match node:
        case ast.Import(names=names):
            return tuple(name.name.split(".", maxsplit=1)[0] for name in names)
        case ast.ImportFrom(module=module):
            return () if module is None else (module.split(".", maxsplit=1)[0],)
        case unreachable:
            assert_never(unreachable)


def _call_name(node: ast.Call) -> tuple[str, str] | None:
    match node.func:  # noqa: MATCH_OK -- unmatched AST calls are outside this policy.
        case ast.Attribute(value=ast.Name(id=owner), attr=method):
            return owner, method
        case _:
            return None


def scan_retention(root: Path) -> tuple[Violation, ...]:
    violations: list[Violation] = []
    for path in _python_files(root):
        relative = path.relative_to(root)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            violations.append(Violation(relative, "malformed Python source"))
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for imported in _import_roots(node):
                    if imported in PROHIBITED_IMPORTS:
                        violations.append(Violation(relative, f"prohibited import {imported}"))
                    if imported == "subprocess" and relative not in SUBPROCESS_ALLOWED_PATHS:
                        violations.append(Violation(relative, "subprocess outside allowed adapter"))
            if isinstance(node, ast.Call):
                called = _call_name(node)
                if called is not None:
                    owner, method = called
                    if owner == "os" and method == "system":
                        violations.append(Violation(relative, "raw shell execution"))
                    if owner == "subprocess" and relative not in SUBPROCESS_ALLOWED_PATHS:
                        violations.append(Violation(relative, "subprocess call outside allowed adapter"))
                if isinstance(node.func, ast.Attribute):
                    method = node.func.attr
                    if method.lower() in PROHIBITED_HTTP_METHODS:
                        violations.append(Violation(relative, f"HTTP {method.upper()} call"))
                for keyword in node.keywords:
                    if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        violations.append(Violation(relative, "shell=True execution"))
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                normalized = node.value.strip().upper()
                if (
                    PROHIBITED_TEXT.search(node.value)
                    or normalized in {"POST", "PATCH", "PUT", "DELETE"}
                ):
                    violations.append(Violation(relative, "prohibited write verb"))
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and PROHIBITED_ENTRYPOINT.match(node.name):
                violations.append(
                    Violation(relative, f"prohibited infrastructure automation entrypoint {node.name}")
                )
    return tuple(violations)


class Stage12RetentionTests(unittest.TestCase):
    def test_phase2_and_connectors_retain_read_only_execution_boundary(self) -> None:
        # Given: the complete Phase 2 and connector Python source trees.
        # When: syntax-aware retention rules inspect executable constructs and strings.
        violations = scan_retention(ROOT)

        # Then: no infrastructure write, automation, or raw execution capability exists.
        self.assertEqual(violations, ())

    def test_subprocess_is_confined_to_docker_compose_database_adapter(self) -> None:
        # Given: the sole permitted subprocess-bearing database adapter.
        path = ROOT / "scripts/phase2/db.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }

        # When: every subprocess invocation and its command construction are inspected.
        subprocess_owners: list[str] = []
        for name, function in functions.items():
            calls = [
                node
                for node in ast.walk(function)
                if isinstance(node, ast.Call)
                and (
                    _call_name(node) is not None
                    and _call_name(node)[0] == "subprocess"
                )
            ]
            if calls:
                subprocess_owners.append(name)
                self.assertTrue(
                    all(_call_name(call) == ("subprocess", "run") for call in calls)
                )
                self.assertTrue(
                    all(
                        call.args
                        and isinstance(call.args[0], ast.Name)
                        and call.args[0].id == "command"
                        for call in calls
                    )
                )
                assignments = [
                    node.value
                    for node in function.body
                    if isinstance(node, ast.Assign)
                    and any(
                        isinstance(target, ast.Name) and target.id == "command"
                        for target in node.targets
                    )
                    and isinstance(node.value, ast.List)
                ]
                self.assertEqual(len(assignments), 1)
                first = assignments[0].elts[0]
                self.assertIsInstance(first, ast.Starred)
                self.assertIsInstance(first.value, ast.Call)
                self.assertIsInstance(first.value.func, ast.Name)
                self.assertEqual(first.value.func.id, "compose_prefix")

        # Then: only psql and pg_dump run the docker-compose-derived argv.
        self.assertEqual(subprocess_owners, ["psql", "pg_dump"])
        compose_source = ast.get_source_segment(
            path.read_text(encoding="utf-8"), functions["compose_prefix"]
        )
        self.assertIsNotNone(compose_source)
        self.assertRegex(compose_source or "", r'command\s*=\s*\[\s*"docker",\s*"compose",')

    def test_subprocess_is_confined_to_docker_compose_kafka_adapter(self) -> None:
        # Given: the sole permitted subprocess-bearing Kafka topic adapter.
        path = ROOT / "scripts/phase2/kafka_topics.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }

        # When: every subprocess invocation and its command construction are inspected.
        subprocess_owners: list[str] = []
        for name, function in functions.items():
            calls = [
                node
                for node in ast.walk(function)
                if isinstance(node, ast.Call)
                and (
                    _call_name(node) is not None
                    and _call_name(node)[0] == "subprocess"
                )
            ]
            if calls:
                subprocess_owners.append(name)
                self.assertTrue(
                    all(_call_name(call) == ("subprocess", "run") for call in calls),
                    f"{name}: all subprocess calls must be subprocess.run",
                )
                self.assertTrue(
                    all(
                        call.args
                        and isinstance(call.args[0], ast.Call)
                        and isinstance(call.args[0].func, ast.Name)
                        and call.args[0].func.id == "kafka_command"
                        for call in calls
                    ),
                    f"{name}: subprocess.run must receive kafka_command(...) as argv",
                )
                for call in calls:
                    for keyword in call.keywords:
                        self.assertNotEqual(
                            keyword.arg,
                            "shell",
                            f"{name}: subprocess.run must not use shell=True",
                        )

        # Then: only run_kafka invokes subprocess via docker-compose-derived argv.
        self.assertEqual(subprocess_owners, ["run_kafka"])

        compose_source = ast.get_source_segment(source, functions["kafka_command"])
        self.assertIsNotNone(compose_source)
        self.assertRegex(compose_source or "", r'"docker"')
        self.assertRegex(compose_source or "", r'"compose"')
        self.assertRegex(compose_source or "", r'"exec"')
        self.assertRegex(compose_source or "", r'"kafka"')

        allowed_executables = {"KAFKA_TOPICS", "KAFKA_CONFIGS"}
        module_constants: dict[str, object] = {}
        for node in tree.body:
            if isinstance(node, ast.AnnAssign):
                target = node.target
                if (
                    isinstance(target, ast.Name)
                    and target.id in allowed_executables
                    and isinstance(node.value, ast.Constant)
                ):
                    module_constants[target.id] = node.value.value
        self.assertEqual(set(module_constants.keys()), allowed_executables)
        for name, value in module_constants.items():
            self.assertIsInstance(value, str)
            self.assertIn("/kafka-", value, f"{name} must point to a kafka CLI binary")

    def test_workflow_stage_one_and_two_safety_text_remains_exact(self) -> None:
        # Given: the accepted workflow safety design text.
        text = WORKFLOW_SAFETY.read_text(encoding="utf-8")

        # When: Stage 1 and Stage 2 paragraphs are selected.
        paragraphs = text.split("\n\n")

        # Then: dry-run-only and advisory-only meaning remains byte-exact.
        self.assertIn(STAGE_1, paragraphs)
        self.assertIn(STAGE_2, paragraphs)

    def test_retention_scan_rejects_unsafe_scratch_without_pipeline_false_positives(self) -> None:
        # Given: prohibited and ordinary pipeline sources in a task-specific scratch tree.
        with tempfile.TemporaryDirectory(prefix="task12-retention-") as temporary:
            root = Path(temporary)
            connector = root / "connectors/unsafe.py"
            connector.parent.mkdir(parents=True)
            connector.write_text(
                "import safe, paramiko, pysnmp\n"
                "\ndef execute_infrastructure_change():\n    pass\n"
                "\ndef unsafe_write(client):\n"
                "    client.post()\n    client.patch()\n    client.put()\n    client.delete()\n"
                "\nSNMP_COMMAND = 'SNMP SET'\n",
                encoding="utf-8",
            )
            malformed = root / "scripts/phase2/malformed.py"
            malformed.parent.mkdir(parents=True)
            malformed.write_text("def incomplete(:\n", encoding="utf-8")
            pipeline = root / "scripts/phase2/pipeline.py"
            pipeline.write_text(
                "def execute(run_id: str) -> None:\n    return None\n"
                "\ndef reconcile_execution() -> None:\n    return None\n",
                encoding="utf-8",
            )

            # When: the retention scanner reads the isolated scratch tree.
            violations = scan_retention(root)

        # Then: unsafe capability and malformed input are rejected, normal names remain allowed.
        self.assertEqual(
            set(violations),
            {
                Violation(Path("scripts/phase2/malformed.py"), "malformed Python source"),
                Violation(Path("connectors/unsafe.py"), "prohibited import paramiko"),
                Violation(Path("connectors/unsafe.py"), "prohibited import pysnmp"),
                Violation(Path("connectors/unsafe.py"), "HTTP POST call"),
                Violation(Path("connectors/unsafe.py"), "HTTP PATCH call"),
                Violation(Path("connectors/unsafe.py"), "HTTP PUT call"),
                Violation(Path("connectors/unsafe.py"), "HTTP DELETE call"),
                Violation(Path("connectors/unsafe.py"), "prohibited write verb"),
                Violation(
                    Path("connectors/unsafe.py"),
                    "prohibited infrastructure automation entrypoint "
                    "execute_infrastructure_change",
                ),
            },
        )


if __name__ == "__main__":
    unittest.main()
