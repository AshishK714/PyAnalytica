"""Relate > Summarize module — group-by aggregation."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.core import round_df
from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_categorical_columns, get_numeric_columns
from pyanalytica.explore.summarize import group_summarize
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.decimals_control import decimals_server, decimals_ui
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


@module.ui
def summarize_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("group_cols", "Group By", choices=[], multiple=True),
            ui.input_select("value_cols", "Value Columns", choices=[], multiple=True),
            ui.input_checkbox_group("agg_funcs", "Aggregation Functions",
                choices={"count": "Count", "mean": "Mean", "median": "Median",
                         "sum": "Sum", "min": "Min", "max": "Max",
                         "std": "Std Dev", "nunique": "Unique Count"},
                selected=["mean", "count"]),
            ui.input_checkbox("pct_total", "Show % of Total", value=False),
            ui.input_action_button("run_btn", "Summarize", class_="btn-primary w-100 mt-2"),
            width=300,
        ),
        decimals_ui("dec"),
        ui.output_data_frame("summary_table"),
        download_result_ui("dl"),
        code_panel_ui("code"),
    )


@module.server
def summarize_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    last_desc = reactive.value("Group summary")
    get_dec = decimals_server("dec")

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            update_multi_choices(input, "group_cols", list(df.columns))
            update_multi_choices(input, "value_cols", get_numeric_columns(df))

    @reactive.calc
    @reactive.event(input.run_btn)
    def result():
        df = get_current_df()
        req(require(df is not None, NO_DATASET))
        group_cols = list(input.group_cols())
        value_cols = list(input.value_cols())
        agg_funcs = list(input.agg_funcs())
        req(require(
            group_cols,
            "Choose at least one column to group by. Hold Ctrl (Cmd on a Mac) "
            "to select more than one.",
        ))

        result_df, snippet = group_summarize(
            df, group_cols, value_cols, agg_funcs if value_cols else ["count"], input.pct_total()
        )
        what = ", ".join(value_cols) if value_cols else "row count"
        last_desc.set(f"Group summary: {what} by {', '.join(group_cols)}")
        state.codegen.record(snippet, action="explore", description=last_desc())
        last_code.set(snippet.code)
        return result_df

    @render.data_frame
    def summary_table():
        df = result()
        req(df is not None)
        return render.DataGrid(round_df(df, get_dec()), height="500px")

    download_result_server("dl", get_df=result, filename=lambda: last_desc() or "summary", decimals=get_dec)
    code_panel_server("code", get_code=last_code, state=state, action="explore", description=last_desc)
