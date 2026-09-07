"""Binning must survive the trip to the data grid -- issue 1.

pd.cut names its bins with pandas Interval objects. Shiny's serialiser cannot
encode those, and it raises downstream of every module's try/except: no error
reached the student, the session stopped responding, and the reload it took to
recover discarded the dataset and every derived column.
"""

import json

import pandas as pd
import pytest

from pyanalytica.core import display_frame
from pyanalytica.data.transform import add_column_binned


@pytest.fixture
def df():
    return pd.DataFrame({"age": [18, 25, 33, 47, 58, 72, 81, 29, 44, 60]})


def _json_round_trip(frame: pd.DataFrame) -> None:
    """Stand in for the grid's encoder, which is what actually broke."""
    json.dumps(
        {
            "columns": list(frame.columns),
            "data": frame.astype(object).where(frame.notna(), None).values.tolist(),
            "categories": [
                list(map(str, frame[c].cat.categories))
                for c in frame.columns
                if isinstance(frame[c].dtype, pd.CategoricalDtype)
            ],
        }
    )


def test_binned_column_is_serializable(df):
    out, _ = add_column_binned(df, "age_binned", "age", 4)
    _json_round_trip(display_frame(out))


def test_bins_are_named_in_readable_text(df):
    out, _ = add_column_binned(df, "age_binned", "age", 4)
    names = list(out["age_binned"].cat.categories)
    assert len(names) == 4
    assert all(" to " in name for name in names)
    assert not any(name.startswith("(") for name in names)


def test_bins_keep_their_order(df):
    out, _ = add_column_binned(df, "age_binned", "age", 4)
    assert out["age_binned"].cat.ordered
    lows = [float(name.split(" to ")[0]) for name in out["age_binned"].cat.categories]
    assert lows == sorted(lows)


def test_narrow_bins_still_get_distinct_names():
    """Rounding to 1dp would have collapsed these into one name."""
    tight = pd.DataFrame({"x": [0.001, 0.002, 0.003, 0.004, 0.005, 0.006]})
    out, _ = add_column_binned(tight, "b", "x", 4)
    names = list(out["b"].cat.categories)
    assert len(set(names)) == len(names)


def test_shown_code_reproduces_the_column(df):
    out, snippet = add_column_binned(df, "age_binned", "age", 4)
    scope = {"df": df.copy(), "pd": pd}
    exec(snippet.code, scope)  # noqa: S102 - the snippet is what we are testing
    assert list(scope["df"]["age_binned"]) == list(out["age_binned"])


def test_explicit_labels_are_left_alone(df):
    out, _ = add_column_binned(df, "b", "age", 3, labels=["low", "mid", "high"])
    assert list(out["b"].cat.categories) == ["low", "mid", "high"]


def test_grid_coerces_any_unserializable_dtype():
    """The defensive half: no dtype should be able to wedge a session this way."""
    frame = pd.DataFrame(
        {
            "interval": pd.cut(pd.Series([1, 2, 3, 4]), 2),
            "period": pd.period_range("2026-01", periods=4, freq="M"),
            "delta": pd.to_timedelta([1, 2, 3, 4], unit="D"),
            "complex": [1 + 2j, 3 + 4j, 5 + 6j, 7 + 8j],
            "nested": [{"a": 1}, [1, 2], {"b": 2}, [3]],
            "fine": [1.5, 2.5, 3.5, 4.5],
        }
    )
    out = display_frame(frame)
    _json_round_trip(out)
    assert out["fine"].dtype == float  # untouched
