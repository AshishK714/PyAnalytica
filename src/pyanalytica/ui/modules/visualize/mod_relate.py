"""Advanced > Scatter module — scatter, hexbin."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_groupable_columns, get_numeric_columns
from pyanalytica.visualize.relate import hexbin, scatter
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.signpost import signpost
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


@module.ui
def relate_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("x", "X Variable", choices=[]),
            ui.input_select("y", "Y Variable", choices=[]),
            ui.input_select("chart_type", "Chart Type",
                choices=["scatter", "hexbin"]),
            ui.input_select("color_by", "Color By (optional)", choices=[""]),
            ui.input_select("size_by", "Size By (optional)", choices=[""]),
            ui.input_select("style_by", "Style By (optional)", choices=[""]),
            ui.input_select("facet_col", "Facet Column (optional)", choices=[""]),
            ui.input_select("facet_row", "Facet Row (optional)", choices=[""]),
            ui.input_checkbox("trend", "Show Trend Line", value=True),
            ui.input_action_button("run_btn", "Plot", class_="btn-primary w-100 mt-2"),
            width=280,
        ),
        signpost(
            "A scatter plot with colour, size, style and facets. For the answer "
            "with the correlation, its test and the fitted line attached, use "
            "Relate > Two Variables."
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
            ui.output_plot("chart", height="500px"),
            full_screen=True,
        ),
        code_panel_ui("code"),
    )


@module.server
def relate_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    _last_fig = reactive.value(None)

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            num_cols = get_numeric_columns(df)
            cat_cols = get_groupable_columns(df)
            update_choices(input, "x", num_cols)
            update_choices(input, "y", num_cols)
            update_choices(input, "color_by", [""] + cat_cols, allow_none=True)
            update_choices(input, "size_by", [""] + num_cols, allow_none=True)
            update_choices(input, "style_by", [""] + cat_cols, allow_none=True)
            update_choices(input, "facet_col", [""] + cat_cols, allow_none=True)
            update_choices(input, "facet_row", [""] + cat_cols, allow_none=True)

    @render.plot
    @reactive.event(input.run_btn)
    def chart():
        df = get_current_df()
        req(require(df is not None, NO_DATASET))
        x, y = input.x(), input.y()
        req(require(x and y, "Choose both an X and a Y variable to plot against each other."))

        color = input.color_by() or None
        size = input.size_by() or None
        style = input.style_by() or None
        facet_c = input.facet_col() or None
        facet_r = input.facet_row() or None
        ct = input.chart_type()

        if ct == "scatter":
            fig, snippet = scatter(
                df, x, y, color_by=color, size_by=size,
                style_by=style, trend_line=input.trend(),
                facet_col=facet_c, facet_row=facet_r,
            )
        else:
            fig, snippet = hexbin(df, x, y)

        state.codegen.record(snippet, action="visualize", description="Scatter plot")
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

    code_panel_server("code", get_code=last_code, state=state, action="visualize", description="Scatter plot")
