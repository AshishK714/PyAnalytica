"""Normality test — Shapiro-Wilk."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from pyanalytica.core.codegen import CodeSnippet


#: scipy's ceiling for Shapiro-Wilk.
SHAPIRO_MAX_N = 5000


@dataclass
class NormalityResult:
    """Result of a normality test."""
    test_name: str
    statistic: float
    p_value: float
    n: int
    #: How many rows the statistic was actually computed on. Below the frame's
    #: n whenever scipy's 5,000-row limit bites, which is the case the reported
    #: n used to hide.
    n_tested: int
    skewness: float
    kurtosis: float
    is_normal: bool
    interpretation: str
    code: CodeSnippet = field(default_factory=lambda: CodeSnippet(code=""))


def shapiro_wilk_test(df: pd.DataFrame, col: str) -> NormalityResult:
    """Shapiro-Wilk test for normality.

    If n > 5000, a random sample of 5000 is used (scipy limitation).
    """
    data = df[col].dropna().values
    n = len(data)

    if n < 3:
        raise ValueError(f"Shapiro-Wilk test requires at least 3 observations, got {n}.")

    # scipy will not run Shapiro-Wilk above 5,000 observations, so a large
    # column is sampled. Reporting the frame's n against a statistic computed
    # on a subset states a precision the test does not have -- and W and p are
    # both sensitive to n, so it is not a rounding matter.
    if n > SHAPIRO_MAX_N:
        rng = np.random.RandomState(42)
        sample = rng.choice(data, size=SHAPIRO_MAX_N, replace=False)
    else:
        sample = data
    n_tested = len(sample)

    stat, p_val = stats.shapiro(sample)
    skew = float(stats.skew(data))
    kurt = float(stats.kurtosis(data))
    is_normal = bool(p_val > 0.05)

    if is_normal:
        interp = (
            f"The distribution of {col} does not significantly deviate from "
            f"normality (W = {stat:.4f}, p = {_fmt_p(p_val)}). "
            f"Parametric tests (t-test, ANOVA) are appropriate."
        )
    else:
        interp = (
            f"The distribution of {col} significantly deviates from normality "
            f"(W = {stat:.4f}, p = {_fmt_p(p_val)}). "
            f"Consider non-parametric alternatives (Mann-Whitney U, Kruskal-Wallis)."
        )

    if n_tested < n:
        interp += (
            f" Computed on a random sample of {n_tested:,} of the {n:,} values: "
            f"Shapiro-Wilk is not defined above {SHAPIRO_MAX_N:,} observations. "
            f"At this size the test rejects normality for deviations too small "
            f"to matter, so read the skewness and a histogram alongside it."
        )

    if n > SHAPIRO_MAX_N:
        sampling = (
            f'\n# Shapiro-Wilk is undefined above {SHAPIRO_MAX_N:,} rows, so this\n'
            f'# is a random sample of that many -- the same one the panel used.\n'
            f'data = np.random.RandomState(42).choice('
            f'data, size={SHAPIRO_MAX_N}, replace=False)'
        )
    else:
        sampling = ""
    code = (
        f'from scipy import stats\n'
        f'import numpy as np\n'
        f'data = df["{col}"].dropna().values{sampling}\n'
        f'stat, p_val = stats.shapiro(data)\n'
        f'print(f"W = {{stat:.4f}}, p = {{p_val:.4f}}")\n'
        f'print(f"Skewness: {{stats.skew(data):.3f}}, Kurtosis: {{stats.kurtosis(data):.3f}}")'
    )

    return NormalityResult(
        test_name="Shapiro-Wilk test",
        statistic=round(stat, 4),
        p_value=round(p_val, 6),
        n=n,
        n_tested=n_tested,
        skewness=round(skew, 4),
        kurtosis=round(kurt, 4),
        is_normal=is_normal,
        interpretation=interp,
        code=CodeSnippet(code=code, imports=["from scipy import stats"]),
    )


def _fmt_p(p: float) -> str:
    if p < 0.001:
        return "< .001"
    return f"{p:.3f}"
