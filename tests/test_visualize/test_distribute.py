"""Tests for visualize/distribute.py."""

import matplotlib
matplotlib.use("Agg")

import pandas as pd
import pytest

from pyanalytica.visualize.distribute import bar_chart, boxplot, histogram, violin


@pytest.fixture
def num_df():
    return pd.DataFrame({"values": range(100), "cat": ["A", "B"] * 50})


def test_histogram(num_df):
    fig, snippet = histogram(num_df, "values")
    assert fig is not None
    assert "histplot" in snippet.code


def test_histogram_with_kde(num_df):
    fig, snippet = histogram(num_df, "values", kde=True)
    assert fig is not None
    assert "kde=True" in snippet.code


def _run_snippet(snippet, df):
    """Execute shown code the way Report Builder does, with no plt.show()."""
    import matplotlib.pyplot as plt
    import seaborn as sns
    ns = {"df": df, "plt": plt, "sns": sns}
    exec(snippet.code.replace("plt.show()", ""), ns)
    plt.close("all")


def test_histogram_snippet_runs(num_df):
    """The shown code must draw what the panel drew, mean/median lines included."""
    _, snippet = histogram(num_df, "values")
    assert "axvline" in snippet.code
    _run_snippet(snippet, num_df)


def test_histogram_grouped_snippet_runs(num_df):
    """A bare Series plus hue="cat" is rejected by seaborn; the code must use data=."""
    _, snippet = histogram(num_df, "values", group_by="cat")
    assert 'data=df, x="values"' in snippet.code
    assert 'hue="cat"' in snippet.code
    assert "axvline" not in snippet.code
    _run_snippet(snippet, num_df)


def test_boxplot(num_df):
    fig, snippet = boxplot(num_df, "values")
    assert fig is not None
    assert "boxplot" in snippet.code.lower() or "boxplot" in snippet.code


def test_violin(num_df):
    fig, snippet = violin(num_df, "values")
    assert fig is not None


def test_bar_chart(num_df):
    fig, snippet = bar_chart(num_df, "cat")
    assert fig is not None
    assert "value_counts" in snippet.code
