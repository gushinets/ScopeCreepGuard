"""Enforce dependency direction, including imports inside functions."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend/src/scope_guard"
API = ROOT / "apps/api/src/scope_guard_api"


def module_graph():
    result = {}
    for directory, prefix in [(BACKEND, "scope_guard"), (API, "scope_guard_api")]:
        for path in directory.rglob("*.py"):
            name = prefix + "." + ".".join(path.relative_to(directory).with_suffix("").parts)
            name = name.removesuffix(".__init__")
            result[name] = tuple(imports(path))
    return result


def reachable_dependencies(name, graph, stop=()):
    seen, pending = set(), [name]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        if current not in stop:
            pending.extend(graph.get(current, ()))
    return seen - {name}


def imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_domain_is_independent():
    assert (BACKEND / "domain").is_dir(), "Missing pure domain boundary"
    banned = (
        "fastapi",
        "starlette",
        "sqlalchemy",
        "alembic",
        "openai",
        "reportlab",
        "scope_guard_api",
        "scope_guard.services",
        "scope_guard.database",
        "scope_guard.integrations",
        "scope_guard.infrastructure",
        "scope_guard.core",
    )
    violations = [
        (str(path), name)
        for path in (BACKEND / "domain").rglob("*.py")
        for name in imports(path)
        if name.startswith(banned)
    ]
    assert not violations, violations


def test_services_depend_on_ports():
    banned = (
        "fastapi",
        "starlette",
        "sqlalchemy",
        "scope_guard_api",
        "scope_guard.database",
        "scope_guard.integrations",
        "scope_guard.infrastructure",
    )
    violations = [
        (str(path), name)
        for path in (BACKEND / "services").rglob("*.py")
        for name in imports(path)
        if name.startswith(banned)
    ]
    assert not violations, violations
    graph = module_graph()
    for name in graph:
        if name.startswith("scope_guard.services."):
            assert not [
                dependency
                for dependency in reachable_dependencies(name, graph)
                if dependency.startswith(banned)
            ], name


def test_routes_use_services():
    assert (API / "routes").is_dir(), "Missing API composition boundary"
    banned = ("sqlalchemy", "scope_guard.database", "scope_guard.integrations")
    violations = [
        (str(path), name)
        for path in (API / "routes").rglob("*.py")
        for name in imports(path)
        if name.startswith(banned)
    ]
    assert not violations, violations
    graph = module_graph()
    for name in graph:
        if name.startswith("scope_guard_api.routes."):
            assert not [
                dependency
                for dependency in reachable_dependencies(
                    name, graph, stop=("scope_guard_api.dependencies",)
                )
                if dependency.startswith(banned)
            ], name
    for path in (API / "routes").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert ".state.database" not in source, path
        assert ".state.technical_operations" not in source, path


def test_backend_never_imports_api():
    violations = [
        (str(path), name)
        for path in BACKEND.rglob("*.py")
        for name in imports(path)
        if name.startswith("scope_guard_api")
    ]
    assert not violations, violations
    assert not (BACKEND / "modules").exists()
    assert not (BACKEND / "infrastructure").exists()
