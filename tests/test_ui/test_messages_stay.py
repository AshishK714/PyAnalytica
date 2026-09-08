"""A message about an action must stay on the panel -- issue 11.

`ui.notification_show` is a toast: about five seconds, then gone. In a teaching
tool the error is often the most instructive output on the screen, assignments
ask for a screenshot of what happened, and a toast hides a stale result -- once
it expires the panel is showing a confident answer beside inputs that failed.

The `status_server` handle keeps the message in the panel and toasts alongside
it, so this is a ratchet: a bare notification_show in a converted panel means
the pattern came back.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

MODULES = Path(__file__).resolve().parents[2] / "src" / "pyanalytica" / "ui" / "modules"

#: Panels not yet converted, with the reason. Both are the unswept section F of
#: the QA plan and out of scope for this term's teaching, so changing their
#: behaviour would mean changing code with no coverage behind it. Shrink only.
NOT_CONVERTED = {
    "homework": "unswept (QA plan section F) and not used this term",
    "practice": "unswept (QA plan section F) and not used this term",
}


def _panels() -> list[Path]:
    return sorted(MODULES.rglob("mod_*.py"))


def _name(path: Path) -> str:
    return path.stem.replace("mod_", "")


def _direct_toasts(path: Path) -> list[int]:
    """Lines calling ui.notification_show directly."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "notification_show":
            found.append(node.lineno)
    return found


@pytest.mark.parametrize("path", _panels(), ids=_name)
def test_a_panel_does_not_speak_only_in_toasts(path: Path):
    name = _name(path)
    if name in NOT_CONVERTED:
        pytest.skip(f"not converted: {NOT_CONVERTED[name]}")

    lines = _direct_toasts(path)
    assert not lines, (
        f"{path.name} calls ui.notification_show at line(s) "
        f"{', '.join(map(str, lines))}. A toast is gone in five seconds: it "
        f"cannot be re-read, cannot be screenshotted for an assignment, and "
        f"leaves a failed run's stale result on screen with nothing marking "
        f"it. Use the status handle -- status.failed / .check / .done -- which "
        f"keeps the message in the panel and toasts alongside it."
    )


@pytest.mark.parametrize("path", _panels(), ids=_name)
def test_a_panel_that_reports_has_somewhere_to_report_it(path: Path):
    """A handle with no status_ui writes messages nobody can see."""
    source = path.read_text(encoding="utf-8")
    if "status_server(" not in source:
        pytest.skip("this panel reports nothing")
    assert 'status_ui("status")' in source, (
        f"{path.name} takes a status handle but never renders the area, so its "
        f"messages go nowhere."
    )


def test_the_exception_list_names_panels_that_exist():
    names = {_name(p) for p in _panels()}
    unknown = set(NOT_CONVERTED) - names
    assert not unknown, f"the exception list names panels that do not exist: {unknown}"


def test_the_exception_list_is_still_needed():
    """When a panel is converted its entry should go, so the list shrinks."""
    stale = [
        name for name in NOT_CONVERTED
        if not any(_direct_toasts(p) for p in _panels() if _name(p) == name)
    ]
    assert not stale, (
        f"these no longer use toasts and no longer need an exception: {stale}"
    )
