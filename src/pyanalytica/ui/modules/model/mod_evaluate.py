"""Model > Evaluate module — confusion matrix, ROC, metrics for saved models."""

from __future__ import annotations

import numpy as np
import pandas as pd

from shiny import module, reactive, render, req, ui

from pyanalytica.core.state import WorkbenchState
from pyanalytica.model.evaluate import evaluate_classification, evaluate_regression
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.disclosure import PLOT_HEIGHT, diagnostics, supporting
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


def _chosen_threshold(input, default: float = 0.5) -> float:
    """Read the threshold slider, which only exists once a binary model has run."""
    try:
        value = input.threshold()
    except Exception:
        return default
    return default if value is None else float(value)


@module.ui
def evaluate_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("model_name", "Saved Model", choices=[]),
            ui.input_select("eval_data", "Evaluate On",
                choices={"test": "Test Set", "train": "Training Set"}),
            ui.input_action_button("run_btn", "Evaluate", class_="btn-primary w-100 mt-2"),
            ui.tags.hr(),
            ui.output_ui("threshold_ui"),
            width=300,
        ),
        # Tier 1 -- how the model did. Which numbers those are depends on the
        # kind of model; the panel used to assume classification and hand a
        # regression to sklearn, which answered "continuous is not supported".
        ui.output_ui("metrics_summary"),
        ui.output_ui("cm_heading"),
        ui.output_data_frame("cm_table"),
        ui.output_data_frame("regression_table"),
        download_result_ui("dl"),
        # Tier 2 -- whichever of these the model has.
        supporting(
            "ROC curve",
            ui.output_plot("roc_plot", height=PLOT_HEIGHT),
        ),
        supporting(
            "Predicted vs actual",
            ui.output_plot("pred_vs_actual", height=PLOT_HEIGHT),
        ),
        supporting(
            "Residuals",
            ui.output_plot("resid_plot", height=PLOT_HEIGHT),
        ),
        code_panel_ui("code"),
    )


@module.server
def evaluate_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    eval_result = reactive.value(None)
    is_binary = reactive.value(False)
    last_threshold = reactive.value(None)
    reg_result = reactive.value(None)
    baseline_rate = reactive.value(None)

    @reactive.effect
    def _update_models():
        # Re-read when datasets/models change
        state._change_signal()
        models = state.model_store.list_models()
        update_choices(input, "model_name", models)

    @render.ui
    def threshold_ui():
        if is_binary():
            return ui.input_slider("threshold", "Classification Threshold", 0.0, 1.0, 0.5, step=0.01)
        return ui.div()

    @reactive.effect
    @reactive.event(input.run_btn)
    def _run():
        model_name = input.model_name()
        if not require(
            model_name,
            "No saved model chosen. Run a model under Model > Regression or "
            "Model > Classify first; it is saved automatically.",
        ):
            return
        try:
            artifact = state.model_store.get(model_name)

            # Get evaluation data
            eval_on = input.eval_data()
            if eval_on == "test":
                X = artifact.X_test
                y_encoded = artifact.y_test
            else:
                X = artifact.X_train
                y_encoded = artifact.y_train

            if X is None or y_encoded is None:
                ui.notification_show("No data available for selected split.", type="warning")
                return

            y_true = np.asarray(y_encoded)

            # A regression is scored against the same rows, with the measures
            # that mean something for a continuous target.
            if artifact.label_encoder is None and not hasattr(
                artifact.model, "predict_proba"
            ):
                r = evaluate_regression(
                    y_true,
                    artifact.model.predict(X),
                    target=artifact.target_name or "the target",
                )
                reg_result.set(r)
                eval_result.set(None)
                is_binary.set(False)
                state.codegen.record(
                    r.code, action="model", description="Regression evaluation"
                )
                last_code.set(r.code.code)
                return
            reg_result.set(None)

            # Get probabilities if available
            y_prob = None
            if hasattr(artifact.model, "predict_proba"):
                try:
                    proba = artifact.model.predict_proba(X)
                    if proba.shape[1] == 2:
                        y_prob = proba[:, 1]
                except Exception:
                    pass

            # Predictions at the chosen threshold. The slider was rendered and
            # never read, so moving it changed nothing -- and threshold tuning
            # is the whole point of reading precision against recall. Below 0.5
            # the model calls more positives (recall up, precision down); above,
            # the reverse. sklearn's .predict() is the 0.5 case.
            threshold = _chosen_threshold(input)
            # Thresholding produces 0/1, so it is only safe where those map back
            # to the model's own classes -- via the label encoder, or because
            # the target already was 0/1. Anywhere else, leave .predict() alone
            # rather than relabel the confusion matrix by accident.
            can_threshold = y_prob is not None and (
                artifact.label_encoder is not None or set(np.unique(y_true)) <= {0, 1}
            )
            if can_threshold:
                y_pred = (y_prob >= threshold).astype(int)
            else:
                y_pred = artifact.model.predict(X)
                threshold = None

            # Decode labels for display if label encoder exists
            if artifact.label_encoder is not None:
                y_true_display = artifact.label_encoder.inverse_transform(y_true.astype(int))
                y_pred_display = artifact.label_encoder.inverse_transform(y_pred.astype(int))
            else:
                y_true_display = y_true
                y_pred_display = y_pred

            is_binary.set(len(set(y_true)) == 2)

            r = evaluate_classification(y_true_display, y_pred_display, y_prob=y_prob)
            last_threshold.set(threshold)
            # Accuracy alone flatters a model on an unbalanced outcome:
            # 88.9% sounds strong until you notice that answering "No" every
            # time scores 88.7%. Keep the comparison next to the number.
            counts = pd.Series(y_true_display).value_counts(normalize=True)
            baseline_rate.set(float(counts.iloc[0]) if len(counts) else None)
            eval_result.set(r)
            state.codegen.record(r.code, action="model", description="Model evaluation")
            last_code.set(r.code.code)

        except Exception as e:
            ui.notification_show(f"Error: {e}", type="error")

    @render.ui
    def metrics_summary():
        reg = reg_result()
        if reg is not None:
            return ui.div(
                ui.h5("Regression Metrics"),
                ui.p(reg.interpretation),
                class_="alert alert-info",
            )
        r = eval_result()
        req(r is not None)
        auc_str = f" | AUC = {r.auc:.4f}" if r.auc is not None else ""
        thr = last_threshold()
        base = baseline_rate()
        notes = []
        if thr is not None:
            notes.append(
                f"Counted as a positive at a predicted probability of "
                f"{thr:.2f} or more."
            )
        if base is not None:
            verdict = "no better than" if r.accuracy <= base + 0.005 else "better than"
            notes.append(
                f"Always answering the most common class scores {base:.4f}, "
                f"so this accuracy is {verdict} that."
            )
        return ui.div(
            ui.h5("Classification Metrics"),
            ui.p(
                f"Accuracy: {r.accuracy:.4f} | Precision: {r.precision:.4f} | "
                f"Recall: {r.recall:.4f} | F1: {r.f1:.4f}{auc_str}"
            ),
            ui.tags.small(" ".join(notes), class_="text-muted") if notes else None,
            class_="alert alert-info",
        )

    @render.ui
    def cm_heading():
        # This heading used to be static, so a failed evaluation left
        # "Confusion Matrix" standing over an empty page.
        req(eval_result() is not None)
        return ui.h5("Confusion Matrix")

    @render.data_frame
    def regression_table():
        r = reg_result()
        req(r is not None)
        return render.DataGrid(r.summary)

    @render.plot
    def pred_vs_actual():
        r = reg_result()
        req(r is not None and r.predicted_vs_actual is not None)
        return r.predicted_vs_actual

    @render.plot
    def resid_plot():
        r = reg_result()
        req(r is not None and r.residual_plot is not None)
        return r.residual_plot

    @render.data_frame
    def cm_table():
        r = eval_result()
        req(r is not None)
        return render.DataGrid(r.confusion_matrix.reset_index())

    @render.plot
    def roc_plot():
        r = eval_result()
        req(r is not None and r.roc_curve_plot is not None)
        return r.roc_curve_plot

    download_result_server(
        "dl",
        get_df=lambda: (
            reg_result().summary if reg_result() is not None
            else eval_result().confusion_matrix.reset_index()
        ),
        filename="confusion_matrix",
    )
    code_panel_server("code", get_code=last_code)
