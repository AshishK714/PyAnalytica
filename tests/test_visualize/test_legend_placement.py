"""A colour legend sits beside the plot, never over its data.

From a student-style run: on screen the legend of a grouped bar chart lay on
a bar, hiding a swatch of the same colour, and legends covered boxes and
error bars. The figure-level charts were the worst case, because the layout
engine the panels use to keep titles on the canvas ignores figure legends.
Measured at the shape the screen renders, as test_facet_layout does.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from pyanalytica.visualize.compare import bar_of_means, grouped_boxplot
from pyanalytica.visualize.distribute import bar_chart, histogram
from pyanalytica.visualize.relate import scatter

#: Screen shapes: a panel's main chart and a disclosed one.
SHAPES = [(8.0, 4.4), (10.42, 5.20)]


@pytest.fixture(scope="module")
def df():
    rng = np.random.default_rng(2)
    n = 400
    return pd.DataFrame({
        "sex": rng.choice(["female", "male"], n),
        "smoker": rng.choice(["yes", "no", "no", "no"], n),
        "region": rng.choice(["northeast", "northwest", "southeast", "southwest"], n),
        "age": rng.integers(18, 65, n),
        "charges": rng.gamma(2, 7000, n),
    })


def _charts(df):
    return {
        "count bars split by colour": lambda: bar_chart(df, "sex", group_by="smoker")[0],
        "count bars split and faceted": lambda: bar_chart(df, "region", group_by="smoker", facet_col="sex")[0],
        "grouped histogram": lambda: histogram(df, "charges", group_by="smoker")[0],
        "boxplot with hue": lambda: grouped_boxplot(df, "region", "charges", hue="smoker")[0],
        "bar of means with hue": lambda: bar_of_means(df, "region", "charges", hue="smoker")[0],
        "scatter with hue": lambda: scatter(df, "age", "charges", color_by="smoker")[0],
        "scatter with hue and facets": lambda: scatter(df, "age", "charges", color_by="smoker", facet_col="sex")[0],
    }


def _legends(fig):
    found = list(fig.legends)
    for ax in fig.axes:
        found += [a for a in ax.get_children() if isinstance(a, matplotlib.legend.Legend)]
    return found


@pytest.mark.parametrize("shape", SHAPES, ids=lambda s: f"{s[0]}x{s[1]}")
@pytest.mark.parametrize("name", list(_charts(pd.DataFrame()).keys()))
def test_the_colour_legend_is_beside_the_plot_not_on_it(df, name, shape):
    fig = _charts(df)[name]()
    try:
        fig.set_size_inches(*shape)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        colour_legends = [lg for lg in _legends(fig) if lg.get_title().get_text()]
        assert colour_legends, f"{name}: no titled colour legend found"
        for legend in colour_legends:
            box = legend.get_window_extent(renderer)
            assert box.x1 <= fig.bbox.x1 + 1, f"{name}: legend runs off the canvas"
            for ax in fig.axes:
                plot = ax.get_window_extent(renderer)
                overlap_x = min(box.x1, plot.x1) - max(box.x0, plot.x0)
                overlap_y = min(box.y1, plot.y1) - max(box.y0, plot.y0)
                assert overlap_x <= 1 or overlap_y <= 1, (
                    f"{name} at {shape}: the legend covers a plotting area"
                )
    finally:
        plt.close(fig)


def test_shown_code_for_an_axes_chart_moves_the_legend_too(df):
    _, snippet = grouped_boxplot(df, "region", "charges", hue="smoker")
    assert "sns.move_legend(ax" in snippet.code
    _, snippet = grouped_boxplot(df, "region", "charges")
    assert "move_legend" not in snippet.code


def test_two_groups_get_two_clearly_different_colours():
    """Blue then violet blended where bars overlapped; blue then orange does not."""
    import seaborn as sns
    from matplotlib.colors import to_rgb

    from pyanalytica.core.theme import DEFAULT_THEME, apply_theme

    apply_theme(DEFAULT_THEME)
    first, second = (to_rgb(c) for c in sns.color_palette(n_colors=2))
    distance = sum((a - b) ** 2 for a, b in zip(first, second)) ** 0.5
    assert distance > 0.8, f"first two colours too close: {first} {second}"
