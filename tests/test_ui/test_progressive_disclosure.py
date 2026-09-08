"""A panel shows its answer and offers the rest -- see docs/DISCLOSURE.md.

Every panel used to render everything it could compute: 103 outputs and 18
plots across 30 panels, against eight uses of a collapsible container in the
whole app. The answer to the question the student asked shared the screen with
three things they did not ask for.

This is the ratchet, and it is a checklist rather than a threshold, because a
count cannot express the design: Simulate's goodness-of-fit table is tier 3
whether it is one output or five. TO_CONVERT names the panels whose tiering is
agreed but not yet built, with what still renders unconditionally in each. It
shrinks as panels move into CONVERTED and is meant never to grow -- a new entry
means a new panel was written the old way.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

MODULES = Path(__file__).resolve().parents[2] / "src" / "pyanalytica" / "ui" / "modules"

OUTPUT_CALLS = {
    "output_plot", "output_data_frame", "output_ui", "output_text",
    "output_text_verbatim", "output_image",
}
DISCLOSURE_CALLS = {"supporting", "diagnostics", "accordion", "accordion_panel"}

#: A hard ceiling, applied to every panel. Two plots on one screen means the
#: second one is competing with the first, and in every case so far the second
#: is a diagnostic.
MAX_UNCONDITIONAL_PLOTS = 1

#: The most a converted panel may put on screen without being asked.
MAX_UNCONDITIONAL_OUTPUTS = 4

#: Panels converted to the tiering. These are held to the full rules.
CONVERTED = {
    "regression", "cluster", "reduce", "evaluate", "simulate",
    "proportions", "means",
}

#: The rest of the agreed tiering from docs/DISCLOSURE.md, with the tier-2 or
#: tier-3 content that still renders unconditionally. A count alone cannot
#: express this -- Simulate's goodness-of-fit table is tier 3 whether it is one
#: output or five -- so the checklist is written out and shrinks as panels move
#: into CONVERTED.
TO_CONVERT: dict[str, str] = {}


def _panels() -> list[Path]:
    return sorted(MODULES.rglob("mod_*.py"))


def _name(path: Path) -> str:
    return path.stem.replace("mod_", "")


def _main_area_outputs(path: Path) -> tuple[int, int]:
    """(outputs, plots) rendered outside the sidebar and outside a disclosure."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    ui_fn = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.FunctionDef) and n.name.endswith("_ui")),
        None,
    )
    if ui_fn is None:
        return 0, 0

    # Anything nested inside the sidebar, or inside a disclosure, does not count.
    excluded: set[int] = set()
    for node in ast.walk(ui_fn):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        if name == "sidebar" or name in DISCLOSURE_CALLS:
            for sub in ast.walk(node):
                if sub is not node:
                    excluded.add(id(sub))

    outputs = plots = 0
    for node in ast.walk(ui_fn):
        if not isinstance(node, ast.Call) or id(node) in excluded:
            continue
        name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        if name in OUTPUT_CALLS:
            outputs += 1
            if name in ("output_plot", "output_image"):
                plots += 1
    return outputs, plots


@pytest.mark.parametrize("path", _panels(), ids=_name)
def test_no_panel_draws_two_plots_unasked(path: Path):
    """The ceiling for every panel that is not already on the checklist."""
    name = _name(path)
    if name in TO_CONVERT:
        pytest.skip(f"tiering agreed, not yet built: {TO_CONVERT[name]}")
    _, plots = _main_area_outputs(path)
    assert plots <= MAX_UNCONDITIONAL_PLOTS, (
        f"{path.name} draws {plots} plots unconditionally. A second plot is "
        f"almost always a diagnostic, and a diagnostic nobody asked for "
        f"competes with the answer for the only screen either of them has. "
        f"Put it in a diagnostics() section -- see docs/DISCLOSURE.md."
    )


@pytest.mark.parametrize("name", sorted(CONVERTED))
def test_a_converted_panel_shows_its_answer_and_offers_the_rest(name: str):
    path = next(p for p in _panels() if _name(p) == name)
    outputs, plots = _main_area_outputs(path)
    assert outputs <= MAX_UNCONDITIONAL_OUTPUTS, (
        f"{path.name} renders {outputs} outputs unconditionally."
    )
    source = path.read_text(encoding="utf-8")
    assert "supporting(" in source or "diagnostics(" in source, (
        f"{path.name} is listed as converted but discloses nothing."
    )


def test_the_checklist_names_panels_that_exist():
    """A stale name would silently track nothing."""
    names = {_name(p) for p in _panels()}
    unknown = (set(TO_CONVERT) | CONVERTED) - names
    assert not unknown, f"the checklist names panels that do not exist: {unknown}"


def test_a_panel_is_not_both_converted_and_pending():
    assert not (CONVERTED & set(TO_CONVERT))


def test_regression_is_the_worked_example():
    """The first panel converted, and the shape the rest follow."""
    path = MODULES / "model" / "mod_regression.py"
    outputs, plots = _main_area_outputs(path)
    assert plots == 0, "both diagnostic plots belong inside the disclosure"
    assert outputs <= MAX_UNCONDITIONAL_OUTPUTS

    source = path.read_text(encoding="utf-8")
    assert "supporting(" in source and "diagnostics(" in source
    # The heading moved inside the section it names.
    assert 'ui.h5("VIF (Multicollinearity)")' not in source
