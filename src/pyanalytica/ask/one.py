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
    if median and abs(mean - median) / (abs(median) + 1e-12) > 0.1:
        shape = (
            " The mean sits above the median, so a tail of high values pulls it up."
            if mean > median else
            " The mean sits below the median, so a tail of low values pulls it down."
        )
    else:
        shape = " Mean and median are close, so the values are roughly symmetric."
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
        title="Another picture",
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
        title="Another picture",
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
