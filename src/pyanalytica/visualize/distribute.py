"""Distribution visualizations — histogram, boxplot, violin, bar chart."""

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


def histogram(
    df: pd.DataFrame, col: str, bins: int = 30,
    kde: bool = False, ref_lines: bool = True,
    group_by: str | None = None,
    facet_col: str | None = None, facet_row: str | None = None,
) -> tuple[Figure, CodeSnippet]:
    """Create a histogram of a numeric column."""
    hue_kwarg = {}
    if group_by and group_by in df.columns:
        hue_kwarg["hue"] = group_by
    hue_str = f', hue="{group_by}"' if group_by else ""
    kde_str = ", kde=True" if kde else ""
    facet_str = _build_facet_args(facet_col, facet_row)

    if facet_col or facet_row:
        facet_kwargs = {}
        if facet_col and facet_col in df.columns:
            facet_kwargs["col"] = facet_col
        if facet_row and facet_row in df.columns:
            facet_kwargs["row"] = facet_row

        g = sns.displot(
            data=df, x=col, bins=bins, kde=kde,
            kind="hist", **hue_kwarg, **facet_kwargs,
        )
        g.figure.suptitle(f"Distribution of {col}", y=1.02)
        g.figure.set_layout_engine("tight")
        fig = g.figure

        code = (
            f'g = sns.displot(data=df, x="{col}", bins={bins}{kde_str}{hue_str}{facet_str})\n'
            f'g.figure.suptitle("Distribution of {col}", y=1.02)\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )
    else:
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.histplot(data=df, x=col, bins=bins, kde=kde, ax=ax, **hue_kwarg)

        if ref_lines and not group_by:
            mean_val = df[col].mean()
            median_val = df[col].median()
            ax.axvline(mean_val, color="red", linestyle="--", label=f"Mean: {mean_val:.2f}")
            ax.axvline(median_val, color="green", linestyle="-.", label=f"Median: {median_val:.2f}")
            ax.legend()

        ax.set_title(f"Distribution of {col}")
        ax.set_xlabel(col)
        ax.set_ylabel("Count")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(8, 5))\n'
            f'sns.histplot(df["{col}"].dropna(), bins={bins}{kde_str}{hue_str}, ax=ax)\n'
            f'ax.set_title("Distribution of {col}")\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt", "import seaborn as sns"],
    )


def boxplot(
    df: pd.DataFrame, col: str,
    group_by: str | None = None,
    facet_col: str | None = None, facet_row: str | None = None,
) -> tuple[Figure, CodeSnippet]:
    """Create a boxplot of a numeric column."""
    hue_kwarg = {}
    if group_by and group_by in df.columns:
        hue_kwarg["hue"] = group_by
    hue_str = f', hue="{group_by}"' if group_by else ""
    facet_str = _build_facet_args(facet_col, facet_row)

    if facet_col or facet_row:
        facet_kwargs = {}
        if facet_col and facet_col in df.columns:
            facet_kwargs["col"] = facet_col
        if facet_row and facet_row in df.columns:
            facet_kwargs["row"] = facet_row

        g = sns.catplot(
            data=df, x=col, kind="box",
            **hue_kwarg, **facet_kwargs,
        )
        g.figure.suptitle(f"Box Plot of {col}", y=1.02)
        g.figure.set_layout_engine("tight")
        fig = g.figure

        code = (
            f'g = sns.catplot(data=df, x="{col}", kind="box"{hue_str}{facet_str})\n'
            f'g.figure.suptitle("Box Plot of {col}", y=1.02)\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )
    else:
        fig, ax = plt.subplots(figsize=(8, 5))
        if group_by:
            sns.boxplot(data=df, x=group_by, y=col, ax=ax)
        else:
            sns.boxplot(x=df[col].dropna(), ax=ax)
        ax.set_title(f"Box Plot of {col}")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(8, 5))\n'
            f'sns.boxplot(x=df["{col}"].dropna(){hue_str}, ax=ax)\n'
            f'ax.set_title("Box Plot of {col}")\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt", "import seaborn as sns"],
    )


def violin(
    df: pd.DataFrame, col: str,
    group_by: str | None = None,
    facet_col: str | None = None, facet_row: str | None = None,
) -> tuple[Figure, CodeSnippet]:
    """Create a violin plot of a numeric column."""
    hue_kwarg = {}
    if group_by and group_by in df.columns:
        hue_kwarg["hue"] = group_by
    hue_str = f', hue="{group_by}"' if group_by else ""
    facet_str = _build_facet_args(facet_col, facet_row)

    if facet_col or facet_row:
        facet_kwargs = {}
        if facet_col and facet_col in df.columns:
            facet_kwargs["col"] = facet_col
        if facet_row and facet_row in df.columns:
            facet_kwargs["row"] = facet_row

        g = sns.catplot(
            data=df, x=col, kind="violin",
            **hue_kwarg, **facet_kwargs,
        )
        g.figure.suptitle(f"Violin Plot of {col}", y=1.02)
        g.figure.set_layout_engine("tight")
        fig = g.figure

        code = (
            f'g = sns.catplot(data=df, x="{col}", kind="violin"{hue_str}{facet_str})\n'
            f'g.figure.suptitle("Violin Plot of {col}", y=1.02)\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )
    else:
        fig, ax = plt.subplots(figsize=(8, 5))
        if group_by:
            sns.violinplot(data=df, x=group_by, y=col, ax=ax)
        else:
            sns.violinplot(x=df[col].dropna(), ax=ax)
        ax.set_title(f"Violin Plot of {col}")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(8, 5))\n'
            f'sns.violinplot(x=df["{col}"].dropna(){hue_str}, ax=ax)\n'
            f'ax.set_title("Violin Plot of {col}")\n'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt", "import seaborn as sns"],
    )


def bar_chart(
    df: pd.DataFrame, col: str, orientation: str = "vertical",
    sort: bool = True, pct: bool = False,
) -> tuple[Figure, CodeSnippet]:
    """Create a bar chart of a categorical column."""
    fig, ax = plt.subplots(figsize=(8, 5))

    counts = df[col].value_counts()
    if sort:
        counts = counts.sort_values(ascending=False)

    if pct:
        counts = counts / counts.sum() * 100
        ylabel = "Percentage"
    else:
        ylabel = "Count"

    if orientation == "horizontal":
        counts.plot.barh(ax=ax)
        ax.set_xlabel(ylabel)
    else:
        counts.plot.bar(ax=ax)
        ax.set_ylabel(ylabel)

    ax.set_title(f"{'Percentage' if pct else 'Count'} of {col}")
    fig.set_layout_engine("tight", pad=1.5)

    sort_str = ".sort_values(ascending=False)" if sort else ""
    pct_str = " / counts.sum() * 100" if pct else ""
    plot_type = "barh" if orientation == "horizontal" else "bar"
    code = (
        f'counts = df["{col}"].value_counts(){sort_str}{pct_str}\n'
        f'fig, ax = plt.subplots(figsize=(8, 5))\n'
        f'counts.plot.{plot_type}(ax=ax)\n'
        f'ax.set_title("{"Percentage" if pct else "Count"} of {col}")\n'
        f'plt.tight_layout()\n'
        f'plt.show()'
    )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt"],
    )
