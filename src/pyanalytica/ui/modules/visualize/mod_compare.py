"""Advanced > Group Plots module — grouped box, violin, bar of means, strip."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_groupable_columns, get_numeric_columns
from pyanalytica.visualize.compare import bar_of_means, grouped_boxplot, grouped_violin, strip_plot
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.signpost import signpost
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


@module.ui
def compare_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("x_cat", "Category (X)", choices=[]),
            ui.input_select("y_num", "Numeric (Y)", choices=[]),
            ui.input_select("chart_type", "Chart Type",
                choices=["boxplot", "violin", "bar_of_means", "strip"]),
            ui.input_select("hue", "Hue (optional)", choices=[""]),
            ui.input_select("facet_col", "Facet Column (optional)", choices=[""]),
            ui.input_select("facet_row", "Facet Row (optional)", choices=[""]),
            ui.input_action_button("run_btn", "Plot", class_="btn-primary w-100 mt-2"),
            width=280,
        ),
        signpost(
            "Group plots with a hue and facets: boxplot, violin, bar of means, "
            "strip. For the group means with the t-test or ANOVA attached, use "
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
def compare_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    last_desc = reactive.value("Group plot")
    _last_fig = reactive.value(None)

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            cat_cols = get_groupable_columns(df)
            update_choices(input, "x_cat", cat_cols)
            update_choices(input, "y_num", get_numeric_columns(df))
            update_choices(input, "hue", [""] + cat_cols, allow_none=True)
            update_choices(input, "facet_col", [""] + cat_cols, allow_none=True)
            update_choices(input, "facet_row", [""] + cat_cols, allow_none=True)

    @render.plot
    @reactive.event(input.run_btn)
    def chart():
        df = get_current_df()
        req(require(df is not None, NO_DATASET))
        x, y = input.x_cat(), input.y_num()
        req(require(
            x and y,
            "Choose both a grouping column and a numeric column to compare "
            "across those groups.",
        ))
        ct = input.chart_type()
        hue = input.hue() or None
        facet_c = input.facet_col() or None
        facet_r = input.facet_row() or None

        if ct == "boxplot":
            fig, snippet = grouped_boxplot(df, x, y, hue=hue, facet_col=facet_c, facet_row=facet_r)
        elif ct == "violin":
            fig, snippet = grouped_violin(df, x, y, hue=hue, facet_col=facet_c, facet_row=facet_r)
        elif ct == "bar_of_means":
            fig, snippet = bar_of_means(df, x, y, hue=hue, facet_col=facet_c, facet_row=facet_r)
        elif ct == "strip":
            fig, snippet = strip_plot(df, x, y, hue=hue, facet_col=facet_c, facet_row=facet_r)
        else:
            return

        last_desc.set(f"{ct.replace('_', ' ').capitalize()}: {y} by {x}" + (f", split by {hue}" if hue else ""))
        state.codegen.record(snippet, action="visualize", description=last_desc())
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

    code_panel_server("code", get_code=last_code, state=state, action="visualize", description=last_desc)
