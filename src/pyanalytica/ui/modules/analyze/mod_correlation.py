"""Analyze > Correlation module — Pearson/Spearman tests."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_numeric_columns
from pyanalytica.analyze.correlation import correlation_test
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.status import status_server, status_ui
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


@module.ui
def correlation_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("x", "Variable X", choices=[]),
            ui.input_select("y", "Variable Y", choices=[]),
            ui.input_select("method", "Method", choices=["pearson", "spearman"]),
            ui.input_select("alternative", "Alternative Hypothesis",
                choices={"two-sided": "Two-sided (!=)", "less": "Less (<)", "greater": "Greater (>)"}),
            ui.input_action_button("run_btn", "Run Test", class_="btn-primary w-100 mt-2"),
            width=300,
        ),
        # Above the result: when a run fails this is what replaces it.
        status_ui("status"),
        ui.output_ui("test_result"),
        code_panel_ui("code"),
    )


@module.server
def correlation_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    result = reactive.value(None)
    status = status_server("status")

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            cols = get_numeric_columns(df)
            update_choices(input, "x", cols)
            update_choices(input, "y", cols)

    @reactive.effect
    @reactive.event(input.run_btn)
    def _run():
        df = get_current_df()
        if not require(df is not None, NO_DATASET):
            return
        x, y = input.x(), input.y()
        if not require(
            x and y,
            "Choose both variables. A correlation measures how two columns move "
            "together, so it needs an X and a Y.",
        ):
            return
        try:
            r = correlation_test(df, x, y, method=input.method(), alternative=input.alternative())
            result.set(r)
            state.codegen.record(r.code, action="analyze", description="Correlation test")
            last_code.set(r.code.code)
        except Exception as e:
            result.set(None)
            status.failed(str(e))

    @render.ui
    def test_result():
        r = result()
        req(r is not None)
        sig_class = "alert-success" if r.p_value < 0.05 else "alert-warning"
        return ui.div(
            ui.h5(f"{r.method.title()} Correlation"),
            ui.p(r.interpretation),
            ui.tags.small(
                f"r = {r.r:.4f} | p = {r.p_value:.4f} | n = {r.n} | "
                f"95% CI [{r.ci_lower:.4f}, {r.ci_upper:.4f}]",
                class_="text-muted",
            ),
            class_=f"alert {sig_class}",
        )

    code_panel_server("code", get_code=last_code)
