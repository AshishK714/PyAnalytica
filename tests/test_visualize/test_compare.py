"""Tests for visualize/compare.py."""

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from pyanalytica.visualize.compare import (
    bar_of_means,
    grouped_boxplot,
    grouped_violin,
    strip_plot,
)


@pytest.fixture
def df():
    np.random.seed(42)
    return pd.DataFrame({
        "cat": np.random.choice(["A", "B", "C"], 100),
        "val": np.random.randn(100),
        "grp": np.random.choice(["X", "Y"], 100),
    })


def test_grouped_boxplot(df):
    fig, snippet = grouped_boxplot(df, "cat", "val")
    assert fig is not None
    assert "boxplot" in snippet.code.lower()


def test_grouped_boxplot_hue(df):
    fig, snippet = grouped_boxplot(df, "cat", "val", hue="grp")
    assert fig is not None
    assert 'hue="grp"' in snippet.code


def test_grouped_boxplot_facet(df):
    fig, snippet = grouped_boxplot(df, "cat", "val", facet_col="grp")
    assert fig is not None
    assert "catplot" in snippet.code


def test_grouped_violin(df):
    fig, snippet = grouped_violin(df, "cat", "val")
    assert fig is not None


def test_bar_of_means(df):
    fig, snippet = bar_of_means(df, "cat", "val")
    assert fig is not None


def test_bar_of_means_no_error_bars_says_so(df):
    """seaborn draws CI bars by default, so switching them off must be in the code."""
    _, snippet = bar_of_means(df, "cat", "val", error_bars=False)
    assert "errorbar=None" in snippet.code
    _, snippet = bar_of_means(df, "cat", "val", error_bars=True)
    assert 'errorbar=("ci", 95)' in snippet.code


def test_strip_plot(df):
    fig, snippet = strip_plot(df, "cat", "val")
    assert fig is not None


def test_strip_plot_hue(df):
    fig, snippet = strip_plot(df, "cat", "val", hue="grp")
    assert fig is not None
    assert 'hue="grp"' in snippet.code
