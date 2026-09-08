"""Model > Regression module."""

from __future__ import annotations

from datetime import datetime

from shiny import module, reactive, render, req, ui

from pyanalytica.core import round_df
from pyanalytica.core.model_store import ModelArtifact, default_model_name
from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_numeric_columns
from pyanalytica.model.regression import linear_regression
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.disclosure import (
    PLOT_HEIGHT,
    diagnostics,
    is_open,
    supporting,
)
from pyanalytica.ui.components.decimals_control import decimals_server, decimals_ui
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


def _r_squared_line(r) -> str:
    """Label each R2 by the rows it was measured on.

    With a Test Split set, the panel used to print the *training* R2 as plain
    "R2" -- the one number the split exists to avoid. Both are shown now, and
    which is which is part of the label rather than something to know already.
    """
    training = (
        f"R\u00b2 (training) = {r.r_squared:.4f} | "
        f"Adj. R\u00b2 = {r.adj_r_squared:.4f}"
    )
    if r.test_r_squared is None:
        return (
            f"R\u00b2 = {r.r_squared:.4f} | Adj. R\u00b2 = {r.adj_r_squared:.4f} "
            f"| fitted and measured on all rows -- set Test Split above to hold "
            f"some back"
        )
    return f"R\u00b2 (held-out) = {r.test_r_squared:.4f} | " + training


@module.ui
def regression_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("target", "Target (Y)", choices=[]),
            ui.input_select("features", "Features (X)", choices=[], multiple=True),
            ui.input_slider("test_size", "Test Split", 0.0, 0.5, 0.0, step=0.05),
            ui.input_numeric("random_seed", "Random Seed", value=42, min=0, max=99999),
            ui.tags.hr(),
            ui.input_text("model_name", "Save Model As", placeholder="my_regression"),
            ui.input_checkbox("save_splits", "Save train/test as datasets", value=False),
            ui.input_action_button("run_btn", "Fit Model", class_="btn-primary w-100 mt-2"),
            width=300,
        ),
        # Tier 1 -- the answer.
        ui.output_ui("model_summary"),
        decimals_ui("dec"),
        ui.output_data_frame("coef_table"),
        download_result_ui("dl"),
        # Tier 2 -- the numbers behind it. The heading is inside the section, so
        # it cannot appear over a table that failed to render.
        supporting(
            "Multicollinearity (VIF)",
            ui.output_data_frame("vif_table"),
        ),
        # Tier 3 -- these check the model rather than state the result, and they
        # need room. In the old 350px boxes their titles were clipped.
        diagnostics(
            "Diagnostic plots",
            ui.output_plot("resid_plot", height=PLOT_HEIGHT),
            ui.output_plot("qq_plot", height=PLOT_HEIGHT),
            id="diagnostics_open",
        ),
        code_panel_ui("code"),
    )


@module.server
def regression_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    result = reactive.value(None)
    get_dec = decimals_server("dec")

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            cols = get_numeric_columns(df)
            update_choices(input, "target", cols)
            update_choices(input, "features", cols)

    @reactive.effect
    # Opening a diagnostics section has to re-run this: the fit is what
    # builds the figures, and with the event limited to the button, a
    # section opened after the fit stayed empty.
    @reactive.event(input.run_btn, input["diagnostics_open"])
    def _run():
        df = get_current_df()
        if not require(df is not None, NO_DATASET):
            return
        target = input.target()
        features = list(input.features())
        if not require(
            target and features,
            "Choose a target (the Y you want to explain) and at least one "
            "feature (an X to explain it with). Hold Ctrl (Cmd on a Mac) to "
            "select more than one feature.",
        ):
            return

        # Both lists offer every column, so the first column starts selected in
        # each and a student who opens the tab and presses Run immediately gets
        # "Expected unique column names, got: 'X' 2 times" straight from pandas.
        # Explaining a variable cannot help predict itself is more use than
        # relaying that.
        if target in features:
            features = [f for f in features if f != target]
            if not features:
                require(
                    False,
                    f"'{target}' is both the target and the only feature. A "
                    f"variable cannot be used to explain itself -- choose at "
                    f"least one different feature.",
                )
                return
            ui.notification_show(
                f"'{target}' is the target, so it was left out of the features.",
                type="message",
            )
        try:
            test_size = input.test_size() if input.test_size() > 0 else None
            seed = int(input.random_seed()) if input.random_seed() is not None else 42
            # Skip building the residual and Q-Q figures while nobody is
            # looking at them. Opening the section re-runs this with them,
            # which costs a refit -- 32ms against 11ms here -- and saves
            # it on every run where the section stays shut.
            r = linear_regression(
                df, target, features, test_size=test_size, random_state=seed,
                diagnostics=is_open(input, "diagnostics_open"),
            )
            result.set(r)
            state.codegen.record(r.code, action="model", description="Linear regression")
            last_code.set(r.code.code)

            # Save the model. Always -- an empty "Save Model As" box used to
            # mean nothing was saved and nothing was said, which left Evaluate
            # and Predict permanently empty for no visible reason.
            model_name = input.model_name().strip() or default_model_name("linear_regression", target)
            artifact = ModelArtifact(
                name=model_name,
                model_type="linear_regression",
                model=r.model,
                feature_names=r.feature_names,
                target_name=target,
                created_at=datetime.now(),
                X_train=r.X_train,
                X_test=r.X_test,
                y_train=r.y_train,
                y_test=r.y_test,
            )
            state.model_store.save(model_name, artifact)
            state._notify()
            ui.notification_show(
                f"Model saved as '{model_name}'. Open it under "
                f"Model > Evaluate or Model > Predict.",
                type="message",
            )

            # Save train/test splits as datasets
            if input.save_splits():
                base = model_name or "regression"
                saved = []
                if r.X_train is not None and r.y_train is not None:
                    train_df = r.X_train.copy()
                    train_df[target] = r.y_train
                    state.load(f"{base}_train", train_df)
                    saved.append(f"{base}_train")
                if r.X_test is not None and r.y_test is not None:
                    test_df = r.X_test.copy()
                    test_df[target] = r.y_test
                    state.load(f"{base}_test", test_df)
                    saved.append(f"{base}_test")
                if saved:
                    ui.notification_show(f"Saved datasets: {', '.join(saved)}", type="message")
                else:
                    ui.notification_show("No train/test data to save (set Test Split > 0).", type="warning")

        except Exception as e:
            ui.notification_show(f"Error: {e}", type="error")

    @render.ui
    def model_summary():
        r = result()
        req(r is not None)
        return ui.div(
            ui.h5("Linear Regression"),
            ui.p(r.interpretation),
            ui.tags.small(
                _r_squared_line(r)
                + f" | F = {r.f_stat:.2f} (p = {r.f_pvalue:.4f})",
                class_="text-muted",
            ),
            class_="alert alert-info",
        )

    @render.data_frame
    def coef_table():
        r = result()
        req(r is not None)
        return render.DataGrid(round_df(r.coefficients, get_dec()))

    @render.data_frame
    def vif_table():
        r = result()
        req(r is not None)
        return render.DataGrid(round_df(r.vif, get_dec()))

    @render.plot
    def resid_plot():
        r = result()
        req(r is not None and r.residual_plot is not None)
        return r.residual_plot

    @render.plot
    def qq_plot():
        r = result()
        req(r is not None and r.qq_plot is not None)
        return r.qq_plot

    download_result_server("dl", get_df=lambda: result().coefficients, filename="coefficients")
    code_panel_server("code", get_code=last_code)
