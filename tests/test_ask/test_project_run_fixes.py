"""Findings from a student-style run of a conference-report project on 0.10.5.

One test per finding. The run used a 5,000-row programme dataset with a
yes/no outcome, a salary recorded only for the employed, and a score whose
histogram has two humps; the fixtures below rebuild those shapes.
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import seaborn as sns
from scipy import stats

from pyanalytica.analyze.means import two_sample_ttest
from pyanalytica.analyze.proportions import two_proportion_ztest
from pyanalytica.ask import describe_one, relate_two
from pyanalytica.ask.one import find_peaks
from pyanalytica.explore.crosstab import create_crosstab
from pyanalytica.explore.pivot import label_columns
from pyanalytica.visualize.compare import rate_chart


@pytest.fixture(scope="module")
def df():
    rng = np.random.default_rng(11)
    n = 2000
    mentored = rng.choice(["Yes", "No"], n, p=[0.85, 0.15])
    employed = np.where(rng.random(n) < np.where(mentored == "Yes", 0.4, 0.3), "Yes", "No")
    salary = np.where(employed == "Yes", rng.normal(60000, 15000, n), np.nan)
    score = np.r_[rng.normal(60, 3, 1400), rng.normal(85, 4, 600)]
    return pd.DataFrame({
        "mentorship": mentored,
        "employed": employed,
        "education": rng.choice(["High School", "Bachelors", "Masters"], n),
        "track": rng.choice(["AI", "Hybrid", "Traditional"], n),
        "salary": salary,
        "score": rng.permutation(score),
        # unequal spreads, so Levene's test picks Welch's t-test
        "ratio": np.where(mentored == "Yes", rng.normal(40, 2, n), rng.normal(41, 8, n)),
    })


def _run(code: str, df: pd.DataFrame) -> dict:
    ns = {"df": df.copy(), "pd": pd, "np": np, "plt": plt, "sns": sns, "stats": stats}
    exec(code.replace("plt.show()", ""), ns)
    plt.close("all")
    return ns


# F1: a yes/no outcome by group was charted as counts, hiding the rate.
def test_two_category_answer_charts_the_rate_with_group_sizes(df):
    r = relate_two(df, "employed", "mentorship")
    ax = r.answer.figure.axes[0]
    assert ax.get_ylabel() == "% with employed = Yes"
    labels = [t.get_text() for t in ax.texts]
    assert any("n=" in t and "%" in t for t in labels), labels
    heights = sorted(round(b.get_height(), 1) for b in ax.patches)
    rates = r.answer.table["employed = Yes (% of row)"].tolist()
    assert heights == sorted(rates)
    _run(r.answer.code.code, df)
    plt.close("all")


def test_more_than_two_outcomes_get_stacked_bars_that_run(df):
    fig, snippet = rate_chart(df, "track", "education", hue="mentorship")
    assert "stacked=True" in snippet.code
    assert "(n=" in fig.axes[0].get_xticklabels()[0].get_text()
    _run(snippet.code, df)


def test_the_counts_are_the_second_picture(df):
    r = relate_two(df, "employed", "mentorship")
    assert r.picture.title == "Counts"


# F2: percentages without group sizes.
def test_two_category_table_gives_each_group_its_size(df):
    r = relate_two(df, "employed", "education", color_by="mentorship")
    table = r.answer.table
    assert "n" in table.columns
    expected = df.groupby(["mentorship", "education"]).size()
    for _, row in table.iterrows():
        assert row["n"] == expected[(row["mentorship"], row["education"])]


# F3: salary means did not say they cover only rows with a salary.
def test_two_variable_sentence_says_how_many_rows_were_left_out(df):
    r = relate_two(df, "salary", "track")
    used = int(df["salary"].notna().sum())
    assert f"{used:,} of {len(df):,} rows" in r.answer.sentence
    assert "salary blank" in r.answer.sentence
    full = relate_two(df, "ratio", "track")
    assert "left out" not in full.answer.sentence


# F4: a two-humped column was called "roughly symmetric".
def test_two_peaks_are_named_not_called_symmetric(df):
    sentence = describe_one(df, "score").answer.sentence
    assert "2 separate peaks" in sentence
    assert "symmetric" not in sentence
    assert len(find_peaks(df["score"])) == 2
    one_hump = pd.DataFrame({"v": np.random.default_rng(2).normal(50, 10, 1000)})
    assert "roughly symmetric" in describe_one(one_hump, "v").answer.sentence


def test_a_skewed_column_says_skewed(df):
    skewed = pd.DataFrame({"v": np.random.default_rng(3).gamma(2, 5, 1000)})
    sentence = describe_one(skewed, "v").answer.sentence
    assert "tail of high values" in sentence and "peaks" not in sentence


# F5: Welch's t-test printed the pooled df, n1 + n2 - 2.
def test_welch_reports_welch_degrees_of_freedom(df):
    r = two_sample_ttest(df, "ratio", "mentorship")
    assert "Welch" in r.test_name
    g = [df.loc[df["mentorship"] == k, "ratio"] for k in ("No", "Yes")]
    v1, v2 = g[0].var() / len(g[0]), g[1].var() / len(g[1])
    welch_df = (v1 + v2) ** 2 / (v1 ** 2 / (len(g[0]) - 1) + v2 ** 2 / (len(g[1]) - 1))
    assert f"t({welch_df:.1f})" in r.interpretation
    assert f"t({len(df) - 2})" not in r.interpretation
    _run(r.code.code, df)


# F6: the difference of two proportions did not say which minus which.
def test_proportion_difference_names_its_order(df):
    r = two_proportion_ztest(df, "employed", "Yes", "mentorship")
    assert "Difference (No minus Yes)" in r.interpretation
    assert "For Yes minus No" in r.interpretation


# F8: the cross-tab sentence printed a Python list, and headers lacked the variable.
def test_crosstab_sentence_uses_plain_names(df):
    r = create_crosstab(df, ["mentorship"], "employed")
    assert "['" not in r.interpretation
    assert "between mentorship and employed" in r.interpretation


def test_crosstab_headers_name_the_column_variable(df):
    r = create_crosstab(df, ["mentorship"], "employed", margins=True)
    table, snippet = label_columns(r.table, "employed", r.code, name="ct")
    assert list(table.columns) == ["employed = No", "employed = Yes", "All"]
    ns = _run(snippet.code, df)
    assert list(ns["ct"].columns) == list(table.columns)


def test_two_variable_test_table_names_the_outcome(df):
    r = relate_two(df, "employed", "mentorship")
    assert "employed = Yes" in r.test.table.columns


# F10: Profile told a student to select a dataset while showing one, and gave
# missing values only as a percentage.
def test_profile_panel_text_and_missing_counts():
    from pathlib import Path
    import pyanalytica.ui.modules.data.mod_profile as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "Select a dataset to see its profile" not in source
    assert "active dataset" in source
    assert '"Missing"' in source
