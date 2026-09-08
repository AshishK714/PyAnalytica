"""Comparison visualizations — grouped boxplot, violin, bar of means, strip plot."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from pyanalytica.core.codegen import CodeSnippet

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
    if sort_by == "mean":
        order = df.groupby(x_cat)[y_num].mean().sort_values(ascending=False).index.tolist()
    elif sort_by == "median":
        order = df.groupby(x_cat)[y_num].median().sort_values(ascending=False).index.tolist()
    else:
        order = sorted(df[x_cat].dropna().unique())

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
            data=df, x=x_cat, y=y_num, kind="box",
            order=order, **hue_kwarg, **facet_kwargs,
        )
        g.figure.suptitle(f"{y_num} by {x_cat}")
        g.set_xticklabels(rotation=45, ha="right")
        g.figure.set_layout_engine("tight")
        fig = g.figure

        code = (
            f'g = sns.catplot(data=df, x="{x_cat}", y="{y_num}", kind="box"{hue_str}{facet_str})\n'
            f'g.figure.suptitle("{y_num} by {x_cat}")\n'
            f'g.set_xticklabels(rotation=45, ha="right")\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.boxplot(data=df, x=x_cat, y=y_num, order=order, ax=ax, **hue_kwarg)
        ax.set_title(f"{y_num} by {x_cat}")
        plt.xticks(rotation=45, ha="right")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(10, 6))\n'
            f'order = df.groupby("{x_cat}")["{y_num}"].mean().sort_values(ascending=False).index\n'
            f'sns.boxplot(data=df, x="{x_cat}", y="{y_num}", order=order{hue_str}, ax=ax)\n'
            f'ax.set_title("{y_num} by {x_cat}")\n'
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
        ax.set_title(f"{y_num} by {x_cat}")
        plt.xticks(rotation=45, ha="right")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(10, 6))\n'
            f'sns.violinplot(data=df, x="{x_cat}", y="{y_num}"{hue_str}, ax=ax)\n'
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
) -> tuple[Figure, CodeSnippet]:
    """Create a bar chart of means with optional error bars."""
    hue_kwarg = {}
    if hue and hue in df.columns:
        hue_kwarg["hue"] = hue
    hue_str = f', hue="{hue}"' if hue else ""
    err_str = ', errorbar=("ci", 95)' if error_bars else ""
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
        g.figure.suptitle(f"Mean {y_num} by {x_cat}")
        g.set_xticklabels(rotation=45, ha="right")
        g.figure.set_layout_engine("tight")
        fig = g.figure

        code = (
            f'g = sns.catplot(data=df, x="{x_cat}", y="{y_num}", kind="bar"{err_str}{hue_str}{facet_str})\n'
            f'g.figure.suptitle("Mean {y_num} by {x_cat}")\n'
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
        ax.set_title(f"Mean {y_num} by {x_cat}")
        plt.xticks(rotation=45, ha="right")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(10, 6))\n'
            f'sns.barplot(data=df, x="{x_cat}", y="{y_num}"{err_str}{hue_str}, ax=ax)\n'
            f'ax.set_title("Mean {y_num} by {x_cat}")\n'
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
        ax.set_title(f"{y_num} by {x_cat}")
        plt.xticks(rotation=45, ha="right")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(10, 6))\n'
            f'sns.stripplot(data=df, x="{x_cat}", y="{y_num}", alpha=0.5, jitter=True{hue_str}, ax=ax)\n'
            f'ax.set_title("{y_num} by {x_cat}")\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt", "import seaborn as sns"],
    )
