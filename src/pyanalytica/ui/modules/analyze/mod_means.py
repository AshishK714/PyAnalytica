"""Analyze > Means module — t-tests, ANOVA, and non-parametric tests."""

from __future__ import annotations

import pandas as pd
from shiny import module, reactive, render, req, ui

from pyanalytica.core import round_df
from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_groupable_columns, get_numeric_columns
from pyanalytica.analyze.means import (
    kruskal_wallis_test, mann_whitney_test, one_sample_ttest, one_way_anova, two_sample_ttest,
)
from pyanalytica.analyze.normality import shapiro_wilk_test
from pyanalytica.ui.components.assumptions import assumption_lines
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.disclosure import PLOT_HEIGHT, diagnostics, supporting
from pyanalytica.ui.components.decimals_control import decimals_server, decimals_ui
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


@module.ui
def means_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("test_type", "Test",
                choices={
                    "one_sample": "One-sample t-test",
                    "two_sample": "Two-sample t-test",
                    "anova": "One-way ANOVA",
                    "mann_whitney": "Mann-Whitney U",
                    "kruskal": "Kruskal-Wallis H",
                    "normality": "Normality (Shapiro-Wilk)",
                }),
            ui.input_select("value_col", "Numeric Variable", choices=[]),
            ui.output_ui("test_controls"),
            ui.input_action_button("run_btn", "Run Test", class_="btn-primary w-100 mt-2"),
            width=300,
        ),
        ui.output_ui("test_result"),
        decimals_ui("dec"),
        ui.output_data_frame("group_stats"),
        download_result_ui("dl"),
        # Tier 2 -- whether the test's conditions hold is a second question.
        supporting(
            "Assumption checks",
            ui.output_ui("assumptions"),
        ),
        code_panel_ui("code"),
    )


@module.server
def means_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    test_result_val = reactive.value(None)
    get_dec = decimals_server("dec")

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            update_choices(input, "value_col", get_numeric_columns(df))

    @render.ui
    def test_controls():
        df = get_current_df()
        tt = input.test_type()
        alt_select = ui.input_select("alternative", "Alternative Hypothesis",
            choices={"two-sided": "Two-sided (!=)", "less": "Less (<)", "greater": "Greater (>)"})
        if tt == "one_sample":
            return ui.div(
                ui.input_numeric("mu", "Hypothesized Mean", value=0),
                alt_select,
            )
        elif tt == "two_sample":
            cats = get_groupable_columns(df) if df is not None else []
            return ui.div(
                ui.input_select("group_col", "Group Variable", choices=cats),
                alt_select,
            )
        elif tt == "anova":
            cats = get_groupable_columns(df) if df is not None else []
            return ui.input_select("group_col", "Group Variable", choices=cats)
        elif tt == "mann_whitney":
            cats = get_groupable_columns(df) if df is not None else []
            return ui.div(
                ui.input_select("group_col", "Group Variable", choices=cats),
                alt_select,
            )
        elif tt == "kruskal":
            cats = get_groupable_columns(df) if df is not None else []
            return ui.input_select("group_col", "Group Variable", choices=cats)
        elif tt == "normality":
            return ui.div()
        return ui.div()

    @reactive.effect
    @reactive.event(input.run_btn)
    def _run():
        df = get_current_df()
        if not require(df is not None, NO_DATASET):
            return
        col = input.value_col()
        if not require(col, "Choose the numeric column whose mean you want to test."):
            return
        tt = input.test_type()

        try:
            alt = input.alternative() if tt in ("one_sample", "two_sample", "mann_whitney") else "two-sided"
            if tt == "one_sample":
                result = one_sample_ttest(df, col, input.mu(), alternative=alt)
            elif tt == "two_sample":
                result = two_sample_ttest(df, col, input.group_col(), alternative=alt)
            elif tt == "anova":
                result = one_way_anova(df, col, input.group_col())
            elif tt == "mann_whitney":
                result = mann_whitney_test(df, col, input.group_col(), alternative=alt)
            elif tt == "kruskal":
                result = kruskal_wallis_test(df, col, input.group_col())
            elif tt == "normality":
                nr = shapiro_wilk_test(df, col)
                # Wrap NormalityResult into a MeansTestResult-like for display
                from pyanalytica.analyze.means import MeansTestResult
                result = MeansTestResult(
                    test_name=nr.test_name,
                    statistic=nr.statistic,
                    p_value=nr.p_value,
                    effect_size=None,
                    effect_size_name="",
                    group_stats=pd.DataFrame({
                        "n": [nr.n], "skewness": [nr.skewness],
                        "kurtosis": [nr.kurtosis], "is_normal": [nr.is_normal],
                    }),
                    interpretation=nr.interpretation,
                    code=nr.code,
                )
            else:
                return
            test_result_val.set(result)
            state.codegen.record(result.code, action="analyze", description=result.test_name)
            last_code.set(result.code.code)
        except Exception as e:
            ui.notification_show(f"Error: {e}", type="error")

    @render.ui
    def test_result():
        r = test_result_val()
        req(r is not None)
        sig_class = "alert-success" if r.p_value < 0.05 else "alert-warning"
        return ui.div(
            ui.h5(r.test_name),
            ui.p(r.interpretation),
            ui.tags.small(f"Test statistic: {r.statistic} | p-value: {r.p_value} | "
                         f"Effect size ({r.effect_size_name}): {r.effect_size}", class_="text-muted"),
            class_=f"alert {sig_class}",
        )

    @render.data_frame
    def group_stats():
        r = test_result_val()
        req(r is not None)
        return render.DataGrid(round_df(r.group_stats, get_dec()))

    @render.ui
    def assumptions():
        r = test_result_val()
        req(r is not None)
        checks = r.assumption_checks
        if not checks:
            return ui.div()
        # n is not on the result, so take it from the group table when the
        # checks do not carry it -- a per-group test has no single n otherwise.
        n = checks.get("n")
        if n is None and getattr(r, "group_stats", None) is not None:
            counts = [c for c in r.group_stats.columns if str(c).lower() in ("n", "count")]
            if counts:
                n = int(r.group_stats[counts[0]].sum())
        lines = assumption_lines(checks, n=n, test_name=r.test_name)
        if not lines:
            return ui.div()
        return ui.div(
            *[ui.p(line, class_="mb-1 small") for line in lines],
            class_="mt-2 p-2 bg-light rounded",
        )

    download_result_server("dl", get_df=lambda: test_result_val().group_stats, filename="group_stats")
    code_panel_server("code", get_code=last_code)
