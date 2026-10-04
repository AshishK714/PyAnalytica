"""Fixes from the third student-style run (0.10.3).

Each test names the finding it guards. The run's log is in the course folder,
MSTM_F_26/Week_6/HW4_app_test_0.10.3/friction_log.md.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import seaborn as sns

from pyanalytica.ask import describe_one, relate_two
from pyanalytica.visualize.compare import bar_of_means, grouped_boxplot
from pyanalytica.visualize.distribute import bar_chart
from pyanalytica.visualize.relate import scatter


@pytest.fixture(scope="module")
def df():
    rng = np.random.default_rng(4)
    n = 300
    return pd.DataFrame({
        "smoker": rng.choice(["yes", "no", "no", "no"], n),
        "region": rng.choice(["northeast", "northwest", "southeast", "southwest"], n),
        "state": rng.choice([f"State number {i}" for i in range(9)], n),
        "age": rng.integers(18, 65, n),
        "charges": rng.gamma(2, 7000, n),
    })


def _rotation(ax) -> float:
    labels = [t for t in ax.get_xticklabels() if t.get_text()]
    return labels[0].get_rotation() if labels else 0.0


# --- "Another picture" did not say what it held -------------------------------

@pytest.mark.parametrize("make,expected", [
    (lambda d: relate_two(d, "charges", "region"), "Bar chart of means"),
    (lambda d: relate_two(d, "charges", "age"), "Density view (hexbin)"),
    (lambda d: relate_two(d, "smoker", "region"), "Percentages of all rows"),
    (lambda d: describe_one(d, "charges"), "Boxplot"),
    (lambda d: describe_one(d, "smoker"), "Percentages"),
])
def test_the_picture_section_is_named_for_its_chart(df, make, expected):
    r = make(df)
    assert r.picture.title == expected
    labels = [label for label, _ in r.report_cells({"picture"})]
    assert labels[1].endswith(expected.lower())


# --- labels slanted for no reason ---------------------------------------------

def test_few_short_labels_stay_level_many_or_long_ones_slant(df):
    fig, snippet = grouped_boxplot(df, "smoker", "charges")
    assert _rotation(fig.axes[0]) == 0
    assert "rotation=45" not in snippet.code
    plt.close(fig)
    fig, snippet = grouped_boxplot(df, "state", "charges")
    assert _rotation(fig.axes[0]) == 45
    assert "rotation=45" in snippet.code
    plt.close(fig)


def test_count_bars_keep_two_labels_level(df):
    fig, snippet = bar_chart(df, "smoker")
    assert _rotation(fig.axes[0]) == 0
    assert "rot=0" in snippet.code
    plt.close(fig)


# --- the axis of a bar of means said "charges" --------------------------------

def test_bar_of_means_axis_says_mean(df):
    fig, snippet = bar_of_means(df, "region", "charges")
    assert fig.axes[0].get_ylabel() == "mean charges"
    assert 'ax.set_ylabel("mean charges")' in snippet.code
    plt.close(fig)


# --- table alphabetical, bars by count -----------------------------------------

def test_two_category_bars_follow_the_tables_order(df):
    r = relate_two(df, "smoker", "region")
    table_order = r.answer.table["region"].tolist()
    bar_order = [t.get_text() for t in r.answer.figure.axes[0].get_xticklabels()]
    assert bar_order == table_order == sorted(table_order)


# --- the R² legend sat on the highest points ----------------------------------

def test_a_plain_scatters_legend_is_beside_the_plot(df):
    fig, snippet = scatter(df, "age", "charges")
    fig.set_size_inches(8, 4.4)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    ax = fig.axes[0]
    legend = ax.get_legend().get_window_extent(renderer)
    plot = ax.get_window_extent(renderer)
    assert legend.x0 >= plot.x1 - 1
    assert "sns.move_legend(ax" in snippet.code
    ns = {"df": df, "np": np, "pd": pd, "plt": plt, "sns": sns}
    exec(snippet.code.replace("plt.show()", ""), ns)
    plt.close("all")


# --- the empty choice of an optional select was a blank row --------------------

def test_an_optional_selects_empty_choice_is_labelled(monkeypatch):
    from pyanalytica.ui.components import selects

    captured = {}
    monkeypatch.setattr(selects.ui, "update_select",
                        lambda input_id, choices, selected: captured.update(choices=choices, selected=selected))
    monkeypatch.setattr(selects, "_current", lambda input, input_id: "")
    selects.update_choices(object(), "color_by", ["", "smoker", "sex"], allow_none=True)
    assert captured["choices"] == {"": "(none)", "smoker": "smoker", "sex": "sex"}
    assert captured["selected"] == ""
