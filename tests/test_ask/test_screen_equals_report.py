"""The table a report cell shows is the table the screen showed.

A retest of a nine-question assignment found the report's tables differing
from the screen's on the same numbers: "index" where the screen said
"statistic", "r_squared" where it said "r squared", a missing "all" row. Each
came from the screen's table and the shown code being written separately.
This runs every rung's shown code the way Report Builder does and compares
the ``result`` it leaves with the rung's on-screen table, for every kind of
question the guided panels answer.
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import seaborn as sns
from scipy import stats

from pyanalytica.ask import describe_one, relate_two


@pytest.fixture(scope="module")
def df():
    rng = np.random.default_rng(5)
    n = 300
    smoker = rng.choice(["yes", "no", "no", "no"], n)
    return pd.DataFrame({
        "age": rng.integers(18, 65, n),
        "bmi": rng.normal(30, 6, n).round(2),
        "smoker": smoker,
        "sex": rng.choice(["female", "male"], n),
        "region": rng.choice(["ne", "nw", "se", "sw"], n),
        "charges": rng.gamma(2, 6000, n) + np.where(smoker == "yes", 20000, 0),
    })


def _normalise(frame: pd.DataFrame) -> pd.DataFrame:
    """What Report Builder renders: a grouping index becomes a column."""
    out = frame.copy()
    if not isinstance(out.index, pd.RangeIndex):
        out = out.reset_index()
    out.columns = [str(c) for c in out.columns]
    return out.reset_index(drop=True)


def _result_of(code: str, df: pd.DataFrame) -> pd.DataFrame:
    ns = {"df": df.copy(), "pd": pd, "np": np, "plt": plt, "sns": sns, "stats": stats}
    exec(code.replace("plt.show()", ""), ns)
    plt.close("all")
    return ns["result"]


def _assert_same(screen: pd.DataFrame, report: pd.DataFrame) -> None:
    screen, report = _normalise(screen), _normalise(report)
    assert screen.columns.tolist() == report.columns.tolist()
    assert len(screen) == len(report)
    for col in screen.columns:
        a, b = screen[col], report[col]
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            assert np.allclose(a.astype(float), b.astype(float), atol=1e-3, equal_nan=True), col
        else:
            assert a.astype(str).tolist() == b.astype(str).tolist(), col


CASES = [
    ("one", ("charges",), {}),
    ("one", ("smoker",), {}),
    ("two", ("charges", "region"), {}),
    ("two", ("charges", "region"), {"color_by": "smoker"}),
    ("two", ("charges", "age"), {}),
    ("two", ("charges", "age"), {"color_by": "smoker"}),
    ("two", ("smoker", "region"), {}),
    ("two", ("smoker", "region"), {"color_by": "sex"}),
]


@pytest.mark.parametrize("kind,cols,kw", CASES, ids=lambda v: str(v))
def test_answer_and_model_tables_match_the_screen(df, kind, cols, kw):
    r = describe_one(df, *cols, **kw) if kind == "one" else relate_two(df, *cols, **kw)
    for rung in (r.answer, r.model):
        if rung is None or rung.table is None or rung.code is None:
            continue
        _assert_same(rung.table, _result_of(rung.code.code, df))


def test_one_variable_names_the_median(df):
    table = describe_one(df, "charges").answer.table
    assert "50% (median)" in table["statistic"].tolist()


def test_histogram_code_puts_the_values_in_the_legend(df):
    code = describe_one(df, "charges").answer.code.code
    _result_of(code, df)  # runs
    assert 'label=f"Mean: {mean_val:.2f}"' in code


def test_the_overlaid_histogram_is_pointed_to_on_the_answer(df):
    r = relate_two(df, "charges", "smoker")
    assert any("Distribution Plots" in n for n in r.answer.notes)
