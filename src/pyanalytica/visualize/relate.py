"""Relationship visualizations — scatter, hexbin with trend lines."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

from pyanalytica.core.codegen import CodeSnippet

Figure = matplotlib.figure.Figure


def scatter(
    df: pd.DataFrame, x: str, y: str,
    color_by: str | None = None, size_by: str | None = None,
    style_by: str | None = None, trend_line: bool = True,
    facet_col: str | None = None, facet_row: str | None = None,
) -> tuple[Figure, CodeSnippet]:
    """Create a scatter plot of two numeric variables."""
    plot_kwargs: dict = {"alpha": 0.6}
    if color_by and color_by in df.columns:
        plot_kwargs["hue"] = color_by
    if size_by and size_by in df.columns:
        plot_kwargs["size"] = size_by
    if style_by and style_by in df.columns:
        plot_kwargs["style"] = style_by

    clean = df[[x, y]].dropna()

    # Build code snippet parts
    extra_args = ""
    if color_by:
        extra_args += f', hue="{color_by}"'
    if size_by:
        extra_args += f', size="{size_by}"'
    if style_by:
        extra_args += f', style="{style_by}"'

    if facet_col or facet_row:
        # Use figure-level API for faceting
        facet_kwargs = {}
        if facet_col and facet_col in df.columns:
            facet_kwargs["col"] = facet_col
        if facet_row and facet_row in df.columns:
            facet_kwargs["row"] = facet_row

        g = sns.relplot(
            data=df, x=x, y=y, kind="scatter",
            **facet_kwargs, **plot_kwargs,
        )
        g.figure.suptitle(f"{y} vs {x}")
        g.figure.set_layout_engine("tight")
        fig = g.figure

        facet_args = ""
        if facet_col:
            facet_args += f', col="{facet_col}"'
        if facet_row:
            facet_args += f', row="{facet_row}"'

        code_lines = [
            f'g = sns.relplot(data=df, x="{x}", y="{y}", kind="scatter", alpha=0.6{extra_args}{facet_args})',
            f'g.figure.suptitle("{y} vs {x}")',
            f'plt.tight_layout()',
            f'plt.show()',
        ]
    else:
        # Use axes-level API (original path)
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.scatterplot(data=df, x=x, y=y, ax=ax, **plot_kwargs)

        code_lines = [
            f'fig, ax = plt.subplots(figsize=(8, 6))',
            f'sns.scatterplot(data=df, x="{x}", y="{y}", alpha=0.6{extra_args}, ax=ax)',
        ]

        if trend_line and len(clean) > 2 and x != y:
            slope, intercept, r_value, p_value, std_err = stats.linregress(clean[x], clean[y])
            x_range = np.linspace(clean[x].min(), clean[x].max(), 100)
            ax.plot(x_range, intercept + slope * x_range, "r--", linewidth=2,
                    label=f"R\u00b2 = {r_value**2:.3f}")
            ax.legend()

            code_lines.extend([
                f'from scipy import stats',
                f'slope, intercept, r, p, se = stats.linregress(df["{x}"].dropna(), df["{y}"].dropna())',
                f'x_range = np.linspace(df["{x}"].min(), df["{x}"].max(), 100)',
                f'ax.plot(x_range, intercept + slope * x_range, "r--", label=f"R\u00b2 = {{r**2:.3f}}")',
                f'ax.legend()',
            ])

        ax.set_title(f"{y} vs {x}")
        fig.set_layout_engine("tight", pad=1.5)

        code_lines.extend([
            f'ax.set_title("{y} vs {x}")',
            f'plt.tight_layout()',
            f'plt.show()',
        ])

    return fig, CodeSnippet(
        code="\n".join(code_lines),
        imports=["import matplotlib.pyplot as plt", "import numpy as np", "import seaborn as sns"],
    )


def hexbin(
    df: pd.DataFrame, x: str, y: str, gridsize: int = 30,
) -> tuple[Figure, CodeSnippet]:
    """Create a hexbin plot for large datasets."""
    fig, ax = plt.subplots(figsize=(8, 6))
    clean = df[[x, y]].dropna()
    hb = ax.hexbin(clean[x], clean[y], gridsize=gridsize, cmap="YlOrRd", mincnt=1)
    fig.colorbar(hb, ax=ax, label="Count")
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(f"{y} vs {x} (hexbin)")
    fig.set_layout_engine("tight", pad=1.5)

    code = (
        f'fig, ax = plt.subplots(figsize=(8, 6))\n'
        f'hb = ax.hexbin(df["{x}"], df["{y}"], gridsize={gridsize}, cmap="YlOrRd", mincnt=1)\n'
        f'fig.colorbar(hb, ax=ax, label="Count")\n'
        f'ax.set_title("{y} vs {x} (hexbin)")\n'
        f'plt.tight_layout()\n'
        f'plt.show()'
    )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt"],
    )
