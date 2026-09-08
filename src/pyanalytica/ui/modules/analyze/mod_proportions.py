"""Analyze > Proportions module — proportion z-tests and chi-square tests."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.core import round_df
from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_groupable_columns
from pyanalytica.analyze.proportions import (
    chi_square_test, goodness_of_fit_test, one_proportion_ztest, two_proportion_ztest,
)
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.disclosure import PLOT_HEIGHT, diagnostics, supporting
from pyanalytica.ui.components.decimals_control import decimals_server, decimals_ui
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.status import status_server, status_ui
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


@module.ui
def proportions_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("test_type", "Test", choices={
                "one_prop": "One-Sample Proportion",
                "two_prop": "Two-Sample Proportion",
                "independence": "Test of Independence",
                "goodness_of_fit": "Goodness of Fit",
            }),
            ui.output_ui("test_controls"),
            ui.input_select("alternative", "Alternative",
                            choices={"two-sided": "Two-sided",
                                     "less": "Less than",
                                     "greater": "Greater than"}),
            ui.input_action_button("run_btn", "Run Test", class_="btn-primary w-100 mt-2"),
            width=300,
        ),
        # Above the result: when a run fails this is what replaces it.
        status_ui("status"),
        ui.output_ui("test_result"),
        decimals_ui("dec"),
        ui.output_ui("result_tables"),
        download_result_ui("dl"),
        code_panel_ui("code"),
    )


SUCCESS_LABEL = 'Which value counts as a "success"?'


def _success_choices(series) -> tuple[list[str], str]:
    """Offer the levels of an outcome, and pick the one worth testing.

    Sorting alphabetically and taking the first put "No" ahead of "Yes" for
    every Yes/No, Pass/Fail and True/False outcome, so the test answered the
    inverse of the question the student asked -- and the result sentence read
    plausibly either way. In a binary outcome the minority level is the event of
    interest almost every time, so default to that instead.
    """
    counts = series.dropna().astype(str).value_counts()
    levels = sorted(counts.index.tolist())
    default = counts.idxmin() if len(levels) == 2 else (levels[0] if levels else "")
    return levels, str(default)


@module.server
def proportions_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    last_result = reactive.value(None)
    status = status_server("status")
    last_test_type = reactive.value(None)
    get_dec = decimals_server("dec")

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            cats = get_groupable_columns(df)
            choices = cats if cats else list(df.columns)
            update_choices(input, "row_var", choices)
            update_choices(input, "col_var", choices)
            update_choices(input, "gof_var", choices)
            update_choices(input, "op_var", choices)
            update_choices(input, "tp_var", choices)
            update_choices(input, "tp_group", choices)

    @render.ui
    def test_controls():
        tt = input.test_type()
        df = get_current_df()
        cats = []
        if df is not None:
            cats = get_groupable_columns(df)
            if not cats:
                cats = list(df.columns)

        if tt == "one_prop":
            return ui.div(
                ui.input_select("op_var", "Variable", choices=cats),
                ui.output_ui("op_success_choices"),
                ui.input_numeric("op_p0", "Hypothesized Proportion (p0)", value=0.5,
                                 min=0.001, max=0.999, step=0.05),
            )
        elif tt == "two_prop":
            return ui.div(
                ui.input_select("tp_var", "Outcome Variable", choices=cats),
                ui.output_ui("tp_success_choices"),
                ui.input_select("tp_group", "Grouping Variable", choices=cats),
            )
        elif tt == "independence":
            return ui.div(
                ui.input_select("row_var", "Row Variable", choices=cats),
                ui.input_select("col_var", "Column Variable", choices=cats),
            )
        else:  # goodness_of_fit
            return ui.div(
                ui.input_select("gof_var", "Variable", choices=cats),
                ui.input_text("expected_probs", "Expected Proportions (optional)",
                              placeholder="A:0.25, B:0.50, C:0.25"),
            )

    @render.ui
    def op_success_choices():
        df = get_current_df()
        var = input.op_var()
        req(df is not None, var)
        vals, default = _success_choices(df[var])
        return ui.input_select(
            "op_success", SUCCESS_LABEL, choices=vals, selected=default
        )

    @render.ui
    def tp_success_choices():
        df = get_current_df()
        var = input.tp_var()
        req(df is not None, var)
        vals, default = _success_choices(df[var])
        return ui.input_select(
            "tp_success", SUCCESS_LABEL, choices=vals, selected=default
        )

    @reactive.effect
    @reactive.event(input.run_btn)
    def _run():
        df = get_current_df()
        if not require(df is not None, NO_DATASET):
            return
        tt = input.test_type()

        try:
            if tt == "one_prop":
                var = input.op_var()
                success = input.op_success()
                p0 = input.op_p0()
                alt = input.alternative()
                if not require(
                    var and success,
                    "Choose the variable and which of its values counts as a success.",
                ):
                    return
                r = one_proportion_ztest(df, var, success, p0=p0, alternative=alt)
                last_result.set(r)
                last_test_type.set("one_prop")
                state.codegen.record(r.code, action="analyze",
                                     description="One-sample proportion z-test")
                last_code.set(r.code.code)

            elif tt == "two_prop":
                var = input.tp_var()
                success = input.tp_success()
                group = input.tp_group()
                alt = input.alternative()
                if not require(
                    var and success and group,
                    "Choose the variable, which value counts as a success, and the "
                    "column that splits the two groups.",
                ):
                    return
                r = two_proportion_ztest(df, var, success, group, alternative=alt)
                last_result.set(r)
                last_test_type.set("two_prop")
                state.codegen.record(r.code, action="analyze",
                                     description="Two-sample proportion z-test")
                last_code.set(r.code.code)

            elif tt == "independence":
                row, col = input.row_var(), input.col_var()
                if not require(row and col, "Choose both variables to test for independence."):
                    return
                r = chi_square_test(df, row, col)
                last_result.set(r)
                last_test_type.set("independence")
                state.codegen.record(r.code, action="analyze",
                                     description="Chi-square test of independence")
                last_code.set(r.code.code)

            else:  # goodness_of_fit
                var = input.gof_var()
                if not require(var, "Choose the variable whose category counts you want to test."):
                    return
                probs_str = input.expected_probs().strip()
                expected = None
                if probs_str:
                    expected = {}
                    for pair in probs_str.split(","):
                        k, v = pair.strip().split(":")
                        expected[k.strip()] = float(v.strip())
                r = goodness_of_fit_test(df, var, expected)
                last_result.set(r)
                last_test_type.set("goodness_of_fit")
                state.codegen.record(r.code, action="analyze",
                                     description="Chi-square goodness-of-fit test")
                last_code.set(r.code.code)

        except Exception as e:
            last_result.set(None)
            status.failed(str(e))

    @render.ui
    def test_result():
        tt = last_test_type()
        r = last_result()
        req(tt is not None, r is not None)
        sig_class = "alert-success" if r.p_value < 0.05 else "alert-warning"
        return ui.div(ui.p(r.interpretation), class_=f"alert {sig_class}")

    @render.ui
    def result_tables():
        tt = last_test_type()
        r = last_result()
        req(tt is not None, r is not None)

        if tt == "one_prop":
            return ui.div(
                ui.h5("Test Summary"),
                ui.output_data_frame("summary_table"),
            )
        elif tt == "two_prop":
            return ui.div(
                ui.h5("Group Proportions"),
                ui.output_data_frame("summary_table"),
            )
        elif tt == "independence":
            return ui.div(
                ui.h5("Observed"),
                ui.output_data_frame("observed"),
                # Tier 2: the expected counts explain the statistic rather than
                # state the result.
                supporting(
                    "Expected counts (if the variables were unrelated)",
                    ui.output_data_frame("expected"),
                ),
            )
        else:  # goodness_of_fit
            return ui.div(
                ui.h5("Goodness-of-Fit Results"),
                ui.output_data_frame("gof_table"),
            )

    @render.data_frame
    def summary_table():
        r = last_result()
        req(r is not None)
        return render.DataGrid(round_df(r.summary, get_dec()))

    @render.data_frame
    def observed():
        r = last_result()
        tt = last_test_type()
        req(r is not None, tt == "independence")
        return render.DataGrid(round_df(r.observed.reset_index(), get_dec()))

    @render.data_frame
    def expected():
        r = last_result()
        tt = last_test_type()
        req(r is not None, tt == "independence")
        return render.DataGrid(round_df(r.expected.reset_index(), get_dec()))

    @render.data_frame
    def gof_table():
        r = last_result()
        tt = last_test_type()
        req(r is not None, tt == "goodness_of_fit")
        return render.DataGrid(round_df(r.table, get_dec()))

    def _get_dl_df():
        tt = last_test_type()
        r = last_result()
        if r is None:
            return None
        if tt in ("one_prop", "two_prop"):
            return r.summary
        elif tt == "independence":
            return r.observed.reset_index()
        else:
            return r.table

    download_result_server("dl", get_df=_get_dl_df, filename="proportions")
    code_panel_server("code", get_code=last_code)
