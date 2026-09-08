"""Model evaluation for both kinds of model.

Evaluate used to be classification-only while offering every saved model,
so choosing a regression gave scikit-learn's "continuous is not supported"
under a Confusion Matrix heading. Refusing those models would have been the
smaller fix and the wrong one: checking a regression against held-out rows
is a thing to want, and this is where a student looks for it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, mean_absolute_error,
    mean_squared_error, precision_score, r2_score, recall_score,
    roc_auc_score, roc_curve,
)

from pyanalytica.core.codegen import CodeSnippet

Figure = matplotlib.figure.Figure


@dataclass
class EvaluationResult:
    """Result of model evaluation."""
    confusion_matrix: pd.DataFrame
    accuracy: float
    precision: float
    recall: float
    f1: float
    auc: float | None = None
    roc_curve_plot: Figure | None = None
    profit_curve_plot: Figure | None = None
    fairness_metrics: dict | None = None
    code: CodeSnippet = field(default_factory=lambda: CodeSnippet(code=""))


@dataclass
class RegressionEvaluation:
    """How well a fitted regression does on a set of rows."""
    r_squared: float
    rmse: float
    mae: float
    n: int
    target: str
    predicted_vs_actual: Figure | None = None
    residual_plot: Figure | None = None
    interpretation: str = ""
    code: CodeSnippet = field(default_factory=lambda: CodeSnippet(code=""))

    @property
    def summary(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Measure": [
                "R\u00b2",
                "RMSE (typical error, in units of the target)",
                "MAE (average error, in units of the target)",
                "Rows",
            ],
            # object dtype: a row count and three decimals in one column
            # otherwise coerce to float, and "Rows 214.0000" reads as a
            # measurement rather than a count.
            "Value": pd.Series(
                [round(self.r_squared, 4), round(self.rmse, 4),
                 round(self.mae, 4), self.n],
                dtype=object,
            ),
        })


def evaluate_regression(
    y_true: pd.Series | np.ndarray,
    y_pred: pd.Series | np.ndarray,
    target: str = "the target",
    plots: bool = True,
) -> RegressionEvaluation:
    """Score a regression's predictions against what actually happened.

    R-squared says how much of the variation is accounted for; RMSE and MAE say
    how wrong a typical prediction is, in the units of the target, which is
    usually the more useful of the two for someone deciding whether to trust it.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"There are {len(y_true)} actual values and {len(y_pred)} predictions; "
            f"they have to describe the same rows."
        )
    if len(y_true) < 2:
        raise ValueError("Two rows at least are needed to score a regression.")

    r2 = float(r2_score(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    spread = float(np.std(y_true, ddof=1))

    comparison = (
        f"about {rmse / spread:.2f} times the spread of {target}"
        if spread > 0 else "not comparable -- the target does not vary"
    )
    if r2 < 0:
        # Saying it accounts for 0% of the variation understates this: the
        # model is worse than the flat line, not merely uninformative.
        interpretation = (
            f"R\u00b2 = {r2:.3f} on these {len(y_true):,} rows. A negative "
            f"R\u00b2 means the model does worse here than predicting the "
            f"average of {target} every time. A typical prediction is out by "
            f"{rmse:.3g} ({comparison})."
        )
    else:
        interpretation = (
            f"R\u00b2 = {r2:.3f} on these {len(y_true):,} rows: the model "
            f"accounts for {r2 * 100:.1f}% of the variation in {target}. A "
            f"typical prediction is out by {rmse:.3g} ({comparison})."
        )

    fig_pred = fig_resid = None
    if plots:
        fig_pred, ax = plt.subplots(figsize=(8, 5))
        ax.scatter(y_true, y_pred, alpha=0.5)
        lo, hi = float(np.min(y_true)), float(np.max(y_true))
        ax.plot([lo, hi], [lo, hi], "r--", label="perfect prediction")
        ax.set_xlabel(f"Actual {target}")
        ax.set_ylabel(f"Predicted {target}")
        ax.set_title("Predicted vs Actual")
        ax.legend()
        fig_pred.set_layout_engine("tight")

        residuals = y_true - y_pred
        fig_resid, ax2 = plt.subplots(figsize=(8, 5))
        ax2.scatter(y_pred, residuals, alpha=0.5)
        ax2.axhline(0, color="red", linestyle="--")
        ax2.set_xlabel(f"Predicted {target}")
        ax2.set_ylabel("Residual (actual - predicted)")
        ax2.set_title("Residuals vs Predicted")
        fig_resid.set_layout_engine("tight")

    code = (
        "from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score\n"
        "import numpy as np\n\n"
        "y_pred = model.predict(X_test)\n"
        "print(f\"R2:   {r2_score(y_test, y_pred):.4f}\")\n"
        "print(f\"RMSE: {np.sqrt(mean_squared_error(y_test, y_pred)):.4f}\")\n"
        "print(f\"MAE:  {mean_absolute_error(y_test, y_pred):.4f}\")"
    )

    return RegressionEvaluation(
        r_squared=round(r2, 4),
        rmse=round(rmse, 4),
        mae=round(mae, 4),
        n=len(y_true),
        target=target,
        predicted_vs_actual=fig_pred,
        residual_plot=fig_resid,
        interpretation=interpretation,
        code=CodeSnippet(
            code=code,
            imports=[
                "import numpy as np",
                "from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score",
            ],
        ),
    )


def evaluate_classification(
    y_true: pd.Series | np.ndarray,
    y_pred: pd.Series | np.ndarray,
    y_prob: pd.Series | np.ndarray | None = None,
    cost_matrix: dict | None = None,
    protected_col: pd.Series | None = None,
) -> EvaluationResult:
    """Evaluate a classification model comprehensively."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    labels = sorted(set(y_true) | set(y_pred))
    cm_df = pd.DataFrame(cm, index=[f"Actual: {l}" for l in labels],
                         columns=[f"Predicted: {l}" for l in labels])

    # Basic metrics (handle multiclass with 'weighted')
    avg = "binary" if len(labels) == 2 else "weighted"
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, average=avg, zero_division=0)
    rec = recall_score(y_true, y_pred, average=avg, zero_division=0)
    f1 = f1_score(y_true, y_pred, average=avg, zero_division=0)

    # AUC and ROC curve
    auc_val = None
    roc_fig = None
    if y_prob is not None and len(labels) == 2:
        y_prob = np.asarray(y_prob)
        try:
            auc_val = round(roc_auc_score(y_true, y_prob), 4)
            fpr, tpr, thresholds = roc_curve(y_true, y_prob)
            roc_fig, ax = plt.subplots(figsize=(8, 6))
            ax.plot(fpr, tpr, "b-", linewidth=2, label=f"AUC = {auc_val:.3f}")
            ax.plot([0, 1], [0, 1], "r--", label="Random")
            ax.set_xlabel("False Positive Rate")
            ax.set_ylabel("True Positive Rate")
            ax.set_title("ROC Curve")
            ax.legend()
            ax.set_xlim([0, 1])
            ax.set_ylim([0, 1.05])
            roc_fig.set_layout_engine("tight")
        except Exception:
            logging.getLogger(__name__).warning("ROC/AUC computation failed", exc_info=True)

    # Profit curve
    profit_fig = None
    if y_prob is not None and cost_matrix and len(labels) == 2:
        y_prob_arr = np.asarray(y_prob)
        sorted_idx = np.argsort(-y_prob_arr)
        tp_cost = cost_matrix.get("tp", 1)
        fp_cost = cost_matrix.get("fp", -1)
        tn_cost = cost_matrix.get("tn", 0)
        fn_cost = cost_matrix.get("fn", 0)

        profits = []
        for i in range(len(sorted_idx) + 1):
            predicted_pos = set(sorted_idx[:i])
            profit = 0
            for j in range(len(y_true)):
                if j in predicted_pos:
                    profit += tp_cost if y_true[j] == 1 else fp_cost
                else:
                    profit += tn_cost if y_true[j] == 0 else fn_cost
            profits.append(profit)

        profit_fig, ax = plt.subplots(figsize=(8, 5))
        pct = np.linspace(0, 100, len(profits))
        ax.plot(pct, profits, "b-", linewidth=2)
        ax.set_xlabel("Percentage of Population Targeted")
        ax.set_ylabel("Profit")
        ax.set_title("Profit Curve")
        ax.axhline(y=0, color="gray", linestyle="--")
        profit_fig.set_layout_engine("tight")

    # Fairness metrics
    fairness = None
    if protected_col is not None and len(labels) == 2:
        protected = np.asarray(protected_col)
        groups = sorted(set(protected))
        fairness = {}
        group_rates = {}
        for g in groups:
            mask = protected == g
            g_pred = y_pred[mask]
            g_true = y_true[mask]
            pos_rate = np.mean(g_pred == 1) if len(g_pred) > 0 else 0
            tpr_g = np.mean(g_pred[g_true == 1] == 1) if np.sum(g_true == 1) > 0 else 0
            group_rates[g] = {"positive_rate": round(pos_rate, 4), "tpr": round(tpr_g, 4)}

        fairness["group_rates"] = group_rates
        rates = [v["positive_rate"] for v in group_rates.values()]
        if max(rates) > 0:
            fairness["disparate_impact"] = round(min(rates) / max(rates), 4)

    code = (
        'from sklearn.metrics import accuracy_score, confusion_matrix, '
        'precision_score, recall_score, f1_score\n\n'
        'cm = confusion_matrix(y_true, y_pred)\n'
        'print("Confusion Matrix:")\n'
        'print(cm)\n'
        'print(f"Accuracy: {accuracy_score(y_true, y_pred):.3f}")\n'
        'print(f"Precision: {precision_score(y_true, y_pred, average=\'weighted\'):.3f}")\n'
        'print(f"Recall: {recall_score(y_true, y_pred, average=\'weighted\'):.3f}")\n'
        'print(f"F1: {f1_score(y_true, y_pred, average=\'weighted\'):.3f}")'
    )

    return EvaluationResult(
        confusion_matrix=cm_df,
        accuracy=round(acc, 4),
        precision=round(prec, 4),
        recall=round(rec, 4),
        f1=round(f1, 4),
        auc=auc_val,
        roc_curve_plot=roc_fig,
        profit_curve_plot=profit_fig,
        fairness_metrics=fairness,
        code=CodeSnippet(code=code, imports=[
            "from sklearn.metrics import accuracy_score, confusion_matrix, "
            "precision_score, recall_score, f1_score",
        ]),
    )
