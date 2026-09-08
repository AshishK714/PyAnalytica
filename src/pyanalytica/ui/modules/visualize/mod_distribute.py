"""Visualize > Distribute module — histogram, box, violin, bar."""

from __future__ import annotations

import pandas as pd
from shiny import module, reactive, render, req, ui

from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import ColumnType, classify_column, get_groupable_columns
from pyanalytica.visualize.distribute import bar_chart, boxplot, histogram, violin
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


@module.ui
def distribute_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("col", "Variable", choices=[]),
            ui.input_select("chart_type", "Chart Type",
                choices=["histogram", "boxplot", "violin", "bar"]),
            ui.output_ui("chart_options"),
            ui.input_select("group_by", "Group By (optional)", choices=[""]),
            ui.input_select("facet_col", "Facet Column (optional)", choices=[""]),
            ui.input_select("facet_row", "Facet Row (optional)", choices=[""]),
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
            ui.output_ui("chart_or_message"),
            full_screen=True,
        ),
        code_panel_ui("code"),
    )


@module.server
def distribute_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    _last_fig = reactive.value(None)
    _error_msg = reactive.value("")

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            cat_cols = get_groupable_columns(df)
            update_choices(input, "col", list(df.columns))
            update_choices(input, "group_by", [""] + cat_cols, allow_none=True)
            update_choices(input, "facet_col", [""] + cat_cols, allow_none=True)
            update_choices(input, "facet_row", [""] + cat_cols, allow_none=True)

    @render.ui
    def chart_options():
        ct = input.chart_type()
        if ct == "histogram":
            return ui.TagList(
                ui.input_slider("bins", "Bins", 5, 100, 30),
                ui.input_checkbox("kde", "Show KDE", value=False),
            )
        elif ct == "bar":
            return ui.TagList(
                ui.input_checkbox("pct", "Show Percentages", value=False),
                ui.input_select("orientation", "Orientation",
                    choices=["vertical", "horizontal"]),
            )
        return ui.div()

    @render.ui
    @reactive.event(input.run_btn)
    def chart_or_message():
        df = get_current_df()
        req(require(df is not None, NO_DATASET))
        col = input.col()
        req(require(col, "Choose a column to show the distribution of."))
        ct = input.chart_type()

        # Validate: histogram/boxplot/violin need numeric columns
        is_numeric = pd.api.types.is_numeric_dtype(df[col])
        if ct in ("histogram", "boxplot", "violin") and not is_numeric:
            _error_msg.set(f'"{col}" is not numeric. Use "bar" chart for categorical variables.')
            return ui.div(
                ui.p(
                    ui.tags.strong("Cannot plot: "),
                    f'"{col}" is a categorical/text column. '
                    f'Histogram, boxplot, and violin require a numeric variable. '
                    f'Switch to "bar" chart type for categorical data.',
                    class_="text-danger mt-3 mx-3",
                ),
            )
        if ct == "bar" and is_numeric:
            pass  # bar on numeric is fine (value_counts still works)

        _error_msg.set("")
        group = input.group_by() or None
        facet_c = input.facet_col() or None
        facet_r = input.facet_row() or None

        if ct == "histogram":
            fig, snippet = histogram(
                df, col, bins=input.bins(), kde=input.kde(),
                group_by=group, facet_col=facet_c, facet_row=facet_r,
            )
        elif ct == "boxplot":
            fig, snippet = boxplot(df, col, group_by=group, facet_col=facet_c, facet_row=facet_r)
        elif ct == "violin":
            fig, snippet = violin(df, col, group_by=group, facet_col=facet_c, facet_row=facet_r)
        elif ct == "bar":
            fig, snippet = bar_chart(
                df, col, orientation=input.orientation(), pct=input.pct(),
                group_by=group, facet_col=facet_c, facet_row=facet_r,
            )
        else:
            return ui.div()

        state.codegen.record(snippet, action="visualize", description="Distribution plot")
        last_code.set(snippet.code)
        _last_fig.set(fig)
        return ui.output_plot("chart", height="500px")

    @render.plot
    def chart():
        fig = _last_fig()
        req(fig is not None)
        req(_error_msg() == "")
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

    code_panel_server("code", get_code=last_code)
