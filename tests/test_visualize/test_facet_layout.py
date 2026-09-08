"""Faceted figures must not push their title off the canvas -- issue 13.

The figures set their suptitle at `y=1.02`, which is above the figure in figure
coordinates. A layout engine reserves room for a title it places; it cannot
reserve room for one deliberately put outside. The result was 10px of title
hanging over the edge on every faceted chart, which the card then clipped.

Measured the way the browser sees it: resize to the panel's shape, draw, and
check what landed where.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from pyanalytica.data.load import load_bundled
from pyanalytica.visualize.compare import bar_of_means, grouped_violin
from pyanalytica.visualize.distribute import histogram, violin

#: The shape a disclosed plot is rendered at.
SHAPE = (10.42, 5.20)


@pytest.fixture(scope="module")
def df():
    frame, _ = load_bundled("titanic")
    return frame.dropna(subset=["Age"])


def _figures(df):
    return {
        "histogram, facet column and row":
            histogram(df, "Age", facet_col="Sex", facet_row="Survived")[0],
        "histogram, grouped":
            histogram(df, "Age", group_by="Sex")[0],
        "violin, grouped and facetted":
            violin(df, "Age", group_by="Sex", facet_col="Survived")[0],
        "bar of means with hue":
            bar_of_means(df, "Pclass", "Age", hue="Sex")[0],
        "grouped violin with facets":
            grouped_violin(df, "Pclass", "Age", hue="Sex", facet_col="Survived")[0],
    }


@pytest.fixture(scope="module")
def figures(df):
    built = _figures(df)
    yield built
    for fig in built.values():
        plt.close(fig)


def test_nothing_is_drawn_above_the_canvas(figures):
    over = []
    for name, fig in figures.items():
        fig.set_size_inches(*SHAPE)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        top = fig.bbox.y1
        if fig._suptitle is not None:
            box = fig._suptitle.get_window_extent(renderer)
            if box.y1 > top:
                over.append(f"{name}: suptitle {box.y1 - top:.0f}px above the canvas")
        for ax in fig.axes:
            if not ax.get_title():
                continue
            box = ax.title.get_window_extent(renderer)
            if box.y1 > top:
                over.append(f"{name}: a facet title {box.y1 - top:.0f}px above")
    assert not over, "\n  ".join(over)


def test_a_suptitle_does_not_sit_on_top_of_a_facet_title(figures):
    collisions = []
    for name, fig in figures.items():
        if fig._suptitle is None:
            continue
        fig.set_size_inches(*SHAPE)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        sup = fig._suptitle.get_window_extent(renderer)
        for ax in fig.axes:
            if not ax.get_title():
                continue
            box = ax.title.get_window_extent(renderer)
            overlaps = (sup.y0 < box.y1 and box.y0 < sup.y1
                        and sup.x0 < box.x1 and box.x0 < sup.x1)
            if overlaps:
                collisions.append(f"{name}: suptitle overlaps a facet title")
                break
    assert not collisions, "\n  ".join(collisions)


def test_legends_stay_inside_the_figure(figures):
    outside = []
    for name, fig in figures.items():
        fig.set_size_inches(*SHAPE)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        legends = list(fig.legends) + [ax.get_legend() for ax in fig.axes if ax.get_legend()]
        for legend in legends:
            box = legend.get_window_extent(renderer)
            if box.x1 > fig.bbox.x1 + 1 or box.x0 < -1:
                outside.append(f"{name}: legend runs from {box.x0:.0f} to {box.x1:.0f}px")
    assert not outside, "\n  ".join(outside)


def test_no_figure_places_its_title_outside_itself():
    """The cause, asserted at the source so it cannot come back by copy-paste."""
    import pathlib

    src = pathlib.Path(__file__).resolve().parents[2] / "src" / "pyanalytica"
    offenders = [
        f"{path.relative_to(src)}:{i}"
        for path in src.rglob("*.py")
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "suptitle" in line and "y=1.0" in line
    ]
    assert not offenders, (
        "a suptitle placed above the figure leaves the layout engine no room "
        "to reserve for it: " + ", ".join(offenders)
    )
