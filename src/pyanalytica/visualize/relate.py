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


def _levels(series: pd.Series) -> list:
    """The order seaborn gives hue levels: categories, else order of
    appearance, else sorted for numbers. The fitted lines borrow the same
    order so their colours match the points."""
    if hasattr(series, "cat"):
        return [c for c in series.cat.categories if c in set(series.dropna())]
    values = pd.unique(series.dropna())
    if pd.api.types.is_numeric_dtype(series):
        values = np.sort(values)
    return list(values)


def _fit(d: pd.DataFrame, x: str, y: str):
    """Slope, intercept and R² of the straight line, or None when there is
    nothing to fit -- fewer than three points, or an X that never changes."""
    d = d[[x, y]].dropna()
    if len(d) < 3 or d[x].nunique() < 2:
        return None
    res = stats.linregress(d[x], d[y])
    return float(res.slope), float(res.intercept), float(res.rvalue ** 2)


def _draw_fit(ax, d: pd.DataFrame, x: str, y: str, *, color, label: str | None) -> bool:
    fit = _fit(d, x, y)
    if fit is None:
        return False
    slope, intercept, r2 = fit
    xs = np.linspace(d[x].min(), d[x].max(), 100)
    text = f"R² = {r2:.3f}" if label is None else f"{label}: R² = {r2:.3f}"
    ax.plot(xs, intercept + slope * xs, "--", color=color, linewidth=2, label=text)
    return True


def _native(value):
    """A level as a plain Python value, so its repr is valid shown code."""
    return value.item() if hasattr(value, "item") else value


def _fit_code(frame: str, x: str, y: str, indent: str, color: str, label: str) -> list[str]:
    """The shown code for one fitted line drawn on ``ax`` from ``frame``."""
    return [
        f'{indent}part = {frame}[["{x}", "{y}"]].dropna()',
        f'{indent}if len(part) >= 3:',
        f'{indent}    slope, intercept = np.polyfit(part["{x}"], part["{y}"], 1)',
        f'{indent}    r2 = part["{x}"].corr(part["{y}"]) ** 2',
        f'{indent}    xs = np.linspace(part["{x}"].min(), part["{x}"].max(), 100)',
        f'{indent}    ax.plot(xs, intercept + slope * xs, "--", linewidth=2, color={color}, label={label})',
    ]


def scatter(
    df: pd.DataFrame, x: str, y: str,
    color_by: str | None = None, size_by: str | None = None,
    style_by: str | None = None, trend_line: bool = True,
    facet_col: str | None = None, facet_row: str | None = None,
) -> tuple[Figure, CodeSnippet]:
    """Create a scatter plot of two numeric variables.

    With Color By each group gets its own fitted line in its own colour, and
    with facets each panel gets its own, so the chart answers "does the
    pattern hold within groups?" rather than hiding it.

    The group order and colours are written out in the shown code. Leaving
    them to defaults gave the points seaborn's order (order of appearance)
    and the lines groupby's (sorted), so a report that re-ran the code drew
    the "yes" line in the "no" colour -- correct on screen, wrong in the
    report, and nothing to show which was which.
    """
    plot_kwargs: dict = {"alpha": 0.6}
    hue = color_by if color_by and color_by in df.columns else None
    if size_by and size_by in df.columns:
        plot_kwargs["size"] = size_by
    if style_by and style_by in df.columns:
        plot_kwargs["style"] = style_by
    fit_ok = trend_line and x != y

    hue_order: list = []
    colors: dict = {}
    if hue:
        hue_order = [_native(v) for v in _levels(df[hue])]
        colors = dict(zip(hue_order, sns.color_palette(n_colors=len(hue_order))))
        plot_kwargs.update(hue=hue, hue_order=hue_order, palette=colors)

    title = f"{y} vs {x}" + (f" by {hue}" if hue else "")

    # Build code snippet parts
    setup_lines: list[str] = []
    extra_args = ""
    if hue:
        setup_lines = [
            f"hue_order = {hue_order!r}",
            "colors = dict(zip(hue_order, sns.color_palette(n_colors=len(hue_order))))",
        ]
        extra_args += f', hue="{hue}", hue_order=hue_order, palette=colors'
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
        if fit_ok:
            # One line per panel, and per group within the panel when
            # coloured. facet_data() yields each panel's rows with its axes
            # position, which is the public way to walk a FacetGrid.
            for (row_i, col_j, _), sub in g.facet_data():
                ax = g.axes[row_i, col_j]
                if hue:
                    for level in hue_order:
                        _draw_fit(ax, sub[sub[hue] == level], x, y,
                                  color=colors[level], label=str(level))
                else:
                    _draw_fit(ax, sub, x, y, color="red", label=None)
                if ax.get_lines():
                    ax.legend(fontsize="small")
        g.figure.suptitle(title)
        g.figure.set_layout_engine("tight")
        fig = g.figure

        facet_args = ""
        if facet_col:
            facet_args += f', col="{facet_col}"'
        if facet_row:
            facet_args += f', row="{facet_row}"'

        code_lines = setup_lines + [
            f'g = sns.relplot(data=df, x="{x}", y="{y}", kind="scatter", alpha=0.6{extra_args}{facet_args})',
        ]
        if fit_ok:
            code_lines.append("for (row_i, col_j, _), sub in g.facet_data():")
            code_lines.append("    ax = g.axes[row_i, col_j]")
            if hue:
                code_lines.append("    for level in hue_order:")
                code_lines += _fit_code(f'sub[sub["{hue}"] == level]', x, y, "        ",
                                        "colors[level]", 'f"{level}: R² = {r2:.3f}"')
            else:
                code_lines += _fit_code("sub", x, y, "    ", '"red"', 'f"R² = {r2:.3f}"')
            code_lines.append('    ax.legend(fontsize="small")')
        code_lines += [
            f'g.figure.suptitle("{title}")',
            f'plt.tight_layout()',
            f'plt.show()',
        ]
    else:
        # Use axes-level API (original path)
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.scatterplot(data=df, x=x, y=y, ax=ax, **plot_kwargs)

        code_lines = setup_lines + [
            f'fig, ax = plt.subplots(figsize=(8, 6))',
            f'sns.scatterplot(data=df, x="{x}", y="{y}", alpha=0.6{extra_args}, ax=ax)',
        ]

        if fit_ok and hue:
            for level in hue_order:
                _draw_fit(ax, df[df[hue] == level], x, y, color=colors[level], label=str(level))
            code_lines.append("for level in hue_order:")
            code_lines += _fit_code(f'df[df["{hue}"] == level]', x, y, "    ",
                                    "colors[level]", 'f"{level}: R² = {r2:.3f}"')
        elif fit_ok:
            _draw_fit(ax, df, x, y, color="red", label=None)
            code_lines += _fit_code("df", x, y, "", '"red"', 'f"R² = {r2:.3f}"')
        if fit_ok:
            ax.legend()
            code_lines.append("ax.legend()")

        ax.set_title(title)
        fig.set_layout_engine("tight", pad=1.5)

        code_lines.extend([
            f'ax.set_title("{title}")',
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
        f'ax.set_xlabel("{x}")\n'
        f'ax.set_ylabel("{y}")\n'
        f'ax.set_title("{y} vs {x} (hexbin)")\n'
        f'plt.tight_layout()\n'
        f'plt.show()'
    )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt"],
    )
