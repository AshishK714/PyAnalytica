"""Relate > Two Variables: how does Y relate to X?

The two column types pick the analysis, the way JMP's "Fit Y by X" does:

| Y        | X        | describe              | picture         | test                 | model              |
|----------|----------|-----------------------|-----------------|----------------------|--------------------|
| number   | category | group means           | boxplots        | t-test or ANOVA      | regression on dummies |
| number   | number   | r, slope              | scatter + line  | correlation test     | fitted line        |
| category | category | row percentages       | grouped bars    | chi-square           | pointer to Classify |
| category | number   | read as number by category, roles swapped, pointer to Classify |

The student never has to know the test's name first; the panel says which it
ran and why.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from pyanalytica.analyze.correlation import correlation_test
from pyanalytica.analyze.means import one_way_anova, two_sample_ttest
from pyanalytica.analyze.proportions import chi_square_test
from pyanalytica.ask._result import (
    AskResult, Rung, combine_code, fmt, reading_sentence, resolve_kind, strength,
)
from pyanalytica.core.codegen import CodeSnippet
from pyanalytica.core.types import MAX_GROUPABLE_LEVELS
from pyanalytica.explore.crosstab import create_crosstab
from pyanalytica.explore.summarize import group_summarize
from pyanalytica.visualize.compare import bar_of_means, grouped_boxplot
from pyanalytica.visualize.distribute import bar_chart
from pyanalytica.visualize.relate import hexbin, scatter


def relate_two(
    df: pd.DataFrame, y: str, x: str,
    treat_y: str = "auto", treat_x: str = "auto",
    color_by: str | None = None,
    *, second_picture: bool = False,
) -> AskResult:
    """Relate Y to X, optionally coloured by a third, categorical column.

    ``color_by`` is the context variable: the same comparison split by a
    category, which is how a two-variable answer is checked for whether it
    holds within groups. ``second_picture`` builds the rung-2 figure; its
    code is always present, the drawing only when the section is open.
    """
    for name in (y, x):
        if name not in df.columns:
            raise ValueError(f'"{name}" is not a column in this dataset. Choose one from the list.')
    if y == x:
        raise ValueError(
            f'Y and X are both "{y}". Choose two different columns, or use '
            f'Describe > One Variable for just one.'
        )

    ky = resolve_kind(df[y], treat_y)
    kx = resolve_kind(df[x], treat_x)
    reading = " ".join([
        reading_sentence(df[y], ky, treat_y, "Y"),
        reading_sentence(df[x], kx, treat_x, "X"),
    ])

    color = color_by or None
    if color:
        if color not in df.columns:
            raise ValueError(f'"{color}" is not a column in this dataset. Choose one from the list.')
        if color in (x, y):
            raise ValueError(
                f'"{color}" is already Y or X. Colour by a third column, or leave it blank.'
            )
        if resolve_kind(df[color], "auto") != "category":
            raise ValueError(
                f'"{color}" is a number with many distinct values, so it cannot colour '
                f'the groups. Colour by a category, or bin it in Data > Transform.'
            )
        if int(df[color].dropna().nunique()) > MAX_GROUPABLE_LEVELS:
            raise ValueError(
                f'"{color}" has too many categories to colour by. Choose one with '
                f'{MAX_GROUPABLE_LEVELS} or fewer.'
            )
        reading += f' Everything is split by "{color}".'

    if ky == "number" and kx == "category":
        return _number_by_category(df, num=y, cat=x, reading=reading, color=color,
                                   second_picture=second_picture, swapped=False)
    if ky == "category" and kx == "number":
        reading += (
            f' A category outcome against a number is read the other way round: '
            f'how {x} differs across the {y} groups.'
        )
        return _number_by_category(df, num=x, cat=y, reading=reading, color=color,
                                   second_picture=second_picture, swapped=True)
    if ky == "number" and kx == "number":
        return _number_by_number(df, y=y, x=x, reading=reading, color=color,
                                 second_picture=second_picture)
    return _category_by_category(df, y=y, x=x, reading=reading, color=color,
                                 second_picture=second_picture)


def _label(index_value) -> str:
    """A group name, whether the index is one level or several."""
    if isinstance(index_value, tuple):
        return ", ".join(str(v) for v in index_value)
    return str(index_value)


# ---------------------------------------------------------------------------
# number by category
# ---------------------------------------------------------------------------

def _number_by_category(
    df: pd.DataFrame, *, num: str, cat: str, reading: str,
    color: str | None, second_picture: bool, swapped: bool,
) -> AskResult:
    levels = int(df[cat].dropna().nunique())
    if levels < 2:
        raise ValueError(f'"{cat}" has only one group, so there is nothing to compare {num} across.')
    if levels > MAX_GROUPABLE_LEVELS:
        raise ValueError(
            f'"{cat}" has {levels} groups, too many to compare one by one. Read it '
            f'as a number, or bin it in Data > Transform.'
        )

    # Rung 1: group summary and boxplots. With a colour the table is two-way
    # and the sentence names the cell, which is the context-variable lesson:
    # the group that costs most may be a group *within* a group.
    groups = [cat, color] if color else [cat]
    table, table_code = group_summarize(df, groups, [num], ["count", "mean", "median", "std"])
    means = df.groupby(groups, observed=True)[num].mean().dropna()
    hi, lo = means.idxmax(), means.idxmin()
    where = " / ".join(groups)
    sentence = (
        f"Mean {num} is highest for {where} = {_label(hi)} ({fmt(means[hi])}) and lowest for "
        f"{where} = {_label(lo)} ({fmt(means[lo])}), a gap of {fmt(means[hi] - means[lo])}."
    )
    fig, box_code = grouped_boxplot(df, cat, num, hue=color)
    answer = Rung(
        title="Describe",
        sentence=sentence,
        table=table,
        figure=fig,
        code=CodeSnippet(
            code=table_code.code + "\n\n" + box_code.code,
            imports=sorted(set(table_code.imports + box_code.imports)),
        ),
    )

    # Rung 2: bar of means
    if second_picture:
        bar_fig, bar_code = bar_of_means(df, cat, num, hue=color)
    else:
        bar_fig, bar_code = None, bar_of_means(df, cat, num, hue=color)[1]
    picture = Rung(
        title="Another picture",
        sentence="One bar per group at its mean, with a 95% confidence interval on each.",
        figure=bar_fig,
        code=bar_code,
    )

    # Rung 3: the test the group count calls for
    try:
        from pyanalytica.ui.components.assumptions import assumption_lines
        result = two_sample_ttest(df, num, cat) if levels == 2 else one_way_anova(df, num, cat)
        n_total = int(result.group_stats["n"].sum()) if "n" in result.group_stats else None
        notes = assumption_lines(result.assumption_checks, n=n_total, test_name=result.test_name)
        if color:
            notes.insert(0, (
                f'The test compares the {cat} groups on their own; "{color}" is not in it. '
                f'Model > Regression can test both together.'
            ))
        why = (
            "Two groups, so a two-sample t-test." if levels == 2
            else f"{levels} groups, so a one-way ANOVA."
        )
        test = Rung(
            title="Test: could the difference be chance?",
            sentence=f"{why} {result.interpretation}",
            table=result.group_stats,
            code=result.code,
            notes=notes,
        )
    except Exception as exc:
        test = Rung(title="Test: could the difference be chance?",
                    sentence=f"Could not run the test: {exc}")

    # Rung 4: the same means as a regression on dummies
    data = df[[num, cat]].dropna()
    dummies = pd.get_dummies(data[cat].astype(str), drop_first=True, dtype=float)
    design = dummies.copy()
    design.insert(0, "intercept", 1.0)
    beta, *_ = np.linalg.lstsq(design.values, data[num].values.astype(float), rcond=None)
    ref = sorted(data[cat].astype(str).unique())[0]
    model_table = pd.DataFrame({"term": design.columns, "coefficient": np.round(beta, 4)})
    model_code = CodeSnippet(
        code=(
            f'data = df[["{num}", "{cat}"]].dropna()\n'
            f'X = pd.get_dummies(data["{cat}"].astype(str), drop_first=True, dtype=float)\n'
            f'X.insert(0, "intercept", 1.0)\n'
            f'beta, *_ = np.linalg.lstsq(X.values, data["{num}"].values, rcond=None)\n'
            f'result = pd.DataFrame({{"term": X.columns, "coefficient": beta}})'
        ),
        imports=["import numpy as np", "import pandas as pd"],
    )
    model_sentence = (
        f"A regression of {num} on {cat} gives the same means as an equation: the "
        f"intercept is the mean for {cat} = {ref}, and each coefficient is how far "
        f"that group's mean sits from it. Model > Regression lets you add more variables."
    )
    if swapped:
        model_sentence += f" To predict {cat} from {num}, use Model > Classify."
    if color:
        model_sentence += f' Adding "{color}" as a second set of dummies is the next step in Model > Regression.'
    model = Rung(title="Model: the same answer as an equation", sentence=model_sentence,
                 table=model_table, code=model_code)

    next_steps = [f"Model > Regression: {num} on {cat} plus other variables."]
    if swapped:
        next_steps.append(f"Model > Classify: predict {cat} from {num} and other variables.")
    next_steps.append(
        "Advanced > Means offers the non-parametric versions (Mann-Whitney, Kruskal-Wallis)."
    )

    by = f", split by {color}" if color else ""
    return AskResult(
        kind="number_by_category",
        question=f"How does {num} differ across {cat}{by}?",
        reading=reading,
        answer=answer, picture=picture, test=test, model=model,
        next_steps=next_steps,
        code=combine_code([answer, picture, test, model]),
        description=f"{num} by {cat}{by}",
    )


# ---------------------------------------------------------------------------
# number by number
# ---------------------------------------------------------------------------

def _number_by_number(
    df: pd.DataFrame, *, y: str, x: str, reading: str, color: str | None,
    second_picture: bool,
) -> AskResult:
    clean = df[[x, y]].dropna()
    n = len(clean)
    if n < 3:
        raise ValueError(
            f'Only {n} rows have both {x} and {y}. At least 3 are needed to relate them.'
        )
    if clean[x].nunique() < 2 or clean[y].nunique() < 2:
        raise ValueError(
            f'One of {x} and {y} never changes, so there is no relationship to find.'
        )

    r = float(clean[x].corr(clean[y]))
    fit = stats.linregress(clean[x], clean[y])
    slope, intercept = float(fit.slope), float(fit.intercept)

    if color:
        # One row per group, then all rows: the context-variable lesson is
        # that r within groups can differ from r overall.
        rows = []
        for level, part in df.groupby(color, observed=True):
            p = part[[x, y]].dropna()
            if len(p) >= 3 and p[x].nunique() > 1:
                res = stats.linregress(p[x], p[y])
                rows.append((str(level), len(p), round(float(res.rvalue), 4),
                             round(float(res.slope), 4), round(float(res.intercept), 4)))
        rows.append(("all", n, round(r, 4), round(slope, 4), round(intercept, 4)))
        table = pd.DataFrame(rows, columns=[color, "n", "Pearson r", "slope", "intercept"])
        table_code = CodeSnippet(
            code=(
                f'rows = []\n'
                f'for level, part in df.groupby("{color}"):\n'
                f'    part = part[["{x}", "{y}"]].dropna()\n'
                f'    slope, intercept = np.polyfit(part["{x}"], part["{y}"], 1)\n'
                f'    rows.append((level, len(part), part["{x}"].corr(part["{y}"]), slope, intercept))\n'
                f'result = pd.DataFrame(rows, columns=["{color}", "n", "r", "slope", "intercept"])'
            ),
            imports=["import numpy as np", "import pandas as pd"],
        )
        within = "; ".join(f"{row[0]}: r = {row[2]:.2f}" for row in rows[:-1])
        sentence = (
            f"Overall r = {r:.2f} across {n:,} rows. Within each {color} group: {within}. "
            f"Where those differ from the overall figure, the group is doing part of the work."
        )
    else:
        table = pd.DataFrame({
            "statistic": ["n", "Pearson r", "r squared", "slope", "intercept"],
            "value": [n, round(r, 4), round(r * r, 4), round(slope, 4), round(intercept, 4)],
        })
        table_code = CodeSnippet(
            code=(
                f'clean = df[["{x}", "{y}"]].dropna()\n'
                f'r = clean["{x}"].corr(clean["{y}"])\n'
                f'slope, intercept = np.polyfit(clean["{x}"], clean["{y}"], 1)\n'
                f'result = pd.DataFrame({{"statistic": ["n", "r", "r_squared", "slope", "intercept"],\n'
                f'                       "value": [len(clean), r, r**2, slope, intercept]}})'
            ),
            imports=["import numpy as np", "import pandas as pd"],
        )
        direction = "positive" if r > 0 else "negative"
        verb = "rises" if slope > 0 else "falls"
        sentence = (
            f"A {strength(r)} {direction} relationship: r = {r:.2f} across {n:,} rows. "
            f"On average {y} {verb} by {fmt(abs(slope))} for each one-unit increase in {x}. "
            f"The line explains {r * r * 100:.0f}% of the variation in {y}."
        )
    fig, scatter_code = scatter(df, x, y, color_by=color, trend_line=True)
    answer = Rung(
        title="Describe",
        sentence=sentence,
        table=table,
        figure=fig,
        code=CodeSnippet(
            code=table_code.code + "\n\n" + scatter_code.code,
            imports=sorted(set(table_code.imports + scatter_code.imports)),
        ),
    )

    if second_picture:
        hex_fig, hex_code = hexbin(df, x, y)
    else:
        hex_fig, hex_code = None, hexbin(df, x, y)[1]
    picture = Rung(
        title="Another picture",
        sentence="A density view: darker cells hold more rows, which a scatter plot hides when points overlap.",
        figure=hex_fig,
        code=hex_code,
    )

    try:
        ct = correlation_test(df, x, y)
        notes = [
            "Pearson's r measures a straight-line relationship. If the scatter "
            "curves, Advanced > Correlation offers Spearman's rank version."
        ]
        if color:
            notes.insert(0, f'The test is for all rows together. The table above gives r within each "{color}" group.')
        test = Rung(
            title="Test: could the relationship be chance?",
            sentence=ct.interpretation,
            table=pd.DataFrame({
                "statistic": ["n", "r", "95% CI low", "95% CI high", "p-value"],
                "value": [ct.n, ct.r, ct.ci_lower, ct.ci_upper, ct.p_value],
            }),
            code=ct.code,
            notes=notes,
        )
    except Exception as exc:
        test = Rung(title="Test: could the relationship be chance?",
                    sentence=f"Could not run the test: {exc}")

    model = Rung(
        title="Model: the same answer as an equation",
        sentence=(
            f"{y} ≈ {fmt(intercept)} + {fmt(slope)} × {x}. That is the line on the "
            f"chart, and it is a one-variable regression. Model > Regression adds more "
            f"variables and checks the residuals."
        ),
        table=pd.DataFrame({
            "term": ["intercept", x],
            "coefficient": [round(intercept, 4), round(slope, 4)],
        }),
        code=CodeSnippet(
            code=(
                f'clean = df[["{x}", "{y}"]].dropna()\n'
                f'slope, intercept = np.polyfit(clean["{x}"], clean["{y}"], 1)\n'
                f'predicted = intercept + slope * clean["{x}"]\n'
                f'result = pd.DataFrame({{"term": ["intercept", "{x}"], "coefficient": [intercept, slope]}})'
            ),
            imports=["import numpy as np", "import pandas as pd"],
        ),
    )

    by = f", split by {color}" if color else ""
    return AskResult(
        kind="number_by_number",
        question=f"How does {y} relate to {x}{by}?",
        reading=reading,
        answer=answer, picture=picture, test=test, model=model,
        next_steps=[
            f"Model > Regression: {y} on {x} plus other variables, with diagnostics.",
            "Colour by a category to see whether the pattern holds within groups."
            if not color else f"Model > Regression with {x} and {color} together separates their effects.",
        ],
        code=combine_code([answer, picture, test, model]),
        description=f"{y} vs {x}{by}",
    )


# ---------------------------------------------------------------------------
# category by category
# ---------------------------------------------------------------------------

def _category_by_category(
    df: pd.DataFrame, *, y: str, x: str, reading: str, color: str | None,
    second_picture: bool,
) -> AskResult:
    for name in (x, y):
        if int(df[name].dropna().nunique()) < 2:
            raise ValueError(f'"{name}" has only one value, so there is nothing to relate.')

    rows = [color, x] if color else x
    ct = create_crosstab(df, rows, col_var=y, normalize="index", margins=False)
    pct = ct.table
    # Which outcome moves most across the groups is the sentence worth saying.
    spread = (pct.max(axis=0) - pct.min(axis=0))
    outcome = spread.idxmax()
    col = pct[outcome]
    where = f"{color} / {x}" if color else x
    sentence = (
        f"The share of {y} = {outcome} ranges from {col.min():.1f}% ({where} = {_label(col.idxmin())}) "
        f"to {col.max():.1f}% ({where} = {_label(col.idxmax())}) across the {where} groups."
    )
    table = pct.reset_index()
    table.columns = [str(c) for c in table.columns]
    rows_expr = f'[df["{color}"], df["{x}"]]' if color else f'df["{x}"]'
    table_code = CodeSnippet(
        code=(
            f'result = pd.crosstab({rows_expr}, df["{y}"], normalize="index") * 100'
        ),
        imports=["import pandas as pd"],
    )
    fig, bar_code = bar_chart(df, x, group_by=y, facet_col=color)
    answer = Rung(
        title="Describe",
        sentence=sentence,
        table=table,
        figure=fig,
        code=CodeSnippet(
            code=table_code.code + "\n\n" + bar_code.code,
            imports=sorted(set(table_code.imports + bar_code.imports)),
        ),
        notes=[f"Each row of the table adds to 100: the percentages are of that {x} group."],
    )

    if second_picture:
        pct_fig, pct_code = bar_chart(df, x, group_by=y, pct=True, facet_col=color)
    else:
        pct_fig, pct_code = None, bar_chart(df, x, group_by=y, pct=True, facet_col=color)[1]
    picture = Rung(
        title="Another picture",
        sentence="The same split as percentages of all rows, so bars can be compared across panels.",
        figure=pct_fig,
        code=pct_code,
    )

    try:
        chi = chi_square_test(df, x, y)
        notes = []
        if color:
            notes.append(
                f'The test is for all rows together; "{color}" is not in it. '
                f'The table above gives the percentages within each {color} group.'
            )
        if (chi.expected.values < 5).any():
            notes.append(
                "Some cells expect fewer than 5 rows, which makes the chi-square "
                "approximation rough. Combine sparse categories in Data > Transform."
            )
        test = Rung(
            title="Test: could the association be chance?",
            sentence=chi.interpretation,
            table=chi.observed.reset_index(),
            code=chi.code,
            notes=notes,
        )
    except Exception as exc:
        test = Rung(title="Test: could the association be chance?",
                    sentence=f"Could not run the test: {exc}")

    model = Rung(
        title="Model: predicting the category",
        sentence=(
            f"A logistic regression predicts {y} from {x} and other variables, and "
            f"gives each group's odds. Model > Classify fits it and scores how well it predicts."
        ),
    )

    by = f", split by {color}" if color else ""
    return AskResult(
        kind="category_by_category",
        question=f"Does {y} depend on {x}{by}?",
        reading=reading,
        answer=answer, picture=picture, test=test, model=model,
        next_steps=[
            f"Relate > Cross-tab shows the same table with margins and column percentages.",
            f"Model > Classify: predict {y} from {x} and other variables.",
        ],
        code=combine_code([answer, picture, test]),
        description=f"{y} by {x}{by}",
    )
