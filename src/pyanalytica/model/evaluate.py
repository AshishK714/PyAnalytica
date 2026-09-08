"""Model evaluation — confusion matrix, ROC, AUC, profit curves, fairness."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_score,
    recall_score, roc_auc_score, roc_curve,
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
