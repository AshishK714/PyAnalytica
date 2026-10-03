"""Describe > Correlate module — correlation matrix, pair plot."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_numeric_columns
from pyanalytica.visualize.correlate import correlation_matrix, pair_plot
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


@module.ui
def correlate_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("cols", "Variables", choices=[], multiple=True),
            ui.input_select("chart_type", "Chart Type",
                choices=["correlation_matrix", "pair_plot"]),
            ui.input_select("method", "Method", choices=["pearson", "spearman"]),
            ui.input_slider("threshold", "|r| Threshold", 0.0, 1.0, 0.0, step=0.05),
            ui.input_action_button("run_btn", "Plot", class_="btn-primary w-100 mt-2"),
            width=280,
        ),
        ui.card(
            ui.card_header(
                ui.div(
                    {"class": "d-flex justify-content-between align-items-center"},
                    ui.span("Chart"),
                    ui.input_action_button("expand_btn", "Expand",
                        class_="btn btn-outline-secondary btn-sm"),
                ),
            ),
            ui.output_ui("guidance"),
            ui.output_plot("chart", height="600px"),
            full_screen=True,
        ),
        code_panel_ui("code"),
    )


@module.server
def correlate_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    _last_fig = reactive.value(None)

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            update_multi_choices(input, "cols", get_numeric_columns(df))

    @render.plot
    @reactive.event(input.run_btn)
    def chart():
        df = get_current_df()
        req(require(df is not None, NO_DATASET))
        cols = list(input.cols())
        # Was a bare req(len(cols) >= 2), which aborts the render silently: a
        # tester selecting one column saw nothing happen and no reason why. The
        # guidance output below is the persistent explanation; require() adds
        # the reply to the button press itself.
        req(require(
            len(cols) >= 2,
            "Choose at least two columns. Hold Ctrl (Cmd on a Mac) to select "
            "more than one.",
        ))
        ct = input.chart_type()

        if ct == "correlation_matrix":
            fig, snippet = correlation_matrix(df, cols, method=input.method(), threshold=input.threshold())
        else:
            fig, snippet = pair_plot(df, cols)

        state.codegen.record(snippet, action="visualize", description="Correlation plot")
        last_code.set(snippet.code)
        _last_fig.set(fig)
        return fig

    @reactive.effect
    @reactive.event(input.expand_btn)
    def _show_modal():
        m = ui.modal(
            ui.output_plot("chart_full", height="80vh"),
            size="xl",
            easy_close=True,
            title="Chart (Full Screen)",
        )
        ui.modal_show(m)

    @render.plot
    def chart_full():
        fig = _last_fig()
        req(fig is not None)
        return fig

    @render.ui
    def guidance():
        df = get_current_df()
        if df is None:
            return ui.TagList()

        chosen = list(input.cols())
        if len(chosen) >= 2:
            return ui.TagList()

        numeric_available = len(get_numeric_columns(df))
        if numeric_available < 2:
            return ui.div(
                ui.tags.strong("Cannot plot: "),
                f"this dataset has {numeric_available} numeric column"
                f"{'' if numeric_available == 1 else 's'}. A correlation "
                f"compares numeric columns to each other, so it needs at "
                f"least two.",
                class_="alert alert-warning",
            )

        return ui.div(
            ui.tags.strong("Choose at least two columns. "),
            "A correlation measures how two columns move together, so one "
            "column on its own has nothing to be compared with. Hold Ctrl "
            "(Cmd on a Mac) to select more than one.",
            class_="alert alert-info",
        )

    code_panel_server("code", get_code=last_code, state=state, action="visualize", description="Correlation matrix")
