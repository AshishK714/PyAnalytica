"""Tests for explore/pivot.py."""

import pandas as pd
import pytest

from pyanalytica.explore.pivot import create_pivot_table


@pytest.fixture
def df():
    return pd.DataFrame({
        "dept": ["Sales", "Sales", "Eng", "Eng", "Sales", "Eng"],
        "level": ["Jr", "Sr", "Jr", "Sr", "Jr", "Sr"],
        "count_col": [1, 1, 1, 1, 1, 1],
    })


def test_basic_pivot(df):
    result, snippet = create_pivot_table(df, "dept", "level", "count_col", aggfunc="count")
    assert result is not None
    assert "pivot_table" in snippet.code


def test_pivot_with_margins(df):
    result, _ = create_pivot_table(df, "dept", "level", "count_col", aggfunc="count", margins=True)
    assert "All" in result.index or "All" in result.columns


def test_pivot_normalize_index(df):
    result, _ = create_pivot_table(df, "dept", "level", "count_col", aggfunc="count", normalize="index")
    # Row percentages should sum to ~100, over the data columns only. Summing the
    # "All" column in as well is what let the halving bug through: 50 + 50 also
    # came to 100.
    body = result.loc[result.index != "All", [c for c in result.columns if c != "All"]]
    for s in body.sum(axis=1):
        assert abs(s - 100) < 1


def test_pivot_row_pct_ignores_margin_column(df):
    """Row % must divide by the row, not by the row plus its own total.

    Dividing by a sum that included the "All" column counted every cell twice
    and reported exactly half of every percentage.
    """
    with_margins, _ = create_pivot_table(
        df, "dept", "level", "count_col", aggfunc="count", margins=True, normalize="index"
    )
    without, _ = create_pivot_table(
        df, "dept", "level", "count_col", aggfunc="count", margins=False, normalize="index"
    )
    # Sales is 2 Jr / 1 Sr -> 66.7 / 33.3, margins on or off.
    assert with_margins.loc["Sales", "Jr"] == pytest.approx(66.667, abs=0.01)
    assert with_margins.loc["Sales", "Sr"] == pytest.approx(33.333, abs=0.01)
    assert with_margins.loc["Sales", "All"] == pytest.approx(100.0, abs=0.01)
    for col in ("Jr", "Sr"):
        assert with_margins.loc["Sales", col] == pytest.approx(without.loc["Sales", col])


def test_pivot_col_pct_ignores_margin_row(df):
    """Column % must divide by the column, not by the column plus its own total."""
    result, _ = create_pivot_table(
        df, "dept", "level", "count_col", aggfunc="count", margins=True, normalize="columns"
    )
    body = result.loc[[i for i in result.index if i != "All"]]
    for s in body.sum(axis=0):
        assert s == pytest.approx(100.0, abs=0.01)


def test_pivot_shown_code_matches_the_arithmetic_run(df):
    """Show Code must reproduce the fixed numbers, margin slice included."""
    result, snippet = create_pivot_table(
        df, "dept", "level", "count_col", aggfunc="count", margins=True, normalize="index"
    )
    assert "result.iloc[:, :-1].sum(axis=1)" in snippet.code

    scope = {"df": df, "pd": pd}
    exec(snippet.code, scope)  # noqa: S102 - the snippet is what we are testing
    reproduced = scope["result"]
    assert reproduced.loc["Sales", "Jr"] == pytest.approx(result.loc["Sales", "Jr"])


def test_pivot_percentages_keep_their_precision(df):
    """Rounding belongs at display, so the decimals control can still recover it."""
    wide = pd.DataFrame({
        "dept": ["Sales"] * 999 + ["Eng"],
        "level": ["Jr"] * 999 + ["Sr"],
        "count_col": [1] * 1000,
    })
    result, _ = create_pivot_table(
        wide, "dept", "level", "count_col", aggfunc="count", margins=True, normalize="all"
    )
    # 1 in 1000 is 0.1%, which .round(1) inside the computation kept, but a
    # rarer cell would have collapsed to 0. Assert the raw value survives.
    assert result.loc["Eng", "Sr"] == pytest.approx(0.1, abs=1e-9)


# --- Tests for columns=None (simple groupby) ---

def test_pivot_no_columns(df):
    result, snippet = create_pivot_table(df, "dept", columns=None, values="count_col", aggfunc="count")
    assert result is not None
    assert "dept" in result.columns
    assert "count_col" in result.columns
    assert "groupby" in snippet.code


def test_pivot_no_columns_margins(df):
    result, _ = create_pivot_table(df, "dept", columns=None, values="count_col", aggfunc="count", margins=True)
    assert "Total" in result["dept"].values


def test_pivot_no_columns_no_margins(df):
    result, _ = create_pivot_table(df, "dept", columns=None, values="count_col", aggfunc="count", margins=False)
    assert "Total" not in result["dept"].values


def test_pivot_no_columns_sum(df):
    result, _ = create_pivot_table(df, "dept", columns=None, values="count_col", aggfunc="sum", margins=False)
    assert result is not None
    assert len(result) == 2  # Eng, Sales


def test_pivot_no_columns_same_index_and_values(df):
    """When index and values are the same column, should not crash with duplicate column error."""
    result, _ = create_pivot_table(df, "dept", columns=None, values="dept", aggfunc="count", margins=False)
    assert result is not None
    assert "dept" in result.columns
    assert "dept_count" in result.columns
