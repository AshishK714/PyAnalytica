"""Statistical tests for comparing means — t-tests, ANOVA, non-parametric."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from pyanalytica.core.codegen import CodeSnippet


@dataclass
class MeansTestResult:
    """Result of a means comparison test."""
    test_name: str
    statistic: float
    p_value: float
    confidence_interval: tuple[float, float] | None = None
    effect_size: float | None = None
    effect_size_name: str = ""
    group_stats: pd.DataFrame = field(default_factory=pd.DataFrame)
    assumption_checks: dict = field(default_factory=dict)
    interpretation: str = ""
    code: CodeSnippet = field(default_factory=lambda: CodeSnippet(code=""))


def one_sample_ttest(
    df: pd.DataFrame, col: str, mu: float, alternative: str = "two-sided"
) -> MeansTestResult:
    """One-sample t-test: compare sample mean to a hypothesized value.

    alternative: 'two-sided', 'less', or 'greater'
    """
    data = df[col].dropna()
    n = len(data)
    t_stat, p_val = stats.ttest_1samp(data, mu, alternative=alternative)

    se = data.std() / np.sqrt(n)
    if alternative == "two-sided":
        ci = (data.mean() - 1.96 * se, data.mean() + 1.96 * se)
    elif alternative == "less":
        ci = (float("-inf"), data.mean() + 1.645 * se)
    else:  # greater
        ci = (data.mean() - 1.645 * se, float("inf"))

    # Cohen's d
    d = (data.mean() - mu) / data.std()

    # Assumption: normality
    if n >= 8 and n <= 5000:
        shap_stat, shap_p = stats.shapiro(data.sample(min(n, 5000), random_state=42))
    else:
        shap_stat, shap_p = None, None

    group_stats = pd.DataFrame({
        "n": [n],
        "mean": [round(data.mean(), 4)],
        "std": [round(data.std(), 4)],
        "se": [round(se, 4)],
    })

    # Interpretation
    sig = "significantly " if p_val < 0.05 else "not significantly "
    if alternative == "less":
        direction = "lower"
        comparison = "lower than"
    elif alternative == "greater":
        direction = "higher"
        comparison = "higher than"
    else:
        direction = "higher" if data.mean() > mu else "lower"
        comparison = "different from"
    interp = (
        f"The sample mean ({data.mean():.2f}) is {sig}{comparison} "
        f"the hypothesized value ({mu}), t({n-1}) = {t_stat:.2f}, "
        f"{_fmt_p(p_val)}, d = {abs(d):.2f}."
    )

    alt_str = f', alternative="{alternative}"' if alternative != "two-sided" else ""
    code = (
        f'from scipy import stats\n'
        f't_stat, p_val = stats.ttest_1samp(df["{col}"].dropna(), {mu}{alt_str})\n'
        f'print(f"t = {{t_stat:.3f}}, p = {{p_val:.4f}}")'
    )

    return MeansTestResult(
        test_name="One-sample t-test",
        statistic=round(t_stat, 4),
        p_value=round(p_val, 6),
        confidence_interval=(round(ci[0], 4), round(ci[1], 4)),
        effect_size=round(abs(d), 4),
        effect_size_name="Cohen's d",
        group_stats=group_stats,
        assumption_checks={
            "normality_shapiro_stat": round(shap_stat, 4) if shap_stat else None,
            "normality_shapiro_p": round(shap_p, 4) if shap_p else None,
            "normality_ok": shap_p > 0.05 if shap_p else None,
            "n": n,
        },
        interpretation=interp,
        code=CodeSnippet(code=code, imports=["from scipy import stats"]),
    )


def two_sample_ttest(
    df: pd.DataFrame, value_col: str, group_col: str, alternative: str = "two-sided"
) -> MeansTestResult:
    """Two-sample (independent) t-test.

    alternative: 'two-sided', 'less', or 'greater'
    """
    groups = df.groupby(group_col)[value_col].apply(lambda x: x.dropna().tolist())
    if len(groups) != 2:
        raise ValueError(f"Expected 2 groups, got {len(groups)}. Column '{group_col}' has {len(groups)} unique values.")

    g1_name, g2_name = groups.index[0], groups.index[1]
    g1, g2 = np.array(groups.iloc[0]), np.array(groups.iloc[1])

    # Levene's test for equal variances
    lev_stat, lev_p = stats.levene(g1, g2)
    equal_var = lev_p > 0.05

    t_stat, p_val = stats.ttest_ind(g1, g2, equal_var=equal_var, alternative=alternative)

    # Cohen's d
    pooled_std = np.sqrt(((len(g1)-1)*np.std(g1, ddof=1)**2 + (len(g2)-1)*np.std(g2, ddof=1)**2)
                         / (len(g1) + len(g2) - 2))
    d = (np.mean(g1) - np.mean(g2)) / pooled_std if pooled_std > 0 else 0

    # Normality checks
    assumption_checks = {
        "levene_stat": round(lev_stat, 4),
        "levene_p": round(lev_p, 4),
        "equal_variance": equal_var,
    }
    for gname, gdata in [(g1_name, g1), (g2_name, g2)]:
        if 8 <= len(gdata) <= 5000:
            s, p = stats.shapiro(gdata[:5000])
            assumption_checks[f"shapiro_{gname}_stat"] = round(s, 4)
            assumption_checks[f"shapiro_{gname}_p"] = round(p, 4)

    group_stats = pd.DataFrame({
        "group": [g1_name, g2_name],
        "n": [len(g1), len(g2)],
        "mean": [round(np.mean(g1), 4), round(np.mean(g2), 4)],
        "std": [round(np.std(g1, ddof=1), 4), round(np.std(g2, ddof=1), 4)],
    })

    sig = "significantly " if p_val < 0.05 else "not significantly "
    welch = " (Welch's)" if not equal_var else ""
    df_val = len(g1) + len(g2) - 2
    if alternative == "less":
        comparison = "lower than"
    elif alternative == "greater":
        comparison = "higher than"
    else:
        comparison = "different from"
    interp = (
        f"The mean {value_col} for {g1_name} ({np.mean(g1):.2f}) is {sig}"
        f"{comparison} {g2_name} ({np.mean(g2):.2f}), "
        f"t({df_val}) = {t_stat:.2f}{welch}, "
        f"{_fmt_p(p_val)}, d = {abs(d):.2f}."
    )

    eq_str = "True" if equal_var else "False"
    alt_str = f', alternative="{alternative}"' if alternative != "two-sided" else ""
    code = (
        f'from scipy import stats\n'
        f'g1 = df[df["{group_col}"] == "{g1_name}"]["{value_col}"].dropna()\n'
        f'g2 = df[df["{group_col}"] == "{g2_name}"]["{value_col}"].dropna()\n'
        f't_stat, p_val = stats.ttest_ind(g1, g2, equal_var={eq_str}{alt_str})\n'
        f'print(f"t = {{t_stat:.3f}}, p = {{p_val:.4f}}")'
    )

    return MeansTestResult(
        test_name=f"Two-sample t-test{welch}",
        statistic=round(t_stat, 4),
        p_value=round(p_val, 6),
        effect_size=round(abs(d), 4),
        effect_size_name="Cohen's d",
        group_stats=group_stats,
        assumption_checks=assumption_checks,
        interpretation=interp,
        code=CodeSnippet(code=code, imports=["from scipy import stats"]),
    )


def one_way_anova(
    df: pd.DataFrame, value_col: str, group_col: str
) -> MeansTestResult:
    """One-way ANOVA."""
    grouped = df.groupby(group_col)[value_col].apply(lambda x: x.dropna().tolist())
    groups = [np.array(g) for g in grouped]
    group_names = list(grouped.index)

    if len(groups) < 2:
        raise ValueError("ANOVA requires at least 2 groups.")

    f_stat, p_val = stats.f_oneway(*groups)

    # Eta-squared
    grand_mean = df[value_col].dropna().mean()
    ss_between = sum(len(g) * (np.mean(g) - grand_mean)**2 for g in groups)
    ss_total = sum((val - grand_mean)**2 for g in groups for val in g)
    eta_sq = ss_between / ss_total if ss_total > 0 else 0

    # Levene's test
    lev_stat, lev_p = stats.levene(*groups)

    group_stats = pd.DataFrame({
        "group": group_names,
        "n": [len(g) for g in groups],
        "mean": [round(np.mean(g), 4) for g in groups],
        "std": [round(np.std(g, ddof=1), 4) for g in groups],
    })

    k = len(groups)
    n_total = sum(len(g) for g in groups)
    sig = "a statistically significant" if p_val < 0.05 else "no statistically significant"
    interp = (
        f"There is {sig} difference in {value_col} across {group_col} groups, "
        f"F({k-1}, {n_total-k}) = {f_stat:.2f}, {_fmt_p(p_val)}, "
        f"\u03b7\u00b2 = {eta_sq:.3f}."
    )

    code = (
        f'from scipy import stats\n'
        f'groups = [group["{value_col}"].dropna().values '
        f'for _, group in df.groupby("{group_col}")]\n'
        f'f_stat, p_val = stats.f_oneway(*groups)\n'
        f'print(f"F = {{f_stat:.3f}}, p = {{p_val:.4f}}")'
    )

    return MeansTestResult(
        test_name="One-way ANOVA",
        statistic=round(f_stat, 4),
        p_value=round(p_val, 6),
        effect_size=round(eta_sq, 4),
        effect_size_name="Eta-squared",
        group_stats=group_stats,
        assumption_checks={
            "levene_stat": round(lev_stat, 4),
            "levene_p": round(lev_p, 4),
            "equal_variance": lev_p > 0.05,
        },
        interpretation=interp,
        code=CodeSnippet(code=code, imports=["from scipy import stats"]),
    )


def mann_whitney_test(
    df: pd.DataFrame, value_col: str, group_col: str, alternative: str = "two-sided"
) -> MeansTestResult:
    """Mann-Whitney U test (non-parametric alternative to two-sample t-test).

    alternative: 'two-sided', 'less', or 'greater'
    """
    groups = df.groupby(group_col)[value_col].apply(lambda x: x.dropna().tolist())
    if len(groups) != 2:
        raise ValueError(f"Expected 2 groups, got {len(groups)}. Column '{group_col}' has {len(groups)} unique values.")

    g1_name, g2_name = groups.index[0], groups.index[1]
    g1, g2 = np.array(groups.iloc[0]), np.array(groups.iloc[1])

    u_stat, p_val = stats.mannwhitneyu(g1, g2, alternative=alternative)

    # Rank-biserial correlation as effect size
    n1, n2 = len(g1), len(g2)
    r = 1 - (2 * u_stat) / (n1 * n2)

    group_stats = pd.DataFrame({
        "group": [g1_name, g2_name],
        "n": [n1, n2],
        "median": [round(np.median(g1), 4), round(np.median(g2), 4)],
        "mean": [round(np.mean(g1), 4), round(np.mean(g2), 4)],
        "std": [round(np.std(g1, ddof=1), 4), round(np.std(g2, ddof=1), 4)],
    })

    sig = "significantly " if p_val < 0.05 else "not significantly "
    if alternative == "less":
        comparison = "lower than"
    elif alternative == "greater":
        comparison = "higher than"
    else:
        comparison = "different from"
    interp = (
        f"The median {value_col} for {g1_name} ({np.median(g1):.2f}) is {sig}"
        f"{comparison} {g2_name} ({np.median(g2):.2f}), "
        f"U = {u_stat:.1f}, {_fmt_p(p_val)}, r = {abs(r):.2f}."
    )

    alt_str = f', alternative="{alternative}"' if alternative != "two-sided" else ""
    code = (
        f'from scipy import stats\n'
        f'g1 = df[df["{group_col}"] == "{g1_name}"]["{value_col}"].dropna()\n'
        f'g2 = df[df["{group_col}"] == "{g2_name}"]["{value_col}"].dropna()\n'
        f'u_stat, p_val = stats.mannwhitneyu(g1, g2{alt_str})\n'
        f'print(f"U = {{u_stat:.1f}}, p = {{p_val:.4f}}")'
    )

    return MeansTestResult(
        test_name="Mann-Whitney U test",
        statistic=round(u_stat, 4),
        p_value=round(p_val, 6),
        effect_size=round(abs(r), 4),
        effect_size_name="Rank-biserial r",
        group_stats=group_stats,
        interpretation=interp,
        code=CodeSnippet(code=code, imports=["from scipy import stats"]),
    )


def kruskal_wallis_test(
    df: pd.DataFrame, value_col: str, group_col: str
) -> MeansTestResult:
    """Kruskal-Wallis H test (non-parametric alternative to one-way ANOVA)."""
    grouped = df.groupby(group_col)[value_col].apply(lambda x: x.dropna().tolist())
    groups = [np.array(g) for g in grouped]
    group_names = list(grouped.index)

    if len(groups) < 2:
        raise ValueError("Kruskal-Wallis test requires at least 2 groups.")

    h_stat, p_val = stats.kruskal(*groups)

    # Epsilon-squared as effect size
    k = len(groups)
    n_total = sum(len(g) for g in groups)
    eps_sq = (h_stat - k + 1) / (n_total - k) if n_total > k else 0

    group_stats = pd.DataFrame({
        "group": group_names,
        "n": [len(g) for g in groups],
        "median": [round(np.median(g), 4) for g in groups],
        "mean": [round(np.mean(g), 4) for g in groups],
        "std": [round(np.std(g, ddof=1), 4) for g in groups],
    })

    sig = "a statistically significant" if p_val < 0.05 else "no statistically significant"
    interp = (
        f"There is {sig} difference in {value_col} across {group_col} groups, "
        f"H({k-1}) = {h_stat:.2f}, {_fmt_p(p_val)}, "
        f"\u03b5\u00b2 = {eps_sq:.3f}."
    )

    code = (
        f'from scipy import stats\n'
        f'groups = [group["{value_col}"].dropna().values '
        f'for _, group in df.groupby("{group_col}")]\n'
        f'h_stat, p_val = stats.kruskal(*groups)\n'
        f'print(f"H = {{h_stat:.3f}}, p = {{p_val:.4f}}")'
    )

    return MeansTestResult(
        test_name="Kruskal-Wallis H test",
        statistic=round(h_stat, 4),
        p_value=round(p_val, 6),
        effect_size=round(eps_sq, 4),
        effect_size_name="Epsilon-squared",
        group_stats=group_stats,
        interpretation=interp,
        code=CodeSnippet(code=code, imports=["from scipy import stats"]),
    )


def _fmt_p(p: float) -> str:
    if p < 0.001:
        return "p < .001"
    return f"p = {p:.3f}"
