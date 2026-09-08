"""Model > Classify module — logistic regression, decision tree."""

from __future__ import annotations

from datetime import datetime

from shiny import module, reactive, render, req, ui

from pyanalytica.core.model_store import ModelArtifact, default_model_name
from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_categorical_columns, get_numeric_columns
from pyanalytica.model.classify import decision_tree, logistic_regression, random_forest
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.status import status_server, status_ui
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


@module.ui
def classify_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("model_type", "Model",
                choices={"logistic": "Logistic Regression", "tree": "Decision Tree",
                         "rf": "Random Forest"}),
            ui.input_select("target", "Target", choices=[]),
            ui.input_select("features", "Features", choices=[], multiple=True),
            ui.input_slider("test_size", "Test Split", 0.1, 0.5, 0.3, step=0.05),
            ui.input_numeric("random_seed", "Random Seed", value=42, min=0, max=99999),
            ui.output_ui("model_options"),
            ui.tags.hr(),
            ui.input_text("model_name", "Save Model As", placeholder="my_classifier"),
            ui.input_checkbox("save_splits", "Save train/test as datasets", value=False),
            ui.input_action_button("run_btn", "Fit Model", class_="btn-primary w-100 mt-2"),
            width=300,
        ),
        # Above the result: when a run fails this is what replaces it.
        status_ui("status"),
        ui.output_ui("model_summary"),
        ui.output_data_frame("detail_table"),
        download_result_ui("dl"),
        code_panel_ui("code"),
    )


@module.server
def classify_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    result = reactive.value(None)
    status = status_server("status")

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            cats = get_categorical_columns(df)
            nums = get_numeric_columns(df)
            update_choices(input, "target", cats + nums)
            update_multi_choices(input, "features", nums)

    @render.ui
    def model_options():
        mt = input.model_type()
        if mt == "tree":
            return ui.input_slider("max_depth", "Max Depth", 1, 20, 5)
        elif mt == "rf":
            return ui.div(
                ui.input_slider("n_estimators", "Number of Trees", 10, 500, 100, step=10),
                ui.input_slider("rf_max_depth", "Max Depth (0 = None)", 0, 30, 0),
            )
        return ui.div()

    @reactive.effect
    @reactive.event(input.run_btn)
    def _run():
        df = get_current_df()
        if not require(df is not None, NO_DATASET):
            return
        target = input.target()
        features = list(input.features())
        if not require(
            target and features,
            "Choose a target (the category you want to predict) and at least "
            "one feature. Hold Ctrl (Cmd on a Mac) to select more than one "
            "feature.",
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
            status.done(
                f"'{target}' is the target, so it was left out of the features."
            )
        try:
            seed = int(input.random_seed()) if input.random_seed() is not None else 42
            model_choice = input.model_type()
            if model_choice == "logistic":
                r = logistic_regression(df, target, features,
                                        test_size=input.test_size(), random_state=seed)
                mt = "logistic_regression"
            elif model_choice == "rf":
                rf_depth = input.rf_max_depth()
                r = random_forest(df, target, features,
                                  test_size=input.test_size(),
                                  n_estimators=input.n_estimators(),
                                  max_depth=rf_depth if rf_depth > 0 else None,
                                  random_state=seed)
                mt = "random_forest"
            else:
                r = decision_tree(df, target, features,
                                  test_size=input.test_size(), max_depth=input.max_depth(),
                                  random_state=seed)
                mt = "decision_tree"
            result.set(r)
            state.codegen.record(r.code, action="model", description="Classification")
            last_code.set(r.code.code)

            # Save the model. Always -- an empty "Save Model As" box used to
            # mean nothing was saved and nothing was said, which left Evaluate
            # and Predict permanently empty for no visible reason.
            model_name = input.model_name().strip() or default_model_name(mt, target)
            artifact = ModelArtifact(
                name=model_name,
                model_type=mt,
                model=r.model,
                feature_names=r.feature_names,
                target_name=target,
                label_encoder=r.label_encoder,
                created_at=datetime.now(),
                X_train=r.X_train,
                X_test=r.X_test,
                y_train=r.y_train,
                y_test=r.y_test,
            )
            state.model_store.save(model_name, artifact)
            state._notify()
            status.done(
                f"Model saved as '{model_name}'. Open it under "
                f"Model > Evaluate or Model > Predict."
            )

            # Save train/test splits as datasets
            if input.save_splits():
                base = model_name or "classifier"
                saved = []
                if r.X_train is not None and r.y_train is not None:
                    train_df = r.X_train.copy()
                    train_df[target] = r.y_train.values
                    state.load(f"{base}_train", train_df)
                    saved.append(f"{base}_train")
                if r.X_test is not None and r.y_test is not None:
                    test_df = r.X_test.copy()
                    test_df[target] = r.y_test.values
                    state.load(f"{base}_test", test_df)
                    saved.append(f"{base}_test")
                if saved:
                    status.done(f"Saved datasets: {', '.join(saved)}")
                else:
                    status.check("No train/test data to save (set Test Split > 0).")

        except Exception as e:
            result.set(None)
            status.failed(str(e))

    @render.ui
    def model_summary():
        r = result()
        req(r is not None)
        test_str = f" | Test: {r.test_accuracy:.3f}" if r.test_accuracy else ""
        return ui.div(
            ui.h5(r.model_type),
            ui.p(f"Train accuracy: {r.train_accuracy:.3f}{test_str}"),
            class_="alert alert-info",
        )

    @render.data_frame
    def detail_table():
        r = result()
        req(r is not None)
        if r.coefficients is not None:
            return render.DataGrid(r.coefficients)
        elif r.feature_importance is not None:
            return render.DataGrid(r.feature_importance)
        return render.DataGrid(None)

    def _get_classify_detail():
        r = result()
        if r is None:
            return None
        if r.coefficients is not None:
            return r.coefficients
        return r.feature_importance

    download_result_server("dl", get_df=_get_classify_detail, filename="model_details")
    code_panel_server("code", get_code=last_code)
