"""Binning at the cut points a reader means, not at equal widths.

Most bands people care about are defined by thresholds, not by dividing the
range evenly: a clinical cut-off, an age band, a price tier. The Transform
panel offered only a number of equal-width bins, so a threshold at 30 on a
column running 16 to 53 landed at 34.5. The library accepted a list of edges
all along; the panel did not ask for one.
"""

import numpy as np
import pandas as pd
import pytest

from pyanalytica.data.transform import add_column_binned, cut_points


@pytest.fixture
def df():
    return pd.DataFrame({
        "bmi": [15.96, 29.99, 30.0, 34.5, 53.13],
        "age": [18, 34, 35, 49, 64],
    })


def test_one_cut_point_gives_under_and_at_or_above(df):
    edges = cut_points("30", df["bmi"].min(), df["bmi"].max())
    assert edges == [-np.inf, 30.0, np.inf]
    out, snippet = add_column_binned(df, "bmi_group", "bmi", edges, right=False)
    assert out["bmi_group"].astype(str).tolist() == [
        "under 30", "under 30", "30 and above", "30 and above", "30 and above",
    ]
    assert "right=False" in snippet.code
    assert "np.inf" in snippet.code and "import numpy as np" in snippet.imports


def test_band_starts_give_the_bands_a_reader_means(df):
    edges = cut_points("18, 35, 50, 65", df["age"].min(), df["age"].max())
    assert edges == [18.0, 35.0, 50.0, 65.0]
    out, _ = add_column_binned(df, "age_group", "age", edges, right=False)
    assert out["age_group"].astype(str).tolist() == [
        "18 to under 35", "18 to under 35", "35 to under 50", "35 to under 50", "50 to under 65",
    ]
    assert out["age_group"].isna().sum() == 0


def test_the_top_value_is_never_lost(df):
    """pd.cut with right=False excludes the last edge; padding with inf keeps it."""
    edges = cut_points("18, 35, 50", df["age"].min(), df["age"].max())
    out, _ = add_column_binned(df, "g", "age", edges, right=False)
    assert out["g"].isna().sum() == 0
    assert str(out["g"].iloc[-1]) == "50 and above"


def test_labels_replace_the_generated_names(df):
    edges = cut_points("30", 15.0, 55.0)
    out, _ = add_column_binned(df, "g", "bmi", edges, ["lean", "obese"], right=False)
    assert set(out["g"].astype(str)) == {"lean", "obese"}


def test_the_shown_code_reproduces_the_column(df):
    edges = cut_points("30", 15.0, 55.0)
    out, snippet = add_column_binned(df, "g", "bmi", edges, right=False)
    ns = {"df": df.copy(), "pd": pd, "np": np}
    exec(snippet.code, ns)
    assert ns["df"]["g"].astype(str).tolist() == out["g"].astype(str).tolist()


def test_bad_text_is_refused_with_a_sentence():
    with pytest.raises(ValueError, match="numbers separated by commas"):
        cut_points("thirty", 0, 100)
    with pytest.raises(ValueError, match="at least one"):
        cut_points(" , ", 0, 100)
    with pytest.raises(ValueError, match="different"):
        cut_points("30, 30", 0, 100)


def test_equal_width_bins_are_unchanged(df):
    out, snippet = add_column_binned(df, "g", "age", 2)
    assert out["g"].nunique() == 2
    assert "right=False" not in snippet.code
