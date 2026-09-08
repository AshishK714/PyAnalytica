"""What the Model tab's numbers are *labelled* as.

The Model sweep found the arithmetic clean -- coefficients, accuracies, AUC,
k-means sizes and PCA variance all matched an independent sklearn computation to
four decimals, including the leakage check where AUC goes 0.6335 -> 0.8644 when
call_seconds is added. Every defect was in the framing instead:

  * a Test Split control whose held-out R2 was computed and then not reported,
    so the panel answered with the training figure;
  * text features refused by sklearn with "could not convert string to float:
    'admin.'", which names a value rather than a column;
  * accuracy printed with no baseline, on an outcome where always answering
    "No" scores 88.7%.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pyanalytica.model._validate import require_numeric_features
from pyanalytica.model.classify import decision_tree, logistic_regression, random_forest
from pyanalytica.model.cluster import kmeans_cluster
from pyanalytica.model.reduce import pca_analysis
from pyanalytica.model.regression import linear_regression


@pytest.fixture
def noise():
    """More columns than rows can support: train R2 flatters, test R2 does not."""
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.normal(size=(60, 25)), columns=[f"x{i}" for i in range(25)])
    df["y"] = rng.normal(size=60)
    return df


@pytest.fixture
def mixed():
    return pd.DataFrame({
        "age": [25, 34, 41, 52, 29, 38, 47, 61],
        "spend": [10.0, 22.5, 31.0, 44.0, 12.5, 27.0, 38.5, 51.0],
        "job": ["admin.", "services", "admin.", "technician",
                "services", "admin.", "technician", "services"],
        "bought": [0, 1, 0, 1, 0, 1, 1, 1],
    })


# --------------------------------------------------- the held-out R2 is reported


def test_a_test_split_reports_the_held_out_r_squared(noise):
    feats = [f"x{i}" for i in range(25)]
    r = linear_regression(noise, "y", feats, test_size=0.3, random_state=42)
    assert r.test_r_squared is not None
    # Fitted on noise: the training figure looks like a model, the honest one
    # does not. Reporting only the first is the defect.
    assert r.r_squared > 0.4
    assert r.test_r_squared < 0


def test_no_split_means_no_held_out_number_to_report(noise):
    feats = [f"x{i}" for i in range(25)]
    r = linear_regression(noise, "y", feats)
    assert r.test_r_squared is None


def test_the_interpretation_says_which_rows_each_figure_came_from(noise):
    feats = [f"x{i}" for i in range(25)]
    split = linear_regression(noise, "y", feats, test_size=0.3, random_state=42)
    assert "held-out" in split.interpretation
    assert "trained on" in split.interpretation

    whole = linear_regression(noise, "y", feats)
    assert "same rows" in whole.interpretation


def test_held_out_r_squared_matches_sklearn(mixed):
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import train_test_split

    r = linear_regression(mixed, "spend", ["age"], test_size=0.5, random_state=7)
    X_tr, X_te, y_tr, y_te = train_test_split(
        mixed[["age"]], mixed["spend"], test_size=0.5, random_state=7
    )
    expected = LinearRegression().fit(X_tr, y_tr).score(X_te, y_te)
    assert r.test_r_squared == pytest.approx(expected, abs=1e-4)


# ------------------------------------------------- text features are explained


@pytest.mark.parametrize(
    "fit",
    [
        lambda df: linear_regression(df, "spend", ["age", "job"]),
        lambda df: logistic_regression(df, "bought", ["age", "job"]),
        lambda df: decision_tree(df, "bought", ["age", "job"]),
        lambda df: random_forest(df, "bought", ["age", "job"]),
        lambda df: kmeans_cluster(df, ["age", "job"], chosen_k=2),
        lambda df: pca_analysis(df, ["age", "job"]),
    ],
)
def test_a_text_feature_is_refused_in_words_the_reader_can_act_on(mixed, fit):
    with pytest.raises(ValueError) as exc:
        fit(mixed)
    message = str(exc.value)
    assert "'job'" in message, "the column must be named"
    assert "admin." in message, "show the values that caused it"
    assert "Dummy Encode" in message, "name the screen that fixes it"
    assert "could not convert string to float" not in message


def test_numeric_and_boolean_features_are_left_alone(mixed):
    frame = mixed.assign(flag=[True, False, True, False, True, False, True, False])
    require_numeric_features(frame, ["age", "spend", "flag"], "A model")


def test_an_unknown_column_says_so(mixed):
    with pytest.raises(ValueError, match="not in the dataset"):
        require_numeric_features(mixed, ["age", "salery"], "A model")


# ------------------------------------------------------- the arithmetic itself


def test_the_leakage_check_still_reproduces(tmp_path):
    """The sweep's headline case, in miniature: a leaked column lifts AUC.

    Kept as a test because it is the one result the whole Model tab exists to
    teach, and a wrapper change that quietly broke the split would still leave
    every other assertion in this file passing.
    """
    from sklearn.metrics import roc_auc_score

    rng = np.random.default_rng(3)
    n = 800
    signal = rng.normal(size=n)
    outcome = (signal + rng.normal(scale=0.6, size=n) > 0.8).astype(int)
    df = pd.DataFrame({
        "noise_a": rng.normal(size=n),
        "noise_b": rng.normal(size=n),
        "leak": outcome * 3.0 + rng.normal(scale=0.3, size=n),
        "y": outcome,
    })

    without = logistic_regression(df, "y", ["noise_a", "noise_b"], test_size=0.3)
    with_leak = logistic_regression(df, "y", ["noise_a", "noise_b", "leak"], test_size=0.3)

    auc_without = roc_auc_score(without.y_test, without.probabilities)
    auc_with = roc_auc_score(with_leak.y_test, with_leak.probabilities)
    assert auc_without < 0.62
    assert auc_with > 0.95
