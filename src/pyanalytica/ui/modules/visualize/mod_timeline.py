"""Visualize > Timeline module — time series charts."""

from __future__ import annotations

import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shiny import module, reactive, render, req, ui

Figure = matplotlib.figure.Figure

from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_datetime_columns, get_numeric_columns
from pyanalytica.data.dates import looks_like_dates
from pyanalytica.visualize.timeline import time_series
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


def _explain(message: str) -> Figure:
    """Render *message* where the chart would have been.

    Timeline refuses a date axis it cannot justify, and the refusal carries the
    reasoning -- which column, which values, what to do instead. Somewhere to
    read it that does not disappear matters more here than anywhere else in the
    app, because the alternative the student is being talked out of is a chart
    that looks entirely convincing.
    """
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axis("off")
    ax.text(
        0.5, 0.5, textwrap.fill(message, width=64),
        ha="center", va="center", fontsize=11, color="#444444", wrap=True,
    )
    fig.set_layout_engine("tight")
    return fig


@module.ui
def timeline_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("date_col", "Date Column", choices=[]),
            ui.input_select("value_col", "Value Column", choices=[]),
            ui.input_select("group_by", "Group By (optional)", choices=[""]),
            ui.input_select("agg_level", "Aggregation",
                choices=["raw", "daily", "weekly", "monthly"]),
            ui.input_select("chart_type", "Chart Type",
                choices=["line", "area", "bar"]),
            ui.input_slider("rolling", "Rolling Window", 0, 30, 0),
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
            ui.output_plot("chart", height="500px"),
            full_screen=True,
        ),
        code_panel_ui("code"),
    )


@module.server
def timeline_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    _last_fig = reactive.value(None)

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            all_cols = list(df.columns)
            # Offer only columns that can carry a timeline. Falling back to
            # every column when none qualified is what let a student pick a
            # month-name column and get a chart dated to the year 1.
            date_choices = get_datetime_columns(df)
            date_choices += [
                col for col in all_cols
                if col not in date_choices and looks_like_dates(df[col])
            ]
            update_choices(input, "date_col", date_choices)
            update_choices(input, "value_col", get_numeric_columns(df))
            update_choices(input, "group_by", [""] + all_cols, allow_none=True)

    @render.plot
    @reactive.event(input.run_btn)
    def chart():
        df = get_current_df()
        req(require(df is not None, NO_DATASET))
        date_col = input.date_col()
        value_col = input.value_col()
        req(require(
            date_col and value_col,
            "Choose both a date column and a numeric column to plot over time. "
            "If no date column is offered, this dataset has none that could be "
            "recognised as dates.",
        ))

        group = input.group_by() or None
        rolling = input.rolling() if input.rolling() > 0 else None

        try:
            fig, snippet = time_series(
                df, date_col, value_col,
                group_by=group,
                agg_level=input.agg_level(),
                chart_type=input.chart_type(),
                rolling_window=rolling,
            )
        except ValueError as exc:
            # A refused date axis is the expected outcome for a column that is
            # not dates, so explain it rather than showing a traceback -- and
            # explain it *on the panel*. A toast is gone in five seconds, and
            # this message is the whole content of the answer.
            return _explain(str(exc))
        state.codegen.record(snippet, action="visualize", description="Time series plot")
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

    code_panel_server("code", get_code=last_code)
