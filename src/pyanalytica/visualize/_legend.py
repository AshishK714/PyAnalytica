"""Put a colour legend beside the plot, never over the data.

Two ways it landed on the data, both reported from a student-style run:

* An axes-level chart (boxplot, bar of means, histogram, scatter with a
  hue) let matplotlib pick a corner "best" for the legend, and with bars or
  boxes in every corner the best was still on top of one.
* A figure-level chart (seaborn's catplot, displot, relplot) puts its legend
  on the figure, outside the axes. The panels then switch on the "tight"
  layout engine so titles are not clipped when the figure is resized for
  the screen, and that engine does not know about figure legends: it spread
  the axes across the full width and the bars ran under the legend. A
  report that re-ran the code drew it correctly, so the screen and the
  report disagreed.

Both now end in the same place: an axes legend anchored just outside the
top-right axes. The layout engine counts axes legends, so it makes room.
"""

from __future__ import annotations

#: The shown-code line for an axes-level chart. Figure-level charts need no
#: line: seaborn's own layout already puts their legend outside, which is
#: what the shown code draws when it runs on its own.
AXES_CODE = 'sns.move_legend(ax, "upper left", bbox_to_anchor=(1.01, 1), borderaxespad=0, frameon=False)\n'

_PLACE = {"loc": "upper left", "bbox_to_anchor": (1.01, 1), "borderaxespad": 0, "frameon": False}


def beside_axes(ax) -> bool:
    """Move an axes' legend outside its right edge. True if there was one."""
    import seaborn as sns

    if ax.get_legend() is None:
        return False
    sns.move_legend(ax, **_PLACE)
    return True


def beside_grid(g) -> bool:
    """Move a FacetGrid's figure legend onto its top-right axes, outside.

    It becomes that axes' own legend, which is what the layout engine makes
    room for; a legend added as a loose artist ran off the canvas. If the
    panel already had a legend of its own (a scatter's fitted lines, say),
    that one is kept as an artist alongside.
    """
    legend = getattr(g, "_legend", None)
    if legend is None:
        return False
    handles = list(legend.legend_handles)
    labels = [t.get_text() for t in legend.get_texts()]
    title = legend.get_title().get_text() or None
    legend.remove()
    g._legend = None

    axes = g.axes
    ax = axes[0, -1] if getattr(axes, "ndim", 1) == 2 else axes.flat[-1]
    own = ax.get_legend()
    if own is not None:
        ax.add_artist(own)  # keep it drawn once ax.legend() replaces legend_
    ax.legend(handles, labels, title=title, **_PLACE)
    return True
