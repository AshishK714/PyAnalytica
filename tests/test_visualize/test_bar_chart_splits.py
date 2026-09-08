"""Bar charts must honour Group By and the facet controls -- issue 9.

The panel showed all three, they accepted values, and `bar_chart()` did not
take the arguments at all: the call site dropped them. A student splitting a
bar chart by a second variable got the same picture back with nothing to say
why, which is indistinguishable from "these two variables look the same".

The assertions compare against the *ungrouped* figure rather than checking that
a figure exists, because a chart that ignored its controls would pass the
second kind of test.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from pyanalytica.data.load import load_bundled
from pyanalytica.visualize.distribute import bar_chart


@pytest.fixture(scope="module")
def df():
    frame, _ = load_bundled("titanic")
    return frame


def _has_legend(fig) -> bool:
    return bool(fig.legends or [ax for ax in fig.axes if ax.get_legend()])


def test_a_plain_bar_chart_is_one_panel_with_no_legend(df):
    fig, _ = bar_chart(df, "Pclass")
    assert len(fig.axes) == 1
    assert not _has_legend(fig)
    plt.close(fig)


def test_group_by_actually_splits_the_bars(df):
    plain, _ = bar_chart(df, "Pclass")
    grouped, _ = bar_chart(df, "Pclass", group_by="Sex")
    assert _has_legend(grouped), "grouping produced no legend, so nothing was split"
    assert not _has_legend(plain)
    plt.close(plain)
    plt.close(grouped)


def test_a_column_facet_produces_one_panel_per_level(df):
    fig, _ = bar_chart(df, "Pclass", facet_col="Survived")
    # Two levels of Survived, so two panels.
    assert len([ax for ax in fig.axes if ax.has_data()]) == 2
    plt.close(fig)


def test_both_facets_produce_a_grid(df):
    fig, _ = bar_chart(df, "Pclass", facet_col="Survived", facet_row="Sex")
    panels = [ax for ax in fig.axes if ax.has_data()]
    assert len(panels) == 4, f"expected a 2x2 grid, got {len(panels)} panels"
    plt.close(fig)


def test_grouping_and_faceting_together(df):
    fig, _ = bar_chart(df, "Pclass", group_by="Sex", facet_col="Survived")
    assert len([ax for ax in fig.axes if ax.has_data()]) == 2
    assert _has_legend(fig)
    plt.close(fig)


def test_facetted_percentages_are_of_all_rows_and_say_so(df):
    """seaborn normalises over the whole dataset, so the panels total 100
    between them rather than 100 each. That is the more useful reading when
    comparing panels, and it is not what "percentage" alone suggests -- so the
    title has to carry it."""
    fig, _ = bar_chart(df, "Pclass", facet_col="Survived", pct=True)
    panels = [ax for ax in fig.axes if ax.has_data()]
    across = sum(bar.get_height() for ax in panels for bar in ax.patches)
    assert 99.0 <= across <= 101.0, f"the panels total {across:.1f}% between them"
    assert any(
        total < 99.0 for total in
        (sum(bar.get_height() for bar in ax.patches) for ax in panels)
    ), "if every panel totalled 100 this test would be describing the wrong thing"
    assert "all rows" in fig._suptitle.get_text()
    plt.close(fig)


def test_horizontal_orientation_survives_grouping(df):
    fig, _ = bar_chart(df, "Pclass", orientation="horizontal", group_by="Sex")
    assert _has_legend(fig)
    plt.close(fig)


def test_the_shown_code_matches_what_was_drawn(df):
    _, snippet = bar_chart(df, "Pclass", group_by="Sex", facet_col="Survived")
    code = snippet.code
    assert "catplot" in code
    assert 'hue="Sex"' in code
    assert 'col="Survived"' in code
    assert "import seaborn as sns" in snippet.imports


def test_an_unknown_column_is_ignored_rather_than_crashing(df):
    """The panel can hold a stale selection after the dataset changes."""
    fig, _ = bar_chart(df, "Pclass", group_by="not_a_column")
    assert len(fig.axes) == 1
    plt.close(fig)
