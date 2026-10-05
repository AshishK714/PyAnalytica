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


#: Shown-code lines for slanted category labels.
ROTATE_AX_CODE = 'plt.xticks(rotation=45, ha="right")\n'
ROTATE_GRID_CODE = 'g.set_xticklabels(rotation=45, ha="right")\n'


def _rotate(df: pd.DataFrame, col: str) -> bool:
    """Slant the category labels only when they would collide.

    Every group chart slanted them, so two labels ("no", "yes") came out at
    45 degrees for no reason and were harder to read than level ones.
    """
    labels = [str(v) for v in df[col].dropna().unique()]
    return len(labels) > 6 or sum(len(s) for s in labels) > 48


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
        if _rotate(df, x_cat):
            g.set_xticklabels(rotation=45, ha="right")
        beside_grid(g)
        g.figure.set_layout_engine("tight")
        fig = g.figure

        code = (
            f'{order_code}'
            f'g = sns.catplot(data=df, x="{x_cat}", y="{y_num}", kind="box", order=order{hue_str}{facet_str})\n'
            f'g.figure.suptitle("{title}")\n'
            f'{ROTATE_GRID_CODE if _rotate(df, x_cat) else ""}'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.boxplot(data=df, x=x_cat, y=y_num, order=order, ax=ax, **hue_kwarg)
        if hue:
            beside_axes(ax)
        ax.set_title(title)
        if _rotate(df, x_cat):
            plt.xticks(rotation=45, ha="right")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(10, 6))\n'
            f'{order_code}'
            f'sns.boxplot(data=df, x="{x_cat}", y="{y_num}", order=order{hue_str}, ax=ax)\n'
            f'{AXES_CODE if hue else ""}'
            f'ax.set_title("{title}")\n'
            f'{ROTATE_AX_CODE if _rotate(df, x_cat) else ""}'
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
        if _rotate(df, x_cat):
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
        if _rotate(df, x_cat):
            plt.xticks(rotation=45, ha="right")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(10, 6))\n'
            f'sns.violinplot(data=df, x="{x_cat}", y="{y_num}"{hue_str}, ax=ax)\n'
            f'{AXES_CODE if hue else ""}'
            f'ax.set_title("{y_num} by {x_cat}")\n'
            f'{ROTATE_AX_CODE if _rotate(df, x_cat) else ""}'
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
        g.set_ylabels(f"mean {y_num}")
        if _rotate(df, x_cat):
            g.set_xticklabels(rotation=45, ha="right")
        beside_grid(g)
        g.figure.set_layout_engine("tight")
        fig = g.figure

        code = (
            f'g = sns.catplot(data=df, x="{x_cat}", y="{y_num}", kind="bar"{err_str}{hue_str}{facet_str})\n'
            f'g.figure.suptitle("{title}")\n'
            f'g.set_ylabels("mean {y_num}")\n'
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
        # The bars are means, so the axis says so; it said "charges".
        ax.set_ylabel(f"mean {y_num}")
        ax.set_title(title)
        if _rotate(df, x_cat):
            plt.xticks(rotation=45, ha="right")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(10, 6))\n'
            f'sns.barplot(data=df, x="{x_cat}", y="{y_num}"{err_str}{hue_str}, ax=ax)\n'
            f'{AXES_CODE if hue else ""}'
            f'ax.set_ylabel("mean {y_num}")\n'
            f'ax.set_title("{title}")\n'
            f'{ROTATE_AX_CODE if _rotate(df, x_cat) else ""}'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt", "import seaborn as sns"],
    )


#: Above this many bars, labelling each one with its rate and size crowds
#: the chart; the table beside it has both numbers.
MAX_LABELLED_BARS = 24


def _py(value):
    """A numpy scalar as a plain Python value, so its repr is valid code."""
    return value.item() if hasattr(value, "item") else value


def rate_chart(
    df: pd.DataFrame, x: str, y: str, event=None, hue: str | None = None,
) -> tuple[Figure, CodeSnippet]:
    """The share of each group with an outcome: a chart of rates, not counts.

    With a two-level outcome (yes/no, employed or not) each bar is the
    percentage of an ``x`` group with ``y == event``, one bar per ``hue``
    level beside it, labelled with the rate and the group's size. Counts
    hide the rate when groups differ in size (637 against 4,363), which is
    the comparison a two-category question asks about. With more outcome
    levels each group gets a 100% stacked bar, its size under its name.

    The figure is drawn by running the shown code, so the two cannot differ.
    """
    levels = sorted(df[y].dropna().unique(), key=str)
    two = len(levels) == 2
    if two:
        if event is None or event not in levels:
            event = df[y].value_counts().idxmin()
        event = _py(event)
        keys = [x, hue] if hue else [x]
        subset = [x, y] + ([hue] if hue else [])
        n_bars = int(df.dropna(subset=subset).groupby(keys, observed=True).ngroups)
        label = f"% with {y} = {event}"
        title = f"{label}, by {x}" + (f", split by {hue}" if hue else "")
        lines = [
            f"data = df.dropna(subset={subset!r})",
            "rates = (",
            f"    data.assign(event=data[{y!r}].eq({event!r}) * 100)",
            f"    .groupby({keys!r}, observed=True)",
            '    .agg(rate=("event", "mean"), n=("event", "size"))',
            "    .reset_index()",
            ")",
            f"order = sorted(rates[{x!r}].unique())",
            "fig, ax = plt.subplots(figsize=(10, 6))",
        ]
        if hue:
            lines += [
                f"hue_order = sorted(rates[{hue!r}].unique())",
                f"sns.barplot(data=rates, x={x!r}, y=\"rate\", hue={hue!r}, order=order,",
                "            hue_order=hue_order, errorbar=None, ax=ax)",
            ]
            if n_bars <= MAX_LABELLED_BARS:
                lines += [
                    "for bars, level in zip(ax.containers, hue_order):",
                    f"    part = rates[rates[{hue!r}] == level].set_index({x!r}).reindex(order)",
                    '    ax.bar_label(bars, labels=["" if pd.isna(n) else f"{r:.1f}%\\nn={n:,.0f}"',
                    '                              for r, n in zip(part["rate"], part["n"])], fontsize=9)',
                ]
            lines.append(AXES_CODE.rstrip("\n"))
        else:
            lines += [
                f"sns.barplot(data=rates, x={x!r}, y=\"rate\", order=order, errorbar=None, ax=ax)",
            ]
            if n_bars <= MAX_LABELLED_BARS:
                lines += [
                    f"part = rates.set_index({x!r}).reindex(order)",
                    'ax.bar_label(ax.containers[0], labels=[f"{r:.1f}%\\nn={n:,.0f}"',
                    '                                       for r, n in zip(part["rate"], part["n"])], fontsize=9)',
                ]
        lines += [
            "ax.margins(y=0.15)",
            f"ax.set_ylabel({label!r})",
            f"ax.set_title({title!r})",
        ]
        n_ticks = int(df[x].nunique())
        long = max((len(str(v)) for v in df[x].dropna().unique()), default=0)
    else:
        index = f"[df[{hue!r}], df[{x!r}]]" if hue else f"df[{x!r}]"
        title = f"{y} within each {x} group" + (f", split by {hue}" if hue else "") + " (% of group)"
        lines = [
            f"pct = pd.crosstab({index}, df[{y!r}], normalize=\"index\") * 100",
            f"sizes = pd.crosstab({index}, df[{y!r}]).sum(axis=1)",
            "names = [\", \".join(map(str, k)) if isinstance(k, tuple) else str(k) for k in pct.index]",
            'pct.index = [f"{name}\\n(n={n:,})" for name, n in zip(names, sizes)]',
            "fig, ax = plt.subplots(figsize=(10, 6))",
            "pct.plot(kind=\"bar\", stacked=True, width=0.8, ax=ax)",
            AXES_CODE.rstrip("\n"),
            "ax.set_xlabel(" + repr(f"{hue} / {x}" if hue else x) + ")",
            'ax.set_ylabel("% of group")',
            f"ax.set_title({title!r})",
        ]
        groups = df.dropna(subset=[x] + ([hue] if hue else []))
        n_ticks = int(groups.groupby([hue, x] if hue else [x], observed=True).ngroups)
        long = max((len(str(v)) for v in df[x].dropna().unique()), default=0) + (
            max((len(str(v)) for v in df[hue].dropna().unique()), default=0) + 2 if hue else 0
        )
    rotate = n_ticks > 6 or long > 12
    lines.append('plt.xticks(rotation=45, ha="right")' if rotate else "plt.xticks(rotation=0)")
    lines += ["plt.tight_layout()", "plt.show()"]
    code = "\n".join(lines)

    ns = {"df": df, "pd": pd, "np": np, "plt": plt, "sns": sns}
    exec(code.replace("plt.tight_layout()\nplt.show()", ""), ns)
    fig = ns["fig"]
    fig.set_layout_engine("tight", pad=1.5)
    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt", "import pandas as pd", "import seaborn as sns"],
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
        if _rotate(df, x_cat):
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
        if _rotate(df, x_cat):
            plt.xticks(rotation=45, ha="right")
        fig.set_layout_engine("tight", pad=1.5)

        code = (
            f'fig, ax = plt.subplots(figsize=(10, 6))\n'
            f'sns.stripplot(data=df, x="{x_cat}", y="{y_num}", alpha=0.5, jitter=True{hue_str}, ax=ax)\n'
            f'{AXES_CODE if hue else ""}'
            f'ax.set_title("{y_num} by {x_cat}")\n'
            f'{ROTATE_AX_CODE if _rotate(df, x_cat) else ""}'
            f'plt.tight_layout()\n'
            f'plt.show()'
        )

    return fig, CodeSnippet(
        code=code,
        imports=["import matplotlib.pyplot as plt", "import seaborn as sns"],
    )
