"""Describe > One Variable: a number and a category each get their ladder."""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import seaborn as sns
from scipy import stats

from pyanalytica.ask import describe_one


@pytest.fixture
def df():
    rng = np.random.default_rng(3)
    return pd.DataFrame({
        "tuition": np.r_[rng.normal(3000, 500, 60), rng.normal(12000, 3000, 140)],
        "type": rng.choice(["Public", "Private", "Private"], 200),
        "code": rng.choice([1, 2], 200),
        "empty": [np.nan] * 200,
    })


def _run(code: str, df: pd.DataFrame) -> dict:
    ns = {"df": df.copy(), "pd": pd, "np": np, "plt": plt, "sns": sns, "stats": stats}
    exec(code.replace("plt.show()", ""), ns)
    plt.close("all")
    return ns


def test_number_gets_summary_histogram_boxplot_and_normality(df):
    r = describe_one(df, "tuition")
    assert r.kind == "number"
    assert "ranges from" in r.answer.sentence
    assert "missing" in r.answer.table["statistic"].tolist()
    assert r.answer.figure is not None
    assert "boxplot" in r.picture.code.code
    assert "Shapiro" in r.test.sentence or "normal" in r.test.sentence.lower()


def test_category_gets_counts_bar_and_goodness_of_fit(df):
    r = describe_one(df, "type")
    assert r.kind == "category"
    assert "most common is Private" in r.answer.sentence
    assert set(r.answer.table.columns) == {"type", "count", "percent"}
    assert r.answer.table["percent"].sum() == pytest.approx(100, abs=0.2)
    assert "distribution of type" in r.test.sentence


def test_small_integer_column_is_a_category_unless_told_otherwise(df):
    assert describe_one(df, "code").kind == "category"
    assert describe_one(df, "code", treat="number").kind == "number"


def test_empty_column_is_refused_with_a_sentence(df):
    with pytest.raises(ValueError, match="every value is missing"):
        describe_one(df, "empty")


def test_unknown_column_is_refused(df):
    with pytest.raises(ValueError, match="not a column"):
        describe_one(df, "nope")


@pytest.mark.parametrize("col", ["tuition", "type"])
def test_combined_code_runs(df, col):
    r = describe_one(df, col, second_picture=True)
    ns = _run(r.code.code, df)
    assert isinstance(ns["result"], pd.DataFrame)


def test_second_picture_only_when_asked(df):
    assert describe_one(df, "tuition").picture.figure is None
    assert describe_one(df, "tuition", second_picture=True).picture.figure is not None
