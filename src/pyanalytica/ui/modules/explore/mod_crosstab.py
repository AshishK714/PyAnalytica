"""Explore > Cross-tab module — cross-tabulation with chi-square."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.core import round_df
from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_groupable_columns
from pyanalytica.explore.crosstab import create_crosstab
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.table_caption import table_caption
from pyanalytica.ui.components.decimals_control import decimals_server, decimals_ui
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


@module.ui
def crosstab_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select(
                "row_var", "Row Variable(s)", choices=[], multiple=True,
            ),
            ui.input_select("col_var", "Column Variable", choices=[]),
            ui.input_select("normalize", "Display",
                choices={"": "Counts", "index": "Row %", "columns": "Column %", "all": "Total %"}),
            ui.input_checkbox("margins", "Show Margins", value=True),
            ui.input_action_button("run_btn", "Create Cross-tab", class_="btn-primary w-100 mt-2"),
            width=300,
        ),
        ui.output_ui("chi2_result"),
        decimals_ui("dec"),
        ui.output_ui("what_the_numbers_are"),
        ui.output_data_frame("crosstab_table"),
        download_result_ui("dl"),
        code_panel_ui("code"),
    )


@module.server
def crosstab_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    get_dec = decimals_server("dec")

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            cat_cols = get_groupable_columns(df)
            all_cols = list(df.columns)
            choices = cat_cols if cat_cols else all_cols
            update_multi_choices(input, "row_var", choices)
            col_choices = {"": "(None)", **{c: c for c in choices}}
            update_choices(input, "col_var", col_choices)

    @reactive.calc
    @reactive.event(input.run_btn)
    def result():
        df = get_current_df()
        req(require(df is not None, NO_DATASET))
        row = [c for c in (input.row_var() or ()) if c]
        col = input.col_var()
        req(require(row, "Choose a Rows variable to tabulate."))

        normalize = input.normalize() or None
        ct_result = create_crosstab(df, row, col_var=col or None, normalize=normalize, margins=input.margins())
        state.codegen.record(ct_result.code, action="explore", description="Cross-tabulation")
        last_code.set(ct_result.code.code)
        return ct_result

    @render.ui
    def what_the_numbers_are():
        req(result() is not None)
        return ui.tags.p(
            table_caption(input.normalize() or None, margins=input.margins()),
            class_="text-muted small mb-2",
        )

    @render.ui
    def chi2_result():
        r = result()
        req(r is not None)
        if r.chi2 is None:
            return ui.div(
                ui.h5("Frequency Table"),
                ui.p(r.interpretation),
                class_="alert alert-info",
            )
        return ui.div(
            ui.h5("Chi-Square Test"),
            ui.p(r.interpretation),
            ui.tags.small(
                f"\u03c7\u00b2 = {r.chi2}, df = {r.dof}, p = {r.p_value}",
                class_="text-muted",
            ),
            class_="alert alert-info",
        )

    @render.data_frame
    def crosstab_table():
        r = result()
        req(r is not None)
        return render.DataGrid(round_df(r.table.reset_index(), get_dec()), height="400px")

    download_result_server("dl", get_df=lambda: result().table.reset_index(), filename="crosstab")
    code_panel_server("code", get_code=last_code)
