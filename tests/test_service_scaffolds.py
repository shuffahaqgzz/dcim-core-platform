import ast
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
SERVICES = {
    "cmdb": "dcim_cmdb",
    "asset-repository": "dcim_asset_repository",
    "api": "dcim_api",
    "analytics": "dcim_analytics",
    "workflow": "dcim_workflow",
}
FORBIDDEN_REFERENCES = {
    "socket",
    "requests",
    "urllib.request",
    "httpx",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "sqlalchemy",
    "redis",
    "kafka",
    "subprocess",
}
FORBIDDEN_SUFFIXES = {
    ".sql",
    ".log",
    ".db",
    ".zip",
    ".tar",
    ".tgz",
    ".gz",
    ".7z",
    ".rar",
}


class ServiceScaffoldTests(unittest.TestCase):
    def test_service_readmes_exist_and_resolve_od_language(self) -> None:
        for service in SERVICES:
            path = ROOT / "services" / service / "README.md"
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertTrue(path.is_file(), f"missing {path.relative_to(ROOT)}")
                if path.is_file():
                    self.assertNotIn("remains OD-0", path.read_text(encoding="utf-8"))

    def test_service_pyprojects_have_exact_metadata(self) -> None:
        for service in SERVICES:
            path = ROOT / "services" / service / "pyproject.toml"
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertTrue(path.is_file(), f"missing {path.relative_to(ROOT)}")
                if not path.is_file():
                    continue
                project = tomllib.loads(path.read_text(encoding="utf-8"))["project"]
                self.assertEqual(project["name"], f"dcim-{service}")
                self.assertEqual(project["requires-python"], ">=3.12")

    def test_service_package_files_exist(self) -> None:
        for service, package in SERVICES.items():
            package_dir = ROOT / "services" / service / "src" / package
            with self.subTest(path=package_dir.relative_to(ROOT)):
                self.assertTrue(package_dir.is_dir(), f"missing {package_dir.relative_to(ROOT)}")
            for filename in ("__init__.py", "main.py"):
                path = package_dir / filename
                with self.subTest(path=path.relative_to(ROOT)):
                    self.assertTrue(path.is_file(), f"missing {path.relative_to(ROOT)}")

    def test_placeholder_modules_are_side_effect_free(self) -> None:
        for service, package in SERVICES.items():
            for filename in ("__init__.py", "main.py"):
                path = ROOT / "services" / service / "src" / package / filename
                with self.subTest(path=path.relative_to(ROOT)):
                    if not path.is_file():
                        self.fail(f"missing {path.relative_to(ROOT)}")
                    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                    allowed = (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
                               ast.AugAssign, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                    for statement in tree.body:
                        is_docstring = (
                            isinstance(statement, ast.Expr)
                            and isinstance(statement.value, ast.Constant)
                            and isinstance(statement.value.value, str)
                        )
                        self.assertTrue(
                            isinstance(statement, allowed) or is_docstring,
                            f"top-level executable statement in {path.relative_to(ROOT)}",
                        )
                    references = {
                        name.id for name in ast.walk(tree) if isinstance(name, ast.Name)
                    }
                    attributes = {
                        ".".join(attribute_parts)
                        for node in ast.walk(tree)
                        if isinstance(node, ast.Attribute)
                        for attribute_parts in [_attribute_parts(node)]
                        if attribute_parts is not None
                    }
                    for forbidden in FORBIDDEN_REFERENCES:
                        with self.subTest(reference=forbidden):
                            self.assertNotIn(forbidden, references | attributes)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.If):
                            self.assertFalse(
                                _compares_module_name(node.test),
                                f"main guard in {path.relative_to(ROOT)}",
                            )

    def test_services_readme_exists(self) -> None:
        path = ROOT / "services" / "README.md"
        self.assertTrue(path.is_file(), f"missing {path.relative_to(ROOT)}")

    def test_no_forbidden_files_under_services_or_web(self) -> None:
        for root_name in ("services", "web"):
            root = ROOT / root_name
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(ROOT)
                with self.subTest(path=relative):
                    self.assertNotIn(path.suffix.lower(), FORBIDDEN_SUFFIXES)
                    self.assertFalse(path.name.startswith(".env"))

    def test_no_sql_file_under_services(self) -> None:
        sql_files = sorted(
            path.relative_to(ROOT) for path in (ROOT / "services").rglob("*.sql")
        )
        self.assertEqual(sql_files, [], f"forbidden SQL files under services: {sql_files}")


def _attribute_parts(node: ast.Attribute) -> list[str] | None:
    parts = [node.attr]
    value = node.value
    while isinstance(value, ast.Attribute):
        parts.append(value.attr)
        value = value.value
    if not isinstance(value, ast.Name):
        return None
    parts.append(value.id)
    return list(reversed(parts))


def _compares_module_name(test: ast.expr) -> bool:
    return any(
        isinstance(node, ast.Compare)
        and any(isinstance(name, ast.Name) and name.id == "__name__" for name in ast.walk(node))
        for node in ast.walk(test)
    )


if __name__ == "__main__":
    unittest.main()
