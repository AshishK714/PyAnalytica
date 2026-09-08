"""Titles must survive the resize the browser performs.

Figures are built at 8x5 inches. Shiny re-renders them at whatever the panel
gives them -- 1042x350 measured in the live app, an aspect three times wider
than they were drawn for. `tight_layout()` is a one-shot call that freezes the
margins as *fractions* computed for the original height, so at a third of the
height the strip above the axes is too small for the title and it clips. That is
what the user saw: "Residuals vs Fitted" cut in half lengthways.

A layout engine recomputes on every draw, so it re-fits after the resize. These
tests do what the browser does -- resize, draw, then measure where the title
actually landed -- because the failure is a rendering result, not a property of
the code.

They assert *headroom*, not a binary fit, because the one-shot version does not
clip everywhere. Measured on this machine it left 4.1px above the title in the
old 350px box against the engine's 15px, and 4px is inside the range a different
font, DPI or device pixel ratio moves it by -- which is why the same build
clipped on the reporter's screen and not in the test suite. Requiring real
headroom is the difference the fix actually makes.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
import pytest

from pyanalytica.data.load import load_bundled

#: What the panel gives a plot: full width, and the disclosed height.
BROWSER_SHAPE = (10.42, 5.20)
#: The shape that used to clip, kept as the harder case.
LETTERBOX_SHAPE = (10.42, 3.50)

#: Pixels that must remain above the title after a resize. A one-shot
#: tight_layout leaves ~4px here, which is inside the margin that fonts and
#: device pixel ratios move things by.
MIN_HEADROOM_PX = 8.0


@pytest.fixture(scope="module")
def titanic():
    df, _ = load_bundled("titanic")
    return df.dropna(subset=["Age"])


def _title_headroom(fig, shape) -> float:
    """Resize, draw, and measure the space left above the highest title."""
    fig.set_size_inches(*shape)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    top = fig.bbox.y1

    highest = 0.0
    for ax in fig.axes:
        if ax.get_title():
            highest = max(highest, ax.title.get_window_extent(renderer).y1)
    if fig._suptitle is not None:
        highest = max(highest, fig._suptitle.get_window_extent(renderer).y1)
    return top - highest if highest else float("inf")


def _figures(titanic):
    """One figure from each function that builds one, with a title."""
    from pyanalytica.model.regression import linear_regression
    from pyanalytica.model.cluster import kmeans_cluster
    from pyanalytica.model.reduce import pca_analysis
    from pyanalytica.visualize.timeline import time_series

    reg = linear_regression(titanic, "Age", ["Fare", "Pclass"], test_size=0.3)
    km = kmeans_cluster(titanic, ["Age", "Fare"], chosen_k=3)
    pca = pca_analysis(titanic, ["Age", "Fare", "Pclass"])
    dates = pd.DataFrame({
        "when": pd.date_range("2026-01-01", periods=40, freq="D"),
        "value": np.arange(40, dtype=float),
    })
    line, _ = time_series(dates, "when", "value")
    years = pd.DataFrame({"year": [2019, 2020, 2021, 2022, 2023], "v": [1, 2, 3, 4, 5]})
    noted, _ = time_series(years, "year", "v")

    return {
        "regression residuals": reg.residual_plot,
        "regression Q-Q": reg.qq_plot,
        "cluster elbow": km.elbow_plot,
        "PCA scree": pca.scree_plot,
        "timeline": line,
        "timeline with a note": noted,
    }


@pytest.fixture(scope="module")
def figures(titanic):
    return _figures(titanic)


@pytest.mark.parametrize("shape,label", [
    (BROWSER_SHAPE, "as a disclosed plot is rendered"),
    (LETTERBOX_SHAPE, "in the old letterbox, the harder case"),
])
def test_titles_keep_their_headroom_after_the_browser_resizes_the_figure(
    figures, shape, label
):
    cramped = []
    for name, fig in figures.items():
        if fig is None:
            continue
        headroom = _title_headroom(fig, shape)
        if headroom < MIN_HEADROOM_PX:
            cramped.append(f"{name}: only {headroom:.1f}px above the title")
    assert not cramped, (
        f"titles had less than {MIN_HEADROOM_PX:.0f}px of headroom when the "
        f"figure was resized {label} -- that is the margin in which they clip "
        f"on one machine and not another:\n  " + "\n  ".join(cramped)
    )


def test_the_figures_carry_a_layout_engine(figures):
    """The property that makes the resize safe, asserted directly.

    A one-shot tight_layout() leaves no engine behind, so this is the
    difference between the two.
    """
    without = [name for name, fig in figures.items()
               if fig is not None and fig.get_layout_engine() is None]
    assert not without, f"these figures have no layout engine: {without}"


def test_the_timeline_note_is_not_swallowed(titanic):
    """The note says the years were read as calendar years; it has to be legible.

    It used to be placed with subplots_adjust and a figure-coordinate text box.
    A layout engine overrides subplots_adjust, so that placement would end up
    under the axis after a resize.
    """
    from pyanalytica.visualize.timeline import time_series

    years = pd.DataFrame({"year": [2019, 2020, 2021, 2022, 2023], "v": [1, 2, 3, 4, 5]})
    fig, _ = time_series(years, "year", "v")
    fig.set_size_inches(*BROWSER_SHAPE)
    fig.canvas.draw()

    assert fig._supxlabel is not None, "the note is gone"
    assert "calendar years" in fig._supxlabel.get_text()

    renderer = fig.canvas.get_renderer()
    note = fig._supxlabel.get_window_extent(renderer)
    axis = fig.axes[0].get_window_extent(renderer)
    assert note.y1 <= axis.y0 + 1, "the note overlaps the axis"
    assert note.y0 >= 0, "the note is off the bottom of the figure"
