"""Data > View module — filter, sort, browse."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.core import round_df
from pyanalytica.core.codegen import CodeSnippet
from pyanalytica.core.state import Operation, WorkbenchState
from pyanalytica.data.view import (
    FilterCondition,
    apply_filters,
    check_filter,
    sort_dataframe,
)
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.decimals_control import decimals_server, decimals_ui
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.status import status_server, status_ui
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)

from datetime import datetime


@module.ui
def view_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.h5("Filter"),
            ui.input_select("filter_col", "Column", choices=[]),
            ui.input_select("filter_op", "Operator",
                choices=["==", "!=", ">", "<", ">=", "<=", "contains", "isnull", "notnull"]),
            ui.input_text("filter_val", "Value"),
            ui.input_action_button("add_filter", "Add Filter", class_="btn-sm btn-outline-primary"),
            ui.input_action_button("clear_filters", "Clear All", class_="btn-sm btn-outline-secondary"),
            ui.hr(),
            ui.h5("Sort"),
            ui.input_select("sort_col", "Sort by", choices=[]),
            ui.input_checkbox("sort_asc", "Ascending", value=True),
            ui.hr(),
            ui.input_action_button("apply_btn", "Apply to Dataset", class_="btn-primary w-100"),
            width=300,
        ),
        # Above the output: a failure belongs where the result would be.
        status_ui("status"),
        ui.output_text("filter_info"),
        decimals_ui("dec"),
        ui.output_data_frame("view_table"),
        download_result_ui("dl"),
        code_panel_ui("code"),
    )


@module.server
def view_server(input, output, session, state: WorkbenchState, get_current_df):
    filters = reactive.value([])
    status = status_server("status")
    last_code = reactive.value("")
    get_dec = decimals_server("dec")
    _prev_dataset_id = reactive.value(None)

    @reactive.effect
    def _reset_on_dataset_change():
        df = get_current_df()
        new_id = id(df) if df is not None else None
        if new_id != _prev_dataset_id():
            _prev_dataset_id.set(new_id)
            filters.set([])
            last_code.set("")
            ui.update_select("sort_col", selected="")

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            cols = list(df.columns)
            update_choices(input, "filter_col", cols)
            update_choices(input, "sort_col", [""] + cols, allow_none=True)

    @reactive.effect
    @reactive.event(input.add_filter)
    def _add_filter():
        col = input.filter_col()
        op = input.filter_op()
        val = input.filter_val()
        if not require(col, "Choose the column to filter on first."):
            return
        f = FilterCondition(column=col, operator=op, value=val)
        # Check before the filter joins the list. A filter that cannot mean
        # anything used to be accepted and then break every output that read
        # the frame -- the table, the row count, the download -- so the panel
        # emptied and the reason appeared nowhere.
        df = get_current_df()
        try:
            if df is not None:
                check_filter(df, f)
        except ValueError as exc:
            require(False, str(exc))
            return
        current = filters()
        filters.set(current + [f])

    @reactive.effect
    @reactive.event(input.clear_filters)
    def _clear():
        filters.set([])

    @reactive.calc
    def filtered_df():
        df = get_current_df()
        req(df is not None)
        fs = filters()
        if fs:
            try:
                df, snippet = apply_filters(df, fs)
            except ValueError as exc:
                # The dataset changed under a filter that no longer fits it.
                require(False, str(exc) + " The filter has been removed.")
                filters.set([])
                return get_current_df()
            last_code.set(snippet.code)
        sort_col = input.sort_col()
        if sort_col:
            df, snippet = sort_dataframe(df, [sort_col], [input.sort_asc()])
            last_code.set(snippet.code)
        return df

    @render.text
    def filter_info():
        df = get_current_df()
        fdf = filtered_df()
        if df is None:
            return ""
        fs = filters()
        n_filters = len(fs)
        return f"Showing {len(fdf):,} of {len(df):,} rows | {n_filters} filter(s) active"

    @render.data_frame
    def view_table():
        df = filtered_df()
        req(df is not None)
        return render.DataGrid(round_df(df.head(500), get_dec()), height="500px")

    @reactive.effect
    @reactive.event(input.apply_btn)
    def _apply():
        df = filtered_df()
        if not require(df is not None, NO_DATASET):
            return
        for name in state.dataset_names():
            if state.get(name) is get_current_df():
                state.update(name, df, Operation(
                    timestamp=datetime.now(), action="filter",
                    description=f"Applied filters to '{name}'", dataset=name,
                ))
                code = last_code()
                if code:
                    snippet = CodeSnippet(code=code, imports=["import pandas as pd"])
                    state.codegen.record(snippet, action="filter",
                                         description=f"Applied filters to '{name}'")
                status.done(f"Filters applied to '{name}'")
                break

    download_result_server("dl", get_df=filtered_df, filename="filtered_data")
    code_panel_server("code", get_code=last_code)
