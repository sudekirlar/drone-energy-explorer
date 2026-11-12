"""Guards the layer rule from CONTRIBUTING.md.

Streamlit may only be imported in app.py and src/sections/. The calculation (src/data, src/ml)
and drawing (src/charts) layers stay plain Python so they can be tested without a browser.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PURE_LAYERS = ["src/data", "src/charts", "src/ml"]


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("layer", PURE_LAYERS)
def test_pure_layers_do_not_import_streamlit(layer: str) -> None:
    offenders = [
        str(p.relative_to(ROOT))
        for p in (ROOT / layer).rglob("*.py")
        if "streamlit" in _imported_modules(p)
    ]
    assert not offenders, f"streamlit imported outside the UI layer: {offenders}"
