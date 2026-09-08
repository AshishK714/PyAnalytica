"""Model > Predict module — run saved models on new data."""

from __future__ import annotations

import pandas as pd
from shiny import module, reactive, render, req, ui

from pyanalytica.core import round_df
from pyanalytica.core.state import WorkbenchState
from pyanalytica.model.predict import predict_from_artifact
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.decimals_control import decimals_server, decimals_ui
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.status import status_server, status_ui
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


@module.ui
def predict_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("model_name", "Saved Model", choices=[]),
            ui.input_select("data_source", "Data Source", choices={
                "train": "Training Set",
                "test": "Test Set",
                "loaded": "Loaded Dataset",
                "upload": "Upload New CSV",
            }),
            ui.output_ui("dataset_selector"),
            ui.output_ui("upload_input"),
            ui.input_action_button("predict_btn", "Run Prediction", class_="btn-primary w-100 mt-2"),
            ui.tags.hr(),
            ui.input_text("save_name", "Save Predictions As", placeholder="predictions"),
            ui.input_action_button("save_btn", "Save to Workbench", class_="btn-outline-primary w-100 mt-1"),
            width=300,
        ),
        # Above the result: when a run fails this is what replaces it.
        status_ui("status"),
        ui.output_ui("predict_summary"),
        decimals_ui("dec"),
        ui.output_data_frame("predict_table"),
        download_result_ui("dl"),
        code_panel_ui("code"),
    )


@module.server
def predict_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    pred_df = reactive.value(None)
    status = status_server("status")
    get_dec = decimals_server("dec")

    @reactive.effect
    def _update_models():
        state._change_signal()
        models = state.model_store.list_models()
        update_choices(input, "model_name", models)

    @render.ui
    def dataset_selector():
        if input.data_source() == "loaded":
            state._change_signal()
            names = state.dataset_names()
            return ui.input_select("loaded_dataset", "Dataset", choices=names)
        return ui.div()

    @render.ui
    def upload_input():
        if input.data_source() == "upload":
            return ui.input_file("upload_file", "Upload CSV", accept=[".csv"])
        return ui.div()

    @reactive.effect
    @reactive.event(input.predict_btn)
    def _predict():
        model_name = input.model_name()
        if not require(
            model_name,
            "No saved model chosen. Run a model under Model > Regression or "
            "Model > Classify first; it is saved automatically.",
        ):
            return
        try:
            artifact = state.model_store.get(model_name)
            source = input.data_source()
            actual_values = None

            if source == "train":
                if artifact.X_train is None:
                    status.check("No training data stored.")
                    return
                df = artifact.X_train.copy()
                if artifact.y_train is not None:
                    actual_values = artifact.y_train
            elif source == "test":
                if artifact.X_test is None:
                    status.check("No test data stored.")
                    return
                df = artifact.X_test.copy()
                if artifact.y_test is not None:
                    actual_values = artifact.y_test
            elif source == "loaded":
                ds_name = input.loaded_dataset()
                if not require(ds_name, "Choose which loaded dataset to predict on."):
                    return
                df = state.get(ds_name)
                # If the loaded dataset has the target column, grab actuals
                if artifact.target_name in df.columns:
                    actual_values = df[artifact.target_name]
            else:  # upload
                file_info = input.upload_file()
                if not require(file_info, "Choose a file to predict on first."):
                    return
                file_path = file_info[0]["datapath"]
                df = pd.read_csv(file_path)
                if artifact.target_name in df.columns:
                    actual_values = df[artifact.target_name]

            result_df, snippet = predict_from_artifact(artifact, df)

            # Insert actual values right before prediction column for easy comparison
            if actual_values is not None:
                col_name = f"actual_{artifact.target_name}"
                pred_idx = result_df.columns.get_loc("prediction")
                result_df.insert(pred_idx, col_name, actual_values.values)

            pred_df.set(result_df)
            state.codegen.record(snippet, action="model", description="Prediction")
            last_code.set(snippet.code)
            status.done(
                f"Predictions generated: {len(result_df)} rows."
            )

        except Exception as e:
            pred_df.set(None)
            status.failed(str(e))

    @reactive.effect
    @reactive.event(input.save_btn)
    def _save():
        df = pred_df()
        if not require(df is not None, "Run a prediction before saving it."):
            return
        name = input.save_name().strip()
        if not name:
            name = "predictions"
        state.load(name, df)
        status.done(f"Saved as '{name}'.")

    @render.ui
    def predict_summary():
        df = pred_df()
        req(df is not None)
        n = len(df)
        pred_col = "prediction"
        if pred_col in df.columns:
            valid = df[pred_col].notna().sum()
            return ui.div(
                ui.h5("Prediction Results"),
                ui.p(f"{valid} / {n} rows predicted."),
                class_="alert alert-success",
            )
        return ui.div()

    @render.data_frame
    def predict_table():
        df = pred_df()
        req(df is not None)
        return render.DataGrid(round_df(df.head(500), get_dec()), height="500px")

    download_result_server("dl", get_df=pred_df, filename="predictions")
    code_panel_server("code", get_code=last_code)
