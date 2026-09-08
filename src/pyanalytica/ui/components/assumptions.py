"""Turn an assumption-check dict into something a student can read.

The panel used to print the dictionary:

    normality_shapiro_stat: 0.6365
    normality_shapiro_p: 0.0
    normality_ok: False
    n: 891

Three faults in four lines. The keys are internal names in snake_case. The
p-value of 1e-16 prints as `0.0`, which says the probability is zero. And
`normality_ok: False` sits under a headline announcing a significant result
with nothing to say whether the violation changes it -- which, at this n, it
does not: the t-test is robust to non-normality once the sample is large, and
the normality test is *more* likely to reject the larger the sample gets.

So each line says what was tested, what came back, and what follows.
"""

from __future__ import annotations

import math
import re

#: Above this, a mean is near-normal by the central limit theorem whatever the
#: underlying distribution looks like, so a failed normality test stops being a
#: reason to avoid a t-test.
CLT_COMFORTABLE_N = 30


def _p(value: float) -> str:
    """A p-value that never claims to be zero."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(v):
        return "not available"
    return "p < .0001" if v < 0.0001 else f"p = {v:.4f}"


def _significant(value) -> bool:
    try:
        return float(value) < 0.05
    except (TypeError, ValueError):
        return False


def assumption_lines(
    checks: dict, n: int | None = None, test_name: str = ""
) -> list[str]:
    """One readable sentence per assumption the test makes.

    *test_name* matters because the tests do different things about a
    failed equal-variance check: the two-sample t-test switches to Welch's,
    while one-way ANOVA uses scipy's f_oneway, which assumes equal spread
    and does not correct for its absence. Saying 'Welch's correction is
    used' under an ANOVA would be a comforting sentence that is not true.
    """
    if not checks:
        return []

    lines: list[str] = []
    n = n if n is not None else checks.get("n")

    if "levene_p" in checks:
        p = checks["levene_p"]
        corrects = "t-test" in test_name.lower()
        if _significant(p) and corrects:
            lines.append(
                f"Equal spread across groups: rejected by Levene's test "
                f"({_p(p)}). Welch's correction is applied, which is why the "
                f"degrees of freedom are not a whole number."
            )
        elif _significant(p):
            lines.append(
                f"Equal spread across groups: rejected by Levene's test "
                f"({_p(p)}). This test assumes equal spread and does not "
                f"correct for its absence, so the p-value above is optimistic "
                f"-- especially if the groups differ in size. Kruskal-Wallis "
                f"makes no such assumption."
            )
        else:
            lines.append(
                f"Equal spread across groups: no evidence against it "
                f"({_p(p)}, Levene's test)."
            )

    # Shapiro-Wilk, either for the whole column or per group.
    normality = [
        (key, value) for key, value in checks.items()
        if key.endswith("_p") and "shapiro" in key
    ]
    for key, p in normality:
        group = re.sub(r"^(normality_)?shapiro_?", "", key[: -len("_p")]).strip("_")
        label = f"Normality of {group}" if group else "Normality"
        if _significant(p):
            lines.append(f"{label}: rejected ({_p(p)}, Shapiro-Wilk).")
        else:
            lines.append(f"{label}: no evidence against it ({_p(p)}, Shapiro-Wilk).")

    rejected_normality = any(_significant(p) for _, p in normality)
    if rejected_normality and n and n >= CLT_COMFORTABLE_N:
        lines.append(
            f"With {int(n):,} values that is not a reason to abandon the test: "
            f"the mean of a large sample is near-normal whatever the data look "
            f"like, and a normality test rejects ever more readily as the "
            f"sample grows. Read a histogram before deciding."
        )
    elif rejected_normality and n:
        lines.append(
            f"With only {int(n):,} values this one is worth taking seriously -- "
            f"consider Mann-Whitney or Kruskal-Wallis instead."
        )

    if n is not None:
        lines.append(f"Based on {int(n):,} values.")

    # Anything the rules above did not recognise, rather than dropping it.
    known = {"n", "levene_stat", "levene_p", "equal_variance", "normality_ok"}
    for key, value in checks.items():
        if key in known or key.endswith("_p") and "shapiro" in key:
            continue
        if key.endswith("_stat"):
            continue
        lines.append(f"{key.replace('_', ' ')}: {value}")

    return lines
