"""Comparison visualizations — grouped boxplot, violin, bar of means, strip plot."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from pyanalytica.core.codegen import CodeSnippet
from pyanalytica.visualize._legend import AXES_CODE, beside_axes, beside_grid

Figure = matplotlib.figure.Figure


def _build_facet_args(facet_col: str | None, facet_row: str | None) -> str:
    """Build facet argument string for code snippet."""
    args = ""
    if facet_col:
        args += f', col="{facet_col}"'
    if facet_row:
        args += f', row="{facet_row}"'
    return args


def grouped_boxplot(
    df: pd.DataFrame, x_cat: str, y_num: str,
    sort_by: str = "mean", hue: str | None = None,
    facet_col: str | None = None, facet_row: str | None = None,
) -> tuple[Figure, CodeSnippet]:
    """Create a grouped box plot."""
    # The shown code sorts the way the chart did. It used to sort by the mean
    # whatever sort_by said, so a chart in name order came with code that
    # drew it in a different order.
    if sort_by == "mean":
        order = df.groupby(x_cat)[y_num].mean().sort_values(ascending=False).index.tolist()
        order_code = f'order = df.groupby("{x_cat}")["{y_num}"].mean().sort_values(ascending=False).index\n'
    elif sort_by == "median":
        order = df.groupby(x_cat)[y_num].median().sort_values(ascending=False).index.tolist()
        order_code = f'order = df.groupby("{x_cat}")["{y_num}"].median().sort_values(ascending=False).index\n'
    else:
        order = sorted(df[x_cat].dropna().unique())
        order_code = f'order = sorted(df["{x_cat}"].dropna().unique())\n'

    hue_kwarg = {}
    if hue and hue in df.columns:
        hue_kwarg["hue"] = hue
    hue_str = f', hue="{hue}"' if hue else ""
    facet_str = _build_facet_args(facet_col, facet_row)
    title = f"{y_num} by {x_cat}" + (f", split by {hue}" if hue else "")

    if facet_col or facet_row:
        facet_kwargs = {}
        if facet_col and facet_col in df.columns:
            facet_kwargs["col"] = facet_col
        if facet_row and facet_row in df.columns:
            facet_kwargs["row"] = facet_row

        g = sns.catplot(
            data=df, x=x_cat, y=y_num, kind="box",
            order=order, **hue_kwarg, **facet_kwargs,
        )
        g.figure.suptitle(title)
        g.set_xticklabels(rotation=45, ha="right")
        beside_grid(g)
        g.figure.set_layout_engine("tight")
        fig = g.figure

        code = (
            f'{order_code}'
            f'g = sns.catplot(data=df, x="{x_cat}", y="{y_num}", kind="box", order=order{hue_str}{facet_str})\n'
            f'g.figure.suptitle("{title}")\n'
            f'g.set_xticklabels(rotation=45, ha="right")\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.boxplot(data=df, x=x_cat, y=y_num, order=order, ax=ax, **hue_kwarg)
        if hue:
            beside_axes(ax)
        ax.set_title(title)
        plt.xticks(rotation=45, ha="right")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(10, 6))\n'
            f'{order_code}'
            f'sns.boxplot(data=df, x="{x_cat}", y="{y_num}", order=order{hue_str}, ax=ax)\n'
            f'{AXES_CODE if hue else ""}'
            f'ax.set_title("{title}")\n'
            f'plt.xticks(rotation=45, ha="right")\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt", "import seaborn as sns"],
    )


def grouped_violin(
    df: pd.DataFrame, x_cat: str, y_num: str,
    hue: str | None = None,
    facet_col: str | None = None, facet_row: str | None = None,
) -> tuple[Figure, CodeSnippet]:
    """Create a grouped violin plot."""
    order = df.groupby(x_cat)[y_num].mean().sort_values(ascending=False).index.tolist()

    hue_kwarg = {}
    if hue and hue in df.columns:
        hue_kwarg["hue"] = hue
    hue_str = f', hue="{hue}"' if hue else ""
    facet_str = _build_facet_args(facet_col, facet_row)

    if facet_col or facet_row:
        facet_kwargs = {}
        if facet_col and facet_col in df.columns:
            facet_kwargs["col"] = facet_col
        if facet_row and facet_row in df.columns:
            facet_kwargs["row"] = facet_row

        g = sns.catplot(
            data=df, x=x_cat, y=y_num, kind="violin",
            order=order, **hue_kwarg, **facet_kwargs,
        )
        g.figure.suptitle(f"{y_num} by {x_cat}")
        g.set_xticklabels(rotation=45, ha="right")
        beside_grid(g)
        g.figure.set_layout_engine("tight")
        fig = g.figure

        code = (
            f'g = sns.catplot(data=df, x="{x_cat}", y="{y_num}", kind="violin"{hue_str}{facet_str})\n'
            f'g.figure.suptitle("{y_num} by {x_cat}")\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.violinplot(data=df, x=x_cat, y=y_num, order=order, ax=ax, **hue_kwarg)
        if hue:
            beside_axes(ax)
        ax.set_title(f"{y_num} by {x_cat}")
        plt.xticks(rotation=45, ha="right")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(10, 6))\n'
            f'sns.violinplot(data=df, x="{x_cat}", y="{y_num}"{hue_str}, ax=ax)\n'
            f'{AXES_CODE if hue else ""}'
            f'ax.set_title("{y_num} by {x_cat}")\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt", "import seaborn as sns"],
    )


def bar_of_means(
    df: pd.DataFrame, x_cat: str, y_num: str,
    error_bars: bool = True, hue: str | None = None,
    facet_col: str | None = None, facet_row: str | None = None,
    order: list | None = None,
) -> tuple[Figure, CodeSnippet]:
    """Create a bar chart of means with optional error bars.

    *order* fixes the order of the bars, so a panel that also shows a table
    and a boxplot of the same groups can list them the same way in all three.
    """
    hue_kwarg = {}
    if hue and hue in df.columns:
        hue_kwarg["hue"] = hue
    if order is not None:
        hue_kwarg["order"] = list(order)
    hue_str = f', hue="{hue}"' if hue else ""
    if order is not None:
        plain = [o.item() if hasattr(o, "item") else o for o in order]
        hue_str = f", order={plain!r}" + hue_str
    title = f"Mean {y_num} by {x_cat}" + (f", split by {hue}" if hue else "")
    # seaborn draws 95% CI bars by default, so turning them off has to be
    # written out or the shown code draws bars the panel did not.
    err_str = ', errorbar=("ci", 95)' if error_bars else ", errorbar=None"
    facet_str = _build_facet_args(facet_col, facet_row)

    if facet_col or facet_row:
        facet_kwargs = {}
        if facet_col and facet_col in df.columns:
            facet_kwargs["col"] = facet_col
        if facet_row and facet_row in df.columns:
            facet_kwargs["row"] = facet_row

        g = sns.catplot(
            data=df, x=x_cat, y=y_num, kind="bar",
            errorbar=("ci", 95) if error_bars else None,
            **hue_kwarg, **facet_kwargs,
        )
        g.figure.suptitle(title)
        g.set_xticklabels(rotation=45, ha="right")
        beside_grid(g)
        g.figure.set_layout_engine("tight")
        fig = g.figure

        code = (
            f'g = sns.catplot(data=df, x="{x_cat}", y="{y_num}", kind="bar"{err_str}{hue_str}{facet_str})\n'
            f'g.figure.suptitle("{title}")\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(
            data=df, x=x_cat, y=y_num,
            errorbar=("ci", 95) if error_bars else None,
            ax=ax, **hue_kwarg,
        )
        if hue:
            beside_axes(ax)
        ax.set_title(title)
        plt.xticks(rotation=45, ha="right")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(10, 6))\n'
            f'sns.barplot(data=df, x="{x_cat}", y="{y_num}"{err_str}{hue_str}, ax=ax)\n'
            f'{AXES_CODE if hue else ""}'
            f'ax.set_title("{title}")\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt", "import seaborn as sns"],
    )


def strip_plot(
    df: pd.DataFrame, x_cat: str, y_num: str,
    hue: str | None = None,
    facet_col: str | None = None, facet_row: str | None = None,
) -> tuple[Figure, CodeSnippet]:
    """Create a strip plot (jittered dot plot)."""
    hue_kwarg = {}
    if hue and hue in df.columns:
        hue_kwarg["hue"] = hue
    hue_str = f', hue="{hue}"' if hue else ""
    facet_str = _build_facet_args(facet_col, facet_row)

    if facet_col or facet_row:
        facet_kwargs = {}
        if facet_col and facet_col in df.columns:
            facet_kwargs["col"] = facet_col
        if facet_row and facet_row in df.columns:
            facet_kwargs["row"] = facet_row

        g = sns.catplot(
            data=df, x=x_cat, y=y_num, kind="strip",
            alpha=0.5, jitter=True, **hue_kwarg, **facet_kwargs,
        )
        g.figure.suptitle(f"{y_num} by {x_cat}")
        g.set_xticklabels(rotation=45, ha="right")
        beside_grid(g)
        g.figure.set_layout_engine("tight")
        fig = g.figure

        code = (
            f'g = sns.catplot(data=df, x="{x_cat}", y="{y_num}", kind="strip", '
            f'alpha=0.5, jitter=True{hue_str}{facet_str})\n'
            f'g.figure.suptitle("{y_num} by {x_cat}")\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.stripplot(data=df, x=x_cat, y=y_num, alpha=0.5, jitter=True, ax=ax, **hue_kwarg)
        if hue:
            beside_axes(ax)
        ax.set_title(f"{y_num} by {x_cat}")
        plt.xticks(rotation=45, ha="right")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(10, 6))\n'
            f'sns.stripplot(data=df, x="{x_cat}", y="{y_num}", alpha=0.5, jitter=True{hue_str}, ax=ax)\n'
            f'{AXES_CODE if hue else ""}'
            f'ax.set_title("{y_num} by {x_cat}")\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt", "import seaborn as sns"],
    )
