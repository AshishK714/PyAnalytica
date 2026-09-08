"""Cross-tabulation with chi-square test."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from scipy import stats

from pyanalytica.core.codegen import CodeSnippet


@dataclass
class CrosstabResult:
    """Result of a cross-tabulation with chi-square test."""
    table: pd.DataFrame
    chi2: float | None
    p_value: float | None
    dof: int | None
    expected: pd.DataFrame | None
    interpretation: str
    code: CodeSnippet


def _index_expr(names: list[str]) -> str:
    """How the shown code names one axis: a Series, or a list of them."""
    if len(names) == 1:
        return f'df["{names[0]}"]'
    inner = ", ".join(f'df["{n}"]' for n in names)
    return f"[{inner}]"


def _as_list(value: "str | list[str] | tuple[str, ...] | None") -> list[str]:
    """One name or several, always as a list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [v for v in value if v]


def _frames(df: pd.DataFrame, names: list[str]) -> "pd.Series | list[pd.Series]":
    """What pandas wants: a Series for one name, a list of them for several."""
    return df[names[0]] if len(names) == 1 else [df[n] for n in names]


def create_crosstab(
    df: pd.DataFrame,
    row_var: "str | list[str]",
    col_var: "str | list[str] | None" = None,
    normalize: str | None = None,
    margins: bool = True,
) -> CrosstabResult:
    """Create a cross-tabulation with chi-square test of independence.

    normalize: None, 'index' (row %), 'columns' (col %), 'all' (total %)
    When col_var is None, produces a simple frequency table.

    Either axis may name more than one column, which is what nests a table --
    job within channel, say. pandas takes a list on either side; the panel used
    to offer only one name.
    """
    rows = _as_list(row_var)
    cols = _as_list(col_var)
    if not rows:
        raise ValueError("Choose at least one row variable to tabulate.")
    row_label = " / ".join(rows)
    col_label = " / ".join(cols)
    if not cols:
        # Simple frequency table. Counting across several columns is a groupby;
        # value_counts is the one-column case of the same thing.
        nested = len(rows) > 1
        if nested:
            sizes = df.groupby(rows, observed=True).size().sort_index()
            source = f'df.groupby({rows!r}, observed=True).size().sort_index()'
        else:
            sizes = df[rows[0]].value_counts().sort_index()
            source = f'df["{rows[0]}"].value_counts().sort_index()'

        if normalize:
            counts = sizes / sizes.sum()
            table = counts.to_frame(name="Percent")
            table["Percent"] = (table["Percent"] * 100).round(1)
            code = f"counts = {source}\nresult = counts / counts.sum() * 100"
        else:
            counts = sizes
            table = counts.to_frame(name="Count")
            code = f"result = {source}"

        if margins:
            col_name = table.columns[0]
            total = table[col_name].sum()
            total_row = pd.DataFrame({col_name: [total]}, index=["Total"])
            table = pd.concat([table, total_row])

        n_cats = len(counts)
        interpretation = f"Frequency table for {row_label} ({n_cats} categories)"

        return CrosstabResult(
            table=table,
            chi2=None,
            p_value=None,
            dof=None,
            expected=None,
            interpretation=interpretation,
            code=CodeSnippet(code=code, imports=["import pandas as pd"]),
        )

    # Two-variable cross-tabulation
    # Raw counts (without margins for chi-square)
    ct_raw = pd.crosstab(_frames(df, rows), _frames(df, cols))

    # Chi-square test
    chi2, p_value, dof, expected = stats.chi2_contingency(ct_raw)
    expected_df = pd.DataFrame(
        expected, index=ct_raw.index, columns=ct_raw.columns
    ).round(1)

    # Display table (with margins and normalization)
    ct_display = pd.crosstab(
        _frames(df, rows), _frames(df, cols),
        margins=margins,
        normalize=normalize if normalize else False,
    )

    if normalize:
        ct_display = (ct_display * 100).round(1)

    # Interpretation
    if p_value < 0.001:
        p_str = "p < .001"
    elif p_value < 0.01:
        p_str = f"p = {p_value:.3f}"
    else:
        p_str = f"p = {p_value:.3f}"

    if p_value < 0.05:
        interpretation = (
            f"There is a statistically significant association between "
            f"{row_var} and {col_var}, \u03c7\u00b2({dof}) = {chi2:.1f}, {p_str}."
        )
    else:
        interpretation = (
            f"There is no statistically significant association between "
            f"{row_var} and {col_var}, \u03c7\u00b2({dof}) = {chi2:.1f}, {p_str}."
        )

    # Code generation
    norm_str = ""
    if normalize:
        norm_str = f', normalize="{normalize}"'
    margins_str = f", margins={margins}" if margins else ""

    code = (
        f'ct = pd.crosstab({_index_expr(rows)}, {_index_expr(cols)}'
        f'{margins_str}{norm_str})\n'
        f'chi2, p, dof, expected = stats.chi2_contingency(\n'
        f'    pd.crosstab({_index_expr(rows)}, {_index_expr(cols)})\n'
        f')\n'
        f'print(f"Chi-square: {{chi2:.2f}}, p-value: {{p:.4f}}, df: {{dof}}")'
    )

    return CrosstabResult(
        table=ct_display,
        chi2=round(chi2, 2),
        p_value=round(p_value, 4),
        dof=dof,
        expected=expected_df,
        interpretation=interpretation,
        code=CodeSnippet(
            code=code,
            imports=["import pandas as pd", "from scipy import stats"],
        ),
    )
