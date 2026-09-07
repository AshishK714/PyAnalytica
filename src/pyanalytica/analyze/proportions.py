"""Proportion tests — z-tests, chi-square independence, and goodness of fit."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from pyanalytica.core.codegen import CodeSnippet


@dataclass
class ProportionsResult:
    """Result of a chi-square test of independence."""
    chi2: float
    p_value: float
    dof: int
    observed: pd.DataFrame
    expected: pd.DataFrame
    residuals: pd.DataFrame
    interpretation: str
    code: CodeSnippet = field(default_factory=lambda: CodeSnippet(code=""))
    cramers_v: float | None = None


@dataclass
class GoodnessOfFitResult:
    """Result of a chi-square goodness-of-fit test."""
    chi2: float
    p_value: float
    dof: int
    table: pd.DataFrame          # Columns: Category, Observed, Expected, Residual
    interpretation: str
    code: CodeSnippet = field(default_factory=lambda: CodeSnippet(code=""))


@dataclass
class OnePropResult:
    """Result of a one-sample proportion z-test."""
    test_name: str
    z_stat: float
    p_value: float
    sample_proportion: float
    hypothesized_proportion: float
    n: int
    successes: int
    confidence_interval: tuple[float, float]
    summary: pd.DataFrame
    interpretation: str
    code: CodeSnippet = field(default_factory=lambda: CodeSnippet(code=""))


@dataclass
class TwoPropResult:
    """Result of a two-sample proportion z-test."""
    test_name: str
    z_stat: float
    p_value: float
    prop1: float
    prop2: float
    diff: float
    confidence_interval: tuple[float, float]
    summary: pd.DataFrame
    interpretation: str
    code: CodeSnippet = field(default_factory=lambda: CodeSnippet(code=""))


def one_proportion_ztest(
    df: pd.DataFrame,
    variable: str,
    success_value: str,
    p0: float = 0.5,
    alternative: str = "two-sided",
) -> OnePropResult:
    """One-sample proportion z-test: compare observed proportion to a hypothesized value.

    Parameters
    ----------
    df : DataFrame
    variable : str
        Column name (categorical).
    success_value : str
        Which category counts as "success".
    p0 : float
        Hypothesized proportion (default 0.5).
    alternative : str
        'two-sided', 'less', or 'greater'.
    """
    data = df[variable].dropna()
    n = len(data)
    successes = int((data.astype(str) == str(success_value)).sum())
    p_hat = successes / n

    # z-test using normal approximation
    se0 = np.sqrt(p0 * (1 - p0) / n)
    z = (p_hat - p0) / se0

    if alternative == "two-sided":
        p_val = 2 * stats.norm.sf(abs(z))
    elif alternative == "less":
        p_val = stats.norm.cdf(z)
    else:  # greater
        p_val = stats.norm.sf(z)

    # Confidence interval (Wald, always two-sided)
    se_hat = np.sqrt(p_hat * (1 - p_hat) / n)
    ci = (p_hat - 1.96 * se_hat, p_hat + 1.96 * se_hat)

    summary = pd.DataFrame({
        "Statistic": [
            "Success value", "n", "Successes", "Sample Proportion",
            "Hypothesized p0", "z", "p-value",
        ],
        "Value": [
            f"{variable} = {success_value}", n, successes, round(p_hat, 4),
            p0, round(z, 4), round(p_val, 6),
        ],
    })

    p_str = "p < .001" if p_val < 0.001 else f"p = {p_val:.3f}"
    alt_desc = {"two-sided": "not equal to", "less": "less than", "greater": "greater than"}
    if p_val < 0.05:
        interp = (
            f"Testing {variable} = {success_value}. Its proportion ({p_hat:.3f}) is "
            f"significantly {alt_desc[alternative]} {p0}, z = {z:.2f}, {p_str}."
        )
    else:
        interp = (
            f"Testing {variable} = {success_value}. Its proportion ({p_hat:.3f}) is not "
            f"significantly {alt_desc[alternative]} {p0}, z = {z:.2f}, {p_str}."
        )
    interp += f" 95% CI: ({ci[0]:.3f}, {ci[1]:.3f})."

    code = (
        f'from scipy import stats\n'
        f'import numpy as np\n'
        f'data = df["{variable}"].dropna()\n'
        f'n = len(data)\n'
        f'successes = (data.astype(str) == "{success_value}").sum()\n'
        f'p_hat = successes / n\n'
        f'p0 = {p0}\n'
        f'se = np.sqrt(p0 * (1 - p0) / n)\n'
        f'z = (p_hat - p0) / se\n'
        f'p_val = 2 * stats.norm.sf(abs(z))  # two-sided\n'
        f'print(f"z = {{z:.4f}}, p = {{p_val:.4f}}, p_hat = {{p_hat:.4f}}")'
    )

    return OnePropResult(
        test_name="One-Sample Proportion z-Test",
        z_stat=round(float(z), 4),
        p_value=round(float(p_val), 6),
        sample_proportion=round(float(p_hat), 4),
        hypothesized_proportion=p0,
        n=n,
        successes=successes,
        confidence_interval=(round(ci[0], 4), round(ci[1], 4)),
        summary=summary,
        interpretation=interp,
        code=CodeSnippet(code=code, imports=["import numpy as np", "from scipy import stats"]),
    )


def two_proportion_ztest(
    df: pd.DataFrame,
    variable: str,
    success_value: str,
    group_var: str,
    alternative: str = "two-sided",
) -> TwoPropResult:
    """Two-sample proportion z-test: compare proportions across two groups.

    Parameters
    ----------
    df : DataFrame
    variable : str
        Column containing the binary outcome.
    success_value : str
        Which category counts as "success".
    group_var : str
        Column defining the two groups (must have exactly 2 unique values).
    alternative : str
        'two-sided', 'less', or 'greater'.
    """
    data = df[[variable, group_var]].dropna()
    groups = sorted(data[group_var].unique())
    if len(groups) != 2:
        msg = f"group_var '{group_var}' must have exactly 2 unique values, got {len(groups)}"
        raise ValueError(msg)

    g1 = data[data[group_var] == groups[0]][variable].astype(str)
    g2 = data[data[group_var] == groups[1]][variable].astype(str)

    n1, n2 = len(g1), len(g2)
    x1 = int((g1 == str(success_value)).sum())
    x2 = int((g2 == str(success_value)).sum())
    p1 = x1 / n1
    p2 = x2 / n2
    diff = p1 - p2

    # Pooled proportion under H0
    p_pool = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))

    z = diff / se if se > 0 else 0.0

    if alternative == "two-sided":
        p_val = 2 * stats.norm.sf(abs(z))
    elif alternative == "less":
        p_val = stats.norm.cdf(z)
    else:
        p_val = stats.norm.sf(z)

    # CI for difference (unpooled)
    se_diff = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    ci = (diff - 1.96 * se_diff, diff + 1.96 * se_diff)

    summary = pd.DataFrame({
        "Group": [str(groups[0]), str(groups[1])],
        "n": [n1, n2],
        f"{variable} = {success_value}": [x1, x2],
        "Proportion": [round(p1, 4), round(p2, 4)],
    })

    p_str = "p < .001" if p_val < 0.001 else f"p = {p_val:.3f}"
    g1_label, g2_label = str(groups[0]), str(groups[1])
    if p_val < 0.05:
        interp = (
            f"Testing {variable} = {success_value}. Its proportion differs "
            f"significantly between {g1_label} ({p1:.3f}) and {g2_label} ({p2:.3f}), "
            f"z = {z:.2f}, {p_str}."
        )
    else:
        interp = (
            f"Testing {variable} = {success_value}. Its proportion does not differ "
            f"significantly between {g1_label} ({p1:.3f}) and {g2_label} ({p2:.3f}), "
            f"z = {z:.2f}, {p_str}."
        )
    interp += f" Difference: {diff:.3f}, 95% CI: ({ci[0]:.3f}, {ci[1]:.3f})."

    code = (
        f'from scipy import stats\n'
        f'import numpy as np\n'
        f'data = df[["{variable}", "{group_var}"]].dropna()\n'
        f'g1 = data[data["{group_var}"] == "{groups[0]}"]["{variable}"].astype(str)\n'
        f'g2 = data[data["{group_var}"] == "{groups[1]}"]["{variable}"].astype(str)\n'
        f'x1, n1 = (g1 == "{success_value}").sum(), len(g1)\n'
        f'x2, n2 = (g2 == "{success_value}").sum(), len(g2)\n'
        f'p_pool = (x1 + x2) / (n1 + n2)\n'
        f'se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))\n'
        f'z = (x1/n1 - x2/n2) / se\n'
        f'p_val = 2 * stats.norm.sf(abs(z))  # two-sided\n'
        f'print(f"z = {{z:.4f}}, p = {{p_val:.4f}}, p1 = {{x1/n1:.4f}}, p2 = {{x2/n2:.4f}}")'
    )

    return TwoPropResult(
        test_name="Two-Sample Proportion z-Test",
        z_stat=round(float(z), 4),
        p_value=round(float(p_val), 6),
        prop1=round(float(p1), 4),
        prop2=round(float(p2), 4),
        diff=round(float(diff), 4),
        confidence_interval=(round(ci[0], 4), round(ci[1], 4)),
        summary=summary,
        interpretation=interp,
        code=CodeSnippet(code=code, imports=["import numpy as np", "from scipy import stats"]),
    )


def goodness_of_fit_test(
    df: pd.DataFrame,
    variable: str,
    expected_probs: dict[str, float] | None = None,
) -> GoodnessOfFitResult:
    """Chi-square goodness-of-fit test for a single categorical variable."""
    observed = df[variable].value_counts().sort_index()
    categories = observed.index.tolist()
    n = observed.sum()
    k = len(categories)

    if expected_probs is not None:
        expected = np.array([expected_probs.get(str(cat), 0) * n for cat in categories])
    else:
        expected = np.full(k, n / k)

    chi2_stat, p_value = stats.chisquare(f_obs=observed.values, f_exp=expected)

    dof = k - 1

    residuals = (observed.values - expected) / np.sqrt(expected)

    table = pd.DataFrame({
        "Category": categories,
        "Observed": observed.values,
        "Expected": np.round(expected, 2),
        "Residual": np.round(residuals, 2),
    })

    if p_value < 0.001:
        p_str = "p < .001"
    else:
        p_str = f"p = {p_value:.3f}"

    dist_type = "uniform" if expected_probs is None else "specified"
    if p_value < 0.05:
        interp = (
            f"The distribution of {variable} differs significantly from the "
            f"{dist_type} distribution, \u03c7\u00b2({dof}) = {chi2_stat:.1f}, {p_str}."
        )
    else:
        interp = (
            f"The distribution of {variable} does not differ significantly from the "
            f"{dist_type} distribution, \u03c7\u00b2({dof}) = {chi2_stat:.1f}, {p_str}."
        )

    if expected_probs is not None:
        exp_code = f"expected_probs = {expected_probs}\n"
        exp_code += f'n = len(df["{variable}"])\n'
        exp_code += "f_exp = [expected_probs[cat] * n for cat in observed.index]\n"
    else:
        exp_code = "f_exp = None  # uniform distribution\n"

    code = (
        f'from scipy import stats\n'
        f'observed = df["{variable}"].value_counts().sort_index()\n'
        f'{exp_code}'
        f'chi2, p = stats.chisquare(f_obs=observed.values, f_exp={("f_exp" if expected_probs is not None else "None")})\n'
        f'print(f"Chi-square: {{chi2:.2f}}, p-value: {{p:.4f}}, df: {{{dof}}}")'
    )

    return GoodnessOfFitResult(
        chi2=round(float(chi2_stat), 4),
        p_value=round(float(p_value), 6),
        dof=dof,
        table=table,
        interpretation=interp,
        code=CodeSnippet(code=code, imports=["import pandas as pd", "from scipy import stats"]),
    )


def chi_square_test(
    df: pd.DataFrame, row_var: str, col_var: str
) -> ProportionsResult:
    """Chi-square test of independence between two categorical variables."""
    observed = pd.crosstab(df[row_var], df[col_var])

    chi2, p_value, dof, expected = stats.chi2_contingency(observed)

    expected_df = pd.DataFrame(
        expected, index=observed.index, columns=observed.columns
    ).round(2)

    # Standardized residuals
    residuals = ((observed - expected_df) / expected_df.apply(lambda x: x**0.5)).round(2)

    # Cramer's V
    n = observed.values.sum()
    min_dim = min(observed.shape[0] - 1, observed.shape[1] - 1)
    v = float(np.sqrt(chi2 / (n * min_dim))) if min_dim > 0 and n > 0 else None

    # Interpretation
    if p_value < 0.001:
        p_str = "p < .001"
    else:
        p_str = f"p = {p_value:.3f}"

    if p_value < 0.05:
        interp = (
            f"There is a statistically significant association between "
            f"{row_var} and {col_var}, \u03c7\u00b2({dof}) = {chi2:.1f}, {p_str}."
        )
    else:
        interp = (
            f"There is no statistically significant association between "
            f"{row_var} and {col_var}, \u03c7\u00b2({dof}) = {chi2:.1f}, {p_str}."
        )
    if v is not None:
        interp += f" Cramer's V = {v:.3f}."

    code = (
        f'from scipy import stats\n'
        f'observed = pd.crosstab(df["{row_var}"], df["{col_var}"])\n'
        f'chi2, p, dof, expected = stats.chi2_contingency(observed)\n'
        f'print(f"Chi-square: {{chi2:.2f}}, p-value: {{p:.4f}}, df: {{dof}}")'
    )

    return ProportionsResult(
        chi2=round(chi2, 4),
        p_value=round(p_value, 6),
        dof=dof,
        observed=observed,
        expected=expected_df,
        residuals=residuals,
        interpretation=interp,
        code=CodeSnippet(code=code, imports=["import pandas as pd", "from scipy import stats"]),
        cramers_v=round(v, 4) if v is not None else None,
    )
