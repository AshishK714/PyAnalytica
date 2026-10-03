"""Relate > Two Variables: the column types pick the analysis, and the shown
code draws what the panel drew."""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import seaborn as sns
from scipy import stats

from pyanalytica.ask import relate_two, resolve_kind


@pytest.fixture
def df():
    rng = np.random.default_rng(7)
    n = 300
    group = rng.choice(["Public", "Private"], n)
    phd = rng.uniform(20, 100, n)
    tuition = np.where(group == "Private", 12000, 2500) + 60 * phd + rng.normal(0, 1500, n)
    return pd.DataFrame({
        "type": group,
        "code": np.where(group == "Private", 2, 1),          # 1/2 integer: a category
        "state": rng.choice(["CA", "NY", "TX"], n),
        "phd_faculty": phd,
        "tuition": tuition,
        "student_id": np.arange(n),
        "name": [f"College {i}" for i in range(n)],
        "when": pd.date_range("2020-01-01", periods=n, freq="D"),
        "grad_rate": rng.choice([0, 1], n),
    })


def _run(code: str, df: pd.DataFrame) -> dict:
    """Execute shown code the way Report Builder does."""
    ns = {"df": df.copy(), "pd": pd, "np": np, "plt": plt, "sns": sns, "stats": stats}
    exec(code.replace("plt.show()", ""), ns)
    plt.close("all")
    return ns


# --- dispatch ---------------------------------------------------------------

def test_number_by_category(df):
    r = relate_two(df, "tuition", "type")
    assert r.kind == "number_by_category"
    assert "highest for type = Private" in r.answer.sentence
    assert "t-test" in r.test.sentence
    assert r.model.table is not None and "intercept" in r.model.table["term"].tolist()
    assert r.answer.figure is not None


def test_three_groups_use_anova(df):
    r = relate_two(df, "tuition", "state")
    assert "ANOVA" in r.test.sentence


def test_number_by_number(df):
    r = relate_two(df, "tuition", "phd_faculty")
    assert r.kind == "number_by_number"
    assert "r = " in r.answer.sentence
    assert "Pearson" in r.test.sentence
    assert r.model.table["term"].tolist() == ["intercept", "phd_faculty"]


def test_category_by_category(df):
    r = relate_two(df, "type", "state")
    assert r.kind == "category_by_category"
    assert "ranges from" in r.answer.sentence
    assert "association" in r.test.sentence
    assert r.model.table is None  # a pointer, not a fit


def test_category_y_by_number_x_is_swapped_and_says_so(df):
    r = relate_two(df, "type", "tuition")
    assert r.kind == "number_by_category"
    assert "the other way round" in r.reading
    assert "Model > Classify" in r.model.sentence


# --- treat as ---------------------------------------------------------------

def test_small_integer_column_is_read_as_category_and_the_reading_says_so(df):
    r = relate_two(df, "tuition", "code")
    assert r.kind == "number_by_category"
    assert "read as categories" in r.reading
    assert "Treat X as" in r.reading


def test_treat_as_number_overrides_the_auto_reading(df):
    r = relate_two(df, "tuition", "code", treat_x="number")
    assert r.kind == "number_by_number"
    assert "as you asked" in r.reading


def test_treat_text_as_number_is_refused_with_a_sentence(df):
    with pytest.raises(ValueError, match="holds text"):
        relate_two(df, "tuition", "type", treat_x="number")


def test_resolve_kind_refuses_dates_ids_and_free_text(df):
    with pytest.raises(ValueError, match="Timeline"):
        resolve_kind(df["when"])
    with pytest.raises(ValueError, match="identifier"):
        resolve_kind(df["student_id"])
    with pytest.raises(ValueError, match="free text"):
        resolve_kind(df["name"])


def test_same_column_twice_is_refused(df):
    with pytest.raises(ValueError, match="two different columns"):
        relate_two(df, "tuition", "tuition")


# --- figures are built only when asked ------------------------------------

def test_second_picture_is_drawn_only_when_its_section_is_open(df):
    closed = relate_two(df, "tuition", "type")
    assert closed.picture.figure is None
    assert closed.picture.code is not None and closed.picture.code.code
    opened = relate_two(df, "tuition", "type", second_picture=True)
    assert opened.picture.figure is not None


# --- the shown code runs ----------------------------------------------------

@pytest.mark.parametrize("y,x", [
    ("tuition", "type"), ("tuition", "state"), ("tuition", "phd_faculty"), ("type", "state"),
])
def test_combined_code_runs_and_ends_with_the_model_table(df, y, x):
    r = relate_two(df, y, x, second_picture=True)
    ns = _run(r.code.code, df)
    assert "result" in ns
    assert isinstance(ns["result"], pd.DataFrame)
    assert "# --- Describe ---" in r.code.code


# --- colour by: the context variable ---------------------------------------

def test_colour_by_splits_the_group_table_and_names_the_cell(df):
    r = relate_two(df, "tuition", "state", color_by="type")
    assert set(["state", "type"]).issubset(r.answer.table.columns)
    assert "state / type = " in r.answer.sentence
    assert "split by type" in r.description
    assert any("not in it" in n for n in r.test.notes)


def test_colour_by_on_a_scatter_gives_r_within_each_group(df):
    r = relate_two(df, "tuition", "phd_faculty", color_by="type", second_picture=True)
    assert r.answer.table["type"].tolist()[-1] == "all"
    assert set(r.answer.table["type"]) >= {"Private", "Public"}
    assert "Within each type group" in r.answer.sentence
    assert 'hue="type"' in r.code.code
    _run(r.code.code, df)


def test_colour_by_on_two_categories_nests_the_table(df):
    r = relate_two(df, "type", "state", color_by="grad_rate", second_picture=True)
    assert r.answer.table.columns[0] == "grad_rate"
    assert 'col="grad_rate"' in r.answer.code.code
    _run(r.code.code, df)


def test_colour_by_must_be_a_third_categorical_column(df):
    with pytest.raises(ValueError, match="already Y or X"):
        relate_two(df, "tuition", "type", color_by="type")
    with pytest.raises(ValueError, match="cannot colour"):
        relate_two(df, "tuition", "type", color_by="phd_faculty")


def test_model_coefficients_equal_the_group_mean_differences(df):
    r = relate_two(df, "tuition", "type")
    means = df.groupby("type")["tuition"].mean()
    coef = dict(zip(r.model.table["term"], r.model.table["coefficient"]))
    assert coef["intercept"] == pytest.approx(means["Private"], abs=0.01)
    assert coef["Public"] == pytest.approx(means["Public"] - means["Private"], abs=0.01)
