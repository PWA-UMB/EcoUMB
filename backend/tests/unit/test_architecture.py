"""Regla de dependencia hexagonal (RNF-16): domain y application no conocen los frameworks."""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"
FRAMEWORKS = {
    "fastapi",
    "starlette",
    "sqlalchemy",
    "alembic",
    "bcrypt",
    "jwt",
    "psycopg",
    "pydantic",
}
OUTER_LAYERS = ("app.infrastructure", "app.interfaces")


def _imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _python_files(layer: str) -> list[Path]:
    return sorted((APP / layer).rglob("*.py"))


@pytest.mark.parametrize("layer", ["domain", "application"])
def test_inner_layers_do_not_import_frameworks(layer: str) -> None:
    files = _python_files(layer)
    assert files, f"no se encontraron archivos en app/{layer}"
    for path in files:
        offending = {m for m in _imports(path) if m.split(".")[0] in FRAMEWORKS}
        assert not offending, f"{path.relative_to(APP)} importa {sorted(offending)}"


@pytest.mark.parametrize("layer", ["domain", "application"])
def test_inner_layers_do_not_import_outer_layers(layer: str) -> None:
    for path in _python_files(layer):
        offending = {m for m in _imports(path) if m.startswith(OUTER_LAYERS)}
        assert not offending, f"{path.relative_to(APP)} importa {sorted(offending)}"


def test_domain_does_not_depend_on_application() -> None:
    for path in _python_files("domain"):
        offending = {m for m in _imports(path) if m.startswith("app.application")}
        assert not offending, f"{path.relative_to(APP)} importa {sorted(offending)}"
