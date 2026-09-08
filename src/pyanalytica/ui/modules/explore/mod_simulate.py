"""Explore > Simulate module — distributions, CLT, and LLN."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.core import round_df
from pyanalytica.core.state import WorkbenchState
from pyanalytica.explore.simulate import (
    DISTRIBUTIONS,
    simulate_clt,
    simulate_distribution,
    simulate_lln,
)
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.disclosure import PLOT_HEIGHT, diagnostics, supporting
from pyanalytica.ui.components.decimals_control import decimals_server, decimals_ui
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui


_MODE_CHOICES = {
    "distribution": "Distributions",
    "clt": "Central Limit Theorem",
    "lln": "Law of Large Numbers",
}

_DIST_CHOICES = {k: k.title() for k in DISTRIBUTIONS}

_PROB_CHOICES = {
    "none": "None",
    "leq": "P(X <= x)",
    "geq": "P(X >= x)",
    "between": "P(a <= X <= b)",
    "quantile": "Quantile",
}


@module.ui
def simulate_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("mode", "Simulation", choices=_MODE_CHOICES),
            ui.input_select("dist", "Distribution", choices=_DIST_CHOICES),
            ui.output_ui("dist_description"),
            ui.output_ui("dist_params"),
            ui.output_ui("mode_controls"),
            ui.input_numeric("seed", "Seed (optional)", value=None, min=0),
            ui.input_action_button("run_btn", "Simulate", class_="btn-primary w-100 mt-2"),
            width=300,
        ),
        ui.output_ui("sim_interpretation"),
        ui.card(
            ui.card_header("Chart"),
            ui.output_ui("chart_or_message"),
            full_screen=True,
        ),
        decimals_ui("dec"),
        ui.output_data_frame("stats_table"),
        download_result_ui("dl"),
        # Tier 3 -- someone simulating a distribution is usually not asking
        # whether the sample passes a formal test of it.
        diagnostics(
            "Goodness-of-fit tests",
            ui.output_data_frame("fit_table"),
        ),
        code_panel_ui("code"),
    )


@module.server
def simulate_server(input, output, session, state: WorkbenchState):
    last_code = reactive.value("")
    _last_fig = reactive.value(None)
    _last_summary = reactive.value(None)
    _last_fit_test = reactive.value(None)
    _last_interpretation = reactive.value("")
    get_dec = decimals_server("dec")

    # --- Distribution description ---

    @render.ui
    def dist_description():
        dist_name = input.dist()
        req(dist_name)
        info = DISTRIBUTIONS.get(dist_name, {})
        rv = info.get("rv", "")
        desc = info.get("description", "")
        return ui.div(
            ui.tags.strong("Random variable: ", style="font-size: 0.85em;"),
            ui.tags.span(rv, style="font-size: 0.85em;"),
            ui.tags.br(),
            ui.tags.small(desc, class_="text-muted"),
            class_="alert alert-light py-2 px-2 mb-2",
            style="font-size: 0.82em; line-height: 1.4;",
        )

    # --- Dynamic UI for distribution parameters ---

    @render.ui
    def dist_params():
        dist_name = input.dist()
        req(dist_name)
        info = DISTRIBUTIONS.get(dist_name, {})
        param_defs = info.get("params", {})
        inputs = []
        for key, (label, default) in param_defs.items():
            step = 1 if isinstance(default, int) else 0.1
            inputs.append(
                ui.input_numeric(f"param_{key}", label, value=default, step=step)
            )
        return ui.TagList(*inputs)

    # --- Dynamic UI for mode-specific controls ---

    @render.ui
    def mode_controls():
        mode = input.mode()
        if mode == "distribution":
            return ui.TagList(
                ui.input_numeric("sample_size", "Sample Size", value=1000, min=10, max=100000, step=100),
                ui.hr(),
                ui.input_select("prob_calc", "Probability Calculator", choices=_PROB_CHOICES),
                ui.output_ui("prob_inputs"),
            )
        elif mode == "clt":
            return ui.TagList(
                ui.input_numeric("clt_n", "Sample Size (n)", value=30, min=2, max=1000, step=5),
                ui.input_numeric("clt_k", "Number of Samples (k)", value=1000, min=100, max=50000, step=100),
            )
        elif mode == "lln":
            return ui.TagList(
                ui.input_numeric("lln_max", "Max Observations", value=5000, min=100, max=100000, step=500),
            )
        return ui.div()

    @render.ui
    def prob_inputs():
        calc = input.prob_calc()
        if calc in ("leq", "geq"):
            return ui.input_numeric("prob_x", "x", value=0.0, step=0.1)
        elif calc == "between":
            return ui.TagList(
                ui.input_numeric("prob_a", "a (lower)", value=-1.0, step=0.1),
                ui.input_numeric("prob_b", "b (upper)", value=1.0, step=0.1),
            )
        elif calc == "quantile":
            return ui.input_numeric("prob_q", "Probability (0-1)", value=0.5, min=0.001, max=0.999, step=0.01)
        return ui.div()

    # --- Helpers ---

    def _collect_params() -> dict:
        dist_name = input.dist()
        info = DISTRIBUTIONS.get(dist_name, {})
        params = {}
        for key, (_, default) in info.get("params", {}).items():
            try:
                val = input[f"param_{key}"]()
                params[key] = float(val) if val is not None else default
            except Exception:
                params[key] = default
        return params

    def _get_seed() -> int | None:
        try:
            val = input.seed()
            return int(val) if val is not None else None
        except Exception:
            return None

    # --- Main run logic ---

    @reactive.calc
    @reactive.event(input.run_btn)
    def _run():
        mode = input.mode()
        dist_name = input.dist()
        params = _collect_params()
        seed = _get_seed()

        if mode == "distribution":
            sample_size = int(input.sample_size() or 1000)
            prob_calc_val = input.prob_calc()
            if prob_calc_val == "none":
                prob_calc_val = None

            prob_value = None
            prob_value2 = None
            if prob_calc_val in ("leq", "geq"):
                prob_value = float(input.prob_x())
            elif prob_calc_val == "between":
                prob_value = float(input.prob_a())
                prob_value2 = float(input.prob_b())
            elif prob_calc_val == "quantile":
                prob_value = float(input.prob_q())

            result = simulate_distribution(
                dist_name, params,
                sample_size=sample_size,
                seed=seed,
                prob_calc=prob_calc_val,
                prob_value=prob_value,
                prob_value2=prob_value2,
            )
            _last_fig.set(result.figure)
            _last_summary.set(result.summary)
            _last_fit_test.set(result.fit_test)
            _last_interpretation.set(result.prob_description)
            state.codegen.record(result.code, action="explore", description="Distribution simulation")
            last_code.set(result.code.code)
            return result

        elif mode == "clt":
            clt_n = int(input.clt_n() or 30)
            clt_k = int(input.clt_k() or 1000)
            result = simulate_clt(dist_name, params, sample_size=clt_n, num_samples=clt_k, seed=seed)
            _last_fig.set(result.figure)
            _last_summary.set(result.summary)
            _last_fit_test.set(result.fit_test)
            _last_interpretation.set(result.interpretation)
            state.codegen.record(result.code, action="explore", description="CLT simulation")
            last_code.set(result.code.code)
            return result

        elif mode == "lln":
            lln_max = int(input.lln_max() or 5000)
            result = simulate_lln(dist_name, params, max_obs=lln_max, seed=seed)
            _last_fig.set(result.figure)
            _last_summary.set(result.summary)
            _last_fit_test.set(result.fit_test)
            _last_interpretation.set(result.interpretation)
            state.codegen.record(result.code, action="explore", description="LLN simulation")
            last_code.set(result.code.code)
            return result

    # --- Outputs ---

    @render.ui
    def sim_interpretation():
        _run()
        text = _last_interpretation()
        if not text:
            return ui.div()
        return ui.div(
            ui.tags.pre(text, class_="mb-0", style="white-space: pre-wrap;"),
            class_="alert alert-info mt-2",
        )

    @render.ui
    @reactive.event(input.run_btn)
    def chart_or_message():
        _run()
        return ui.output_plot("chart", height="500px")

    @render.plot
    def chart():
        fig = _last_fig()
        req(fig is not None)
        return fig

    @render.data_frame
    def stats_table():
        _run()
        df = _last_summary()
        req(df is not None)
        return render.DataGrid(round_df(df, get_dec()), height="200px")

    @render.data_frame
    def fit_table():
        _run()
        df = _last_fit_test()
        req(df is not None)
        return render.DataGrid(round_df(df, get_dec()), height="150px")

    def _get_summary():
        return _last_summary()

    download_result_server("dl", get_df=_get_summary, filename="simulation")
    code_panel_server("code", get_code=last_code)
