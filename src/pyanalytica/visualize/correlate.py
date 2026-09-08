"""Correlation visualizations — correlation matrix, pair plot."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from pyanalytica.core.codegen import CodeSnippet

Figure = matplotlib.figure.Figure


def correlation_matrix(
    df: pd.DataFrame, cols: list[str],
    method: str = "pearson", threshold: float = 0.0,
) -> tuple[Figure, CodeSnippet]:
    """Create a correlation matrix heatmap."""
    corr = df[cols].corr(method=method)

    # Apply threshold mask
    mask_threshold = corr.abs() < threshold
    mask_upper = np.triu(np.ones_like(corr, dtype=bool), k=1)

    fig, ax = plt.subplots(figsize=(max(8, len(cols)), max(6, len(cols) * 0.8)))
    mask = mask_upper | mask_threshold
    sns.heatmap(
        corr, mask=mask, annot=True, fmt=".2f",
        cmap="RdBu_r", center=0, vmin=-1, vmax=1,
        square=True, ax=ax,
    )
    ax.set_title(f"Correlation Matrix ({method.title()})")
    fig.set_layout_engine("tight", pad=1.5)

    cols_str = repr(cols)
    code = (
        f'corr = df[{cols_str}].corr(method="{method}")\n'
        f'mask = np.triu(np.ones_like(corr, dtype=bool), k=1)\n'
        f'fig, ax = plt.subplots(figsize=({max(8, len(cols))}, {max(6, len(cols))}))\n'
        f'sns.heatmap(corr, mask=mask, annot=True, fmt=".2f",\n'
        f'            cmap="RdBu_r", center=0, vmin=-1, vmax=1, square=True, ax=ax)\n'
        f'ax.set_title("Correlation Matrix ({method.title()})")\n'
        f'plt.tight_layout()\n'
        f'plt.show()'
    )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt", "import numpy as np", "import seaborn as sns"],
    )


def pair_plot(
    df: pd.DataFrame, cols: list[str],
    color_by: str | None = None,
) -> tuple[Figure, CodeSnippet]:
    """Create a pair plot (scatter matrix)."""
    plot_cols = cols[:6]  # Limit to 6 columns
    plot_df = df[plot_cols + ([color_by] if color_by else [])].dropna()

    g = sns.pairplot(plot_df, vars=plot_cols, hue=color_by, diag_kind="hist",
                     plot_kws={"alpha": 0.5})
    g.figure.suptitle("Pair Plot", y=1.02)
    fig = g.figure

    hue_str = f', hue="{color_by}"' if color_by else ""
    code = (
        f'g = sns.pairplot(df[{repr(plot_cols)}]{hue_str}, diag_kind="hist",\n'
        f'                 plot_kws={{"alpha": 0.5}})\n'
        f'plt.show()'
    )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt", "import seaborn as sns"],
    )
