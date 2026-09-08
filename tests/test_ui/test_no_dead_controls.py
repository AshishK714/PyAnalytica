"""Every control the app renders must be read by the code behind it.

Two defects have had this shape. Bar charts show Group By, Facet Column and
Facet Row, accept values for all three and pass none of them to the plotting
function (issue 6). Model > Evaluate rendered a Classification Threshold slider
whose value was never read at all, so moving it from 0.5 to 0.9 left every
metric identical -- in the panel where trading precision against recall is the
entire lesson.

A student cannot tell a control that does nothing from one whose effect they do
not yet understand. This is an AST check, so it runs in milliseconds and needs
no browser; it catches the "never read" case. The "read and then dropped" case
(issue 6) needs the call site checked too, which is left to the panel's own
tests.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

MODULES = Path(__file__).resolve().parents[2] / "src" / "pyanalytica" / "ui" / "modules"

# Buttons and links are pressed, not read.
NO_VALUE_TO_READ = {"input_action_button", "input_action_link"}

#: Controls known to be inert, each with the reason it is still rendered.
#: Empty, and meant to stay that way -- a control with no effect is a bug, not
#: a style preference. Add an entry only alongside the issue that tracks it.
KNOWN_INERT: dict[str, str] = {}


def _module_files() -> list[Path]:
    return sorted(MODULES.rglob("mod_*.py"))


def _declared(tree: ast.AST) -> list[tuple[str, str, int]]:
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        if not name or not name.startswith("input_"):
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            out.append((first.value, name, node.lineno))
    return out


def _read(tree: ast.AST) -> set[str]:
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "input":
                used.add(node.attr)
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            if node.value.id == "input" and isinstance(node.slice, ast.Constant):
                used.add(str(node.slice.value))
    return used


@pytest.mark.parametrize("path", _module_files(), ids=lambda p: p.stem)
def test_every_rendered_control_is_read(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    used = _read(tree)

    dead = [
        f"  {path.name}:{lineno} — {input_id} ({kind})"
        for input_id, kind, lineno in _declared(tree)
        if kind not in NO_VALUE_TO_READ
        and input_id not in used
        and f"{path.stem}:{input_id}" not in KNOWN_INERT
    ]

    assert not dead, (
        "These controls are rendered but their value is never read, so changing "
        "them changes nothing and the student is given no way to tell:\n"
        + "\n".join(dead)
        + "\n\n  Either use the value, or stop rendering the control."
    )


def test_the_modules_directory_is_where_we_think_it_is():
    assert MODULES.is_dir()
    assert len(_module_files()) > 20
