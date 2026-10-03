"""Collapsible 'Show Code' panel with copy button, and 'Add to Report'.

Every panel that can show its code can also hand that code to Report
Builder. The button used to exist as a separate component that no panel had
wired up, so a student assembling a report had to switch on Procedure
recording before starting, and one who found that out after the fourth
chart started over. Putting it next to Show Code gives every panel the
button for the price of naming its action.
"""

from __future__ import annotations

import re
from typing import Callable

from shiny import module, reactive, render, ui

#: What each prefix in shown code needs imported. Report Builder pre-imports
#: these names before running a cell, so the list is for the HTML and the
#: notebook export, where a reader expects to see them.
_IMPORTS = [
    (r"\bpd\.", "import pandas as pd"),
    (r"\bnp\.", "import numpy as np"),
    (r"\bplt\.", "import matplotlib.pyplot as plt"),
    (r"\bsns\.", "import seaborn as sns"),
    (r"\bstats\.", "from scipy import stats"),
]


def infer_imports(code: str) -> list[str]:
    """The import lines a snippet needs, read off the prefixes it uses."""
    return [line for pattern, line in _IMPORTS if re.search(pattern, code)]


@module.ui
def code_panel_ui():
    """Show Code panel UI."""
    return ui.div(
        ui.input_action_button("toggle_code", "Show Code", class_="btn-sm btn-outline-secondary"),
        ui.input_action_button(
            "add_to_report", "Add to Report", class_="btn-sm btn-outline-success ms-2",
        ),
        ui.output_ui("code_display"),
        class_="mt-3",
    )


@module.server
def code_panel_server(
    input, output, session,
    get_code: Callable[[], str],
    state=None,
    action: str = "",
    description: str | Callable[[], str] = "",
):
    """Server logic for code panel.

    *state* is the WorkbenchState whose report builder receives the code;
    *action* is the badge the report shows; *description* names the cell and
    may be a callable for a panel whose result changes with its inputs.
    """
    show_code = reactive.value(False)

    @reactive.effect
    @reactive.event(input.toggle_code)
    def _toggle():
        show_code.set(not show_code())
        label = "Hide Code" if show_code() else "Show Code"
        ui.update_action_button("toggle_code", label=label)

    @reactive.effect
    @reactive.event(input.add_to_report)
    def _add():
        code = get_code()
        if state is None:
            ui.notification_show("This panel cannot add to the report.", type="warning")
            return
        if not code:
            ui.notification_show("Run something first, then add its result to the report.", type="warning")
            return
        state.report_builder.add_code_cell(
            action=action,
            description=description() if callable(description) else description,
            code=code,
            imports=infer_imports(code),
        )
        n = state.report_builder.cell_count()
        state._notify_report()
        ui.notification_show(
            f"Added to Report Builder ({n} cell{'s' if n != 1 else ''}). "
            f"Open Report > Report Builder to run and export it.",
            type="message",
        )

    @render.ui
    def code_display():
        if not show_code():
            return ui.div()
        code = get_code()
        if not code:
            return ui.div("No code generated yet.", class_="text-muted")
        return ui.div(
            ui.tags.pre(
                ui.tags.code(code, class_="language-python"),
                class_="bg-light p-3 rounded border",
                style="max-height: 400px; overflow-y: auto;",
            ),
            class_="mt-2",
        )
