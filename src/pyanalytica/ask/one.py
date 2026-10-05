"""Describe > One Variable: what does one column look like?

A number gets a summary table and a histogram, then a boxplot and a normality
check. A category gets counts and a bar chart, then a percentage view and a
test of whether the categories are equally common.
"""

from __future__ import annotations

import pandas as pd

from pyanalytica.analyze.normality import shapiro_wilk_test
from pyanalytica.analyze.proportions import goodness_of_fit_test
from pyanalytica.ask._result import (
    AskResult, Rung, combine_code, fmt, reading_sentence, resolve_kind,
)
from pyanalytica.core.codegen import CodeSnippet
from pyanalytica.visualize.distribute import bar_chart, boxplot, histogram


def describe_one(
    df: pd.DataFrame, col: str, treat: str = "auto", *, second_picture: bool = False,
) -> AskResult:
    """Describe one column. ``second_picture`` builds the rung-2 figure; its
    code is always there, the drawing only when the section is open."""
    if col not in df.columns:
        raise ValueError(f'"{col}" is not a column in this dataset. Choose one from the list.')
    series = df[col]
    if series.dropna().empty:
        raise ValueError(f'"{col}" is empty: every value is missing, so there is nothing to describe.')

    kind = resolve_kind(series, treat)
    reading = reading_sentence(series, kind, treat, "it")

    if kind == "number":
        return _number(df, col, reading, second_picture)
    return _category(df, col, reading, second_picture)


def _number(df: pd.DataFrame, col: str, reading: str, second_picture: bool) -> AskResult:
    clean = df[col].dropna()
    n_missing = int(df[col].isna().sum())

    # The screen's table and the report's are built by the same steps, so a
    # report reads "statistic / value" and "50% (median)" exactly as the
    # screen does. They differed ("index", no median label) when each was
    # written separately.
    summary = clean.describe().rename(index={"50%": "50% (median)"})
    summary["missing"] = n_missing
    table = summary.rename_axis("statistic").reset_index(name="value")
    table_code = CodeSnippet(
        code=(
            f'summary = df["{col}"].describe().rename(index={{"50%": "50% (median)"}})\n'
            f'summary["missing"] = df["{col}"].isna().sum()\n'
            f'result = summary.rename_axis("statistic").reset_index(name="value")'
        ),
        imports=["import pandas as pd"],
    )

    mean, median = clean.mean(), clean.median()
    shape = shape_sentence(clean)
    sentence = (
        f"{col} ranges from {fmt(clean.min())} to {fmt(clean.max())}, with a median "
        f"of {fmt(median)} and a mean of {fmt(mean)} across {len(clean):,} values"
        f"{f' ({n_missing:,} missing)' if n_missing else ''}.{shape}"
    )

    fig, hist_code = histogram(df, col)
    answer = Rung(
        title="Describe",
        sentence=sentence,
        table=table,
        figure=fig,
        code=CodeSnippet(
            code=table_code.code + "\n\n" + hist_code.code,
            imports=sorted(set(table_code.imports + hist_code.imports)),
        ),
    )

    box_fig, box_code = boxplot(df, col) if second_picture else (None, boxplot(df, col)[1])
    picture = Rung(
        title="Boxplot",
        sentence="A boxplot shows the middle half of the values as the box, and marks any outliers.",
        figure=box_fig,
        code=box_code,
    )

    try:
        nr = shapiro_wilk_test(df, col)
        test = Rung(
            title="Test: is it normal?",
            sentence=nr.interpretation,
            table=pd.DataFrame({
                "statistic": ["n", "W", "p-value", "skewness", "kurtosis"],
                "value": [nr.n, nr.statistic, nr.p_value, nr.skewness, nr.kurtosis],
            }),
            code=nr.code,
            notes=[
                "Normality matters for a t-test on a small sample. With more than "
                "about 30 values the mean is near-normal regardless, so read the "
                "histogram before deciding."
            ],
        )
    except Exception as exc:  # scipy refuses very small or constant samples
        test = Rung(title="Test: is it normal?", sentence=f"Could not run the test: {exc}")

    return AskResult(
        kind="number",
        question=f"What does {col} look like?",
        reading=reading,
        answer=answer,
        picture=picture,
        test=test,
        model=None,
        next_steps=[
            f"To compare {col} across groups, or against another number, use Relate > Two Variables.",
            f"Advanced > Means tests whether the mean of {col} differs from a value you choose.",
        ],
        code=combine_code([answer, picture, test]),
        description=f"Describe {col}",
    )


def _category(df: pd.DataFrame, col: str, reading: str, second_picture: bool) -> AskResult:
    counts = df[col].value_counts()
    n = int(counts.sum())
    table = pd.DataFrame({
        col: counts.index.astype(str),
        "count": counts.values,
        "percent": (counts.values / n * 100).round(1),
    })
    table_code = CodeSnippet(
        code=(
            f'counts = df["{col}"].value_counts()\n'
            f'result = pd.DataFrame({{"count": counts, "percent": (counts / counts.sum() * 100).round(1)}})\n'
            f'result = result.rename_axis("{col}").reset_index()'
        ),
        imports=["import pandas as pd"],
    )

    top, top_n = str(counts.index[0]), int(counts.iloc[0])
    sentence = (
        f"{col} has {len(counts)} categories across {n:,} rows. The most common is "
        f"{top} ({top_n:,} rows, {top_n / n * 100:.1f}%)"
    )
    if len(counts) > 1:
        low, low_n = str(counts.index[-1]), int(counts.iloc[-1])
        sentence += f"; the rarest is {low} ({low_n:,} rows, {low_n / n * 100:.1f}%)"
    sentence += "."

    fig, bar_code = bar_chart(df, col)
    answer = Rung(
        title="Describe",
        sentence=sentence,
        table=table,
        figure=fig,
        code=CodeSnippet(
            code=table_code.code + "\n\n" + bar_code.code,
            imports=sorted(set(table_code.imports + bar_code.imports)),
        ),
    )

    if second_picture:
        pct_fig, pct_code = bar_chart(df, col, orientation="horizontal", pct=True)
    else:
        pct_fig, pct_code = None, bar_chart(df, col, orientation="horizontal", pct=True)[1]
    picture = Rung(
        title="Percentages",
        sentence="The same counts as percentages of all rows.",
        figure=pct_fig,
        code=pct_code,
    )

    try:
        gof = goodness_of_fit_test(df, col)
        test = Rung(
            title="Test: are the categories equally common?",
            sentence=gof.interpretation,
            table=gof.table,
            code=gof.code,
            notes=[
                "This compares the counts with an even split. A significant result "
                "says the categories are not equally common, which the bar chart "
                "usually makes obvious already."
            ],
        )
    except Exception as exc:
        test = Rung(title="Test: are the categories equally common?",
                    sentence=f"Could not run the test: {exc}")

    return AskResult(
        kind="category",
        question=f"How is {col} distributed?",
        reading=reading,
        answer=answer,
        picture=picture,
        test=test,
        model=None,
        next_steps=[
            f"To see how a number differs across these {col} groups, or how {col} "
            f"relates to another category, use Relate > Two Variables.",
            f"Advanced > Proportions tests the share of one {col} value against a value you choose.",
        ],
        code=combine_code([answer, picture, test]),
        description=f"Describe {col}",
    )


def find_peaks(values: pd.Series, min_height: float = 0.2, max_dip: float = 0.6) -> list[float]:
    """Where a smoothed histogram (a kernel density) has separate humps.

    A hump counts if it reaches ``min_height`` of the tallest one, and two
    humps count as separate only if the density between them falls below
    ``max_dip`` of the lower hump. Columns with few distinct values (counts,
    codes) and small samples return [] because a smooth curve says little
    about them.
    """
    import numpy as np
    from scipy.stats import gaussian_kde

    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if len(v) > 5000:
        v = np.random.default_rng(0).choice(v, 5000, replace=False)
    if len(v) < 50 or np.ptp(v) == 0 or len(np.unique(v)) < 10:
        return []
    grid = np.linspace(v.min(), v.max(), 512)
    try:
        d = gaussian_kde(v)(grid)
    except Exception:  # singular data
        return []
    top = d.max()
    tops = [i for i in range(1, len(d) - 1)
            if d[i] >= d[i - 1] and d[i] > d[i + 1] and d[i] >= min_height * top]
    kept: list[int] = []
    for i in tops:
        if kept:
            j = kept[-1]
            if d[j:i + 1].min() > max_dip * min(d[i], d[j]):
                if d[i] > d[j]:
                    kept[-1] = i
                continue
        kept.append(i)
    return [float(grid[i]) for i in kept]


def shape_sentence(clean: pd.Series) -> str:
    """One sentence on the shape: separate peaks, a tail, or roughly symmetric.

    Peaks come first because mean against median cannot see them: two humps
    of different sizes can put the mean near the median.
    """
    peaks = find_peaks(clean)
    if len(peaks) >= 2:
        where = ", ".join(fmt(p) for p in peaks[:-1]) + f" and {fmt(peaks[-1])}"
        return (
            f" The histogram has {len(peaks)} separate peaks, near {where}, so the "
            "values fall into groups and the mean and median describe neither group "
            "well. Look for a column that separates them."
        )
    skew = clean.skew() if len(clean) > 2 else 0.0
    mean, median = clean.mean(), clean.median()
    if pd.notna(skew) and abs(skew) >= 0.5:
        side = "high" if skew > 0 else "low"
        where = "above" if mean > median else "below" if mean < median else "at"
        return (
            f" Skewness is {fmt(skew)}: a tail of {side} values, with the mean "
            f"{where} the median."
        )
    return " Mean and median are close and skewness is small, so the values are roughly symmetric."
