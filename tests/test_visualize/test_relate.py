"""Tests for visualize/relate.py."""

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from pyanalytica.visualize.relate import hexbin, scatter


@pytest.fixture
def df():
    np.random.seed(42)
    return pd.DataFrame({
        "x": np.random.randn(100),
        "y": np.random.randn(100),
        "cat": np.random.choice(["A", "B"], 100),
    })


def test_scatter(df):
    fig, snippet = scatter(df, "x", "y")
    assert fig is not None
    assert "scatterplot" in snippet.code


def test_scatter_no_trend(df):
    fig, snippet = scatter(df, "x", "y", trend_line=False)
    assert fig is not None


def test_scatter_same_variable(df):
    """x == y should not crash (linregress on identical data)."""
    fig, snippet = scatter(df, "x", "x")
    assert fig is not None


def test_scatter_style_by(df):
    fig, snippet = scatter(df, "x", "y", style_by="cat")
    assert fig is not None
    assert 'style="cat"' in snippet.code


def test_scatter_facet_col(df):
    fig, snippet = scatter(df, "x", "y", facet_col="cat")
    assert fig is not None
    assert "relplot" in snippet.code


def _dashed_lines(ax):
    """The fitted lines: dashed Line2D artists with 100 points."""
    return [l for l in ax.get_lines() if l.get_linestyle() == "--" and len(l.get_xdata()) == 100]


def _run(snippet, df):
    import matplotlib.pyplot as plt
    import seaborn as sns
    ns = {"df": df, "np": np, "pd": pd, "plt": plt, "sns": sns}
    exec(snippet.code.replace("plt.show()", ""), ns)
    plt.close("all")


def test_plain_scatter_has_one_trend_line(df):
    fig, snippet = scatter(df, "x", "y")
    assert len(_dashed_lines(fig.axes[0])) == 1
    _run(snippet, df)


def test_color_by_draws_one_trend_line_per_group(df):
    """With Color By there used to be a single line through every group,
    which cannot show whether the pattern holds within each."""
    fig, snippet = scatter(df, "x", "y", color_by="cat")
    assert len(_dashed_lines(fig.axes[0])) == 2
    labels = [l.get_label() for l in _dashed_lines(fig.axes[0])]
    assert any(lbl.startswith("A") for lbl in labels)
    assert "hue_order" in snippet.code
    _run(snippet, df)


def test_rerun_code_draws_each_line_in_its_groups_colour(df):
    """The report re-runs the shown code. It drew the points in seaborn's
    order and the lines in groupby's, so the "B" line came out in "A"'s
    colour. Each line must match its own points, and say its R²."""
    import matplotlib.pyplot as plt
    import seaborn as sns
    from matplotlib.colors import to_hex

    # Appearance order (B first) differs from sorted order (A first): the case
    # that swapped the colours.
    df = pd.concat([df[df["cat"] == "B"], df[df["cat"] == "A"]], ignore_index=True)
    _, snippet = scatter(df, "x", "y", color_by="cat")
    ns = {"df": df, "np": np, "pd": pd, "plt": plt, "sns": sns}
    exec(snippet.code.replace("plt.show()", ""), ns)
    ax = plt.gcf().axes[0]
    points = ax.collections[0]
    point_colours = {to_hex(c) for c in points.get_facecolors()}
    lines = {l.get_label().split(":")[0]: to_hex(l.get_color()) for l in _dashed_lines(ax)}
    assert set(lines) == {"A", "B"}
    assert all("R²" in l.get_label() for l in _dashed_lines(ax))
    colors = ns["colors"]
    for level, colour in lines.items():
        assert colour == to_hex(colors[level])
        assert colour in point_colours
    plt.close("all")


def test_colour_name_is_in_the_title(df):
    fig, snippet = scatter(df, "x", "y", color_by="cat")
    assert fig.axes[0].get_title() == "y vs x by cat"
    assert 'ax.set_title("y vs x by cat")' in snippet.code


def test_facets_draw_a_trend_line_in_every_panel(df):
    """The faceted branch never drew a line at all."""
    fig, snippet = scatter(df, "x", "y", facet_col="cat")
    panels = [ax for ax in fig.axes if ax.collections]
    assert len(panels) == 2
    for ax in panels:
        assert len(_dashed_lines(ax)) == 1
    assert "facet_data()" in snippet.code
    _run(snippet, df)


def test_facets_with_color_by_draw_a_line_per_group_per_panel(df):
    df = df.assign(grp=np.random.choice(["p", "q"], len(df)))
    fig, snippet = scatter(df, "x", "y", color_by="cat", facet_col="grp")
    panels = [ax for ax in fig.axes if ax.collections]
    for ax in panels:
        assert len(_dashed_lines(ax)) == 2
    _run(snippet, df)


def test_trend_off_draws_no_lines_anywhere(df):
    fig, _ = scatter(df, "x", "y", color_by="cat", facet_col="cat", trend_line=False)
    assert all(not _dashed_lines(ax) for ax in fig.axes)


def test_hexbin(df):
    fig, snippet = hexbin(df, "x", "y")
    assert fig is not None
    assert "hexbin" in snippet.code
