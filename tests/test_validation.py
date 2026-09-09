"""Compare the tool against notebooks written without reading it.

The two halves never meet except through `validation/expected/*.json`: the
notebooks record what they computed under agreed keys, and this file computes
the tool's value for each key and compares. The notebooks do not import
pyanalytica, which is the property that makes the comparison worth anything --
see `validation/SPEC.md`.

Three outcomes, and they mean different things:

  match      the tool and an independent computation agree
  MISMATCH   they do not, and one of them is wrong. A finding either way.
  unmapped   the notebook computed something the tool does not expose. Also a
             finding: it is usually a quantity a student would want.

A mismatch fails. An unmapped key does not -- it is reported, because the
notebook is the reference and the tool having a gap is not the notebook's fault.

Until a notebook exists this file skips, so it is wired into CI from the start
rather than added once there is something to run.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Callable

import pytest

VALIDATION = Path(__file__).resolve().parents[1] / "validation"
EXPECTED = VALIDATION / "expected"


# ---------------------------------------------------------------------------
# What the tool says, per case. Each provider returns {quantity: value} for one
# case in the spec. Writing these needs the source; the notebooks do not.
# ---------------------------------------------------------------------------

def _titanic():
    from pyanalytica.data.load import load_bundled

    df, _ = load_bundled("titanic")
    return df


def _tips():
    from pyanalytica.data.load import load_bundled

    df, _ = load_bundled("tips")
    return df


def _diamonds():
    from pyanalytica.data.load import load_bundled

    df, _ = load_bundled("diamonds")
    return df


def _means_titanic_age_by_sex() -> dict[str, Any]:
    from pyanalytica.analyze.means import two_sample_ttest

    r = two_sample_ttest(_titanic(), "Age", "Sex")
    return {
        "t": r.statistic,
        "p": r.p_value,
        "effect_size": r.effect_size,
        "test_name": r.test_name,
    }


def _means_titanic_age_vs_30() -> dict[str, Any]:
    from pyanalytica.analyze.means import one_sample_ttest

    r = one_sample_ttest(_titanic(), "Age", 30)
    return {"t": r.statistic, "p": r.p_value, "effect_size": r.effect_size}


def _means_titanic_age_by_pclass() -> dict[str, Any]:
    from pyanalytica.analyze.means import one_way_anova

    r = one_way_anova(_titanic(), "Age", "Pclass")
    return {"f": r.statistic, "p": r.p_value, "effect_size": r.effect_size}


def _crosstab_titanic_pclass_survived() -> dict[str, Any]:
    from pyanalytica.explore.crosstab import create_crosstab

    r = create_crosstab(_titanic(), "Pclass", "Survived", margins=False)
    return {
        "chi2": r.chi2,
        "p": r.p_value,
        "dof": r.dof,
        "cramers_v": getattr(r, "cramers_v", None),
    }


def _proportions_titanic_survival_by_sex() -> dict[str, Any]:
    from pyanalytica.analyze.proportions import two_proportion_ztest

    df = _titanic()
    r = two_proportion_ztest(df, "Survived", "1", "Sex")
    return {"z": r.z_stat, "p": r.p_value, "difference": r.diff}


def _correlation_tips_bill_tip() -> dict[str, Any]:
    from pyanalytica.analyze.correlation import correlation_test

    r = correlation_test(_tips(), "total_bill", "tip", method="pearson")
    return {"r": getattr(r, "correlation", None), "p": getattr(r, "p_value", None)}


def _regression_titanic_age() -> dict[str, Any]:
    from pyanalytica.model.regression import linear_regression

    r = linear_regression(_titanic(), "Age", ["Fare", "Pclass"], diagnostics=False)
    coefs = dict(zip(r.coefficients["variable"], r.coefficients["coefficient"]))
    return {
        "r_squared": r.r_squared,
        "adj_r_squared": r.adj_r_squared,
        "f": r.f_stat,
        "f_p": r.f_pvalue,
        "coef_Fare": coefs.get("Fare"),
        "coef_Pclass": coefs.get("Pclass"),
        "intercept": coefs.get("(Intercept)"),
    }


def _regression_titanic_age_split() -> dict[str, Any]:
    from pyanalytica.model.regression import linear_regression

    r = linear_regression(
        _titanic(), "Age", ["Fare", "Pclass"],
        test_size=0.3, random_state=42, diagnostics=False,
    )
    return {"r_squared_train": r.r_squared, "r_squared_test": r.test_r_squared}


def _classification_titanic_survived() -> dict[str, Any]:
    from pyanalytica.model.classify import logistic_regression
    from pyanalytica.model.evaluate import evaluate_classification

    r = logistic_regression(
        _titanic(), "Survived", ["Pclass", "Age", "Fare"],
        test_size=0.3, random_state=42,
    )
    ev = evaluate_classification(
        r.y_test, r.model.predict(r.X_test), r.probabilities
    )
    return {
        "accuracy": ev.accuracy,
        "precision": ev.precision,
        "recall": ev.recall,
        "f1": ev.f1,
        "auc": ev.auc,
        "test_accuracy": r.test_accuracy,
    }


def _clustering_titanic_age_fare() -> dict[str, Any]:
    from pyanalytica.model.cluster import kmeans_cluster

    r = kmeans_cluster(
        _titanic().dropna(subset=["Age"]), ["Age", "Fare"],
        chosen_k=3, diagnostics=False,
    )
    sizes = sorted(int(n) for n in r.labels.value_counts())
    return {"sizes": sizes, "n_clusters": r.n_clusters}


def _pca_titanic() -> dict[str, Any]:
    from pyanalytica.model.reduce import pca_analysis

    r = pca_analysis(
        _titanic().dropna(subset=["Age"]), ["Age", "Fare", "Pclass"],
        diagnostics=False,
    )
    explained = r.explained_variance
    if hasattr(explained, "tolist"):
        explained = explained.tolist()
    return {"explained_variance": [float(v) for v in explained]}


def _normality_diamonds_price() -> dict[str, Any]:
    from pyanalytica.analyze.normality import shapiro_wilk_test

    r = shapiro_wilk_test(_diamonds(), "price")
    return {"statistic": r.statistic, "p": r.p_value, "n": r.n, "n_tested": r.n_tested}


#: case key -> what the tool says about it
PROVIDERS: dict[str, Callable[[], dict[str, Any]]] = {
    "means.titanic_age_by_sex": _means_titanic_age_by_sex,
    "means.titanic_age_vs_30": _means_titanic_age_vs_30,
    "means.titanic_age_by_pclass": _means_titanic_age_by_pclass,
    "crosstab.titanic_pclass_survived": _crosstab_titanic_pclass_survived,
    "proportions.titanic_survival_by_sex": _proportions_titanic_survival_by_sex,
    "correlation.tips_bill_tip": _correlation_tips_bill_tip,
    "regression.titanic_age": _regression_titanic_age,
    "regression.titanic_age_split": _regression_titanic_age_split,
    "classification.titanic_survived": _classification_titanic_survived,
    "clustering.titanic_age_fare": _clustering_titanic_age_fare,
    "pca.titanic": _pca_titanic,
    "normality.diamonds_price": _normality_diamonds_price,
}


# ---------------------------------------------------------------------------

def _sections() -> list[Path]:
    return sorted(EXPECTED.glob("*.json")) if EXPECTED.is_dir() else []


def _close(a: Any, b: Any, tol: float) -> bool:
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y, tol) for x, y in zip(a, b))
    if a is None or b is None:
        return a is b
    if isinstance(a, str) or isinstance(b, str):
        return str(a) == str(b)
    try:
        return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)
    except (TypeError, ValueError):
        return a == b


@pytest.mark.parametrize("path", _sections() or [None], ids=lambda p: p.stem if p else "none")
def test_the_tool_agrees_with_the_notebook(path: Path | None):
    if path is None:
        pytest.skip(
            "no validation notebooks yet -- see validation/SPEC.md. This test is "
            "wired in first so the harness cannot be forgotten once they exist."
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    values: dict[str, dict[str, Any]] = payload["values"]
    notes: dict[str, str] = payload.get("notes", {})

    computed: dict[str, dict[str, Any]] = {}
    mismatches: list[str] = []
    unmapped: list[str] = []

    for key, entry in sorted(values.items()):
        section, _, rest = key.partition(".")
        case, _, quantity = rest.rpartition(".")
        case_key = f"{section}.{case}"

        provider = PROVIDERS.get(case_key)
        if provider is None:
            unmapped.append(f"{key} (no case {case_key!r} in the harness)")
            continue
        if case_key not in computed:
            computed[case_key] = provider()
        actual = computed[case_key]
        if quantity not in actual:
            unmapped.append(f"{key} (the tool exposes no {quantity!r} for this case)")
            continue

        expected = entry["value"]
        if not _close(expected, actual[quantity], entry.get("tol", 1e-6)):
            line = f"{key}: notebook {expected!r}, tool {actual[quantity]!r}"
            if case_key in notes:
                line += f"\n      the notebook noted: {notes[case_key]}"
            mismatches.append(line)

    if unmapped:
        print(f"\n{len(unmapped)} quantity(ies) the tool does not expose:")
        for line in unmapped:
            print(f"  - {line}")

    assert not mismatches, (
        f"{len(mismatches)} value(s) differ from the independent computation. "
        f"The notebook is the reference: do not change it to match.\n  "
        + "\n  ".join(mismatches)
    )


def test_every_provider_runs():
    """A provider that raises would be reported as a mismatch it did not cause."""
    broken = []
    for case_key, provider in PROVIDERS.items():
        try:
            result = provider()
            assert isinstance(result, dict) and result
        except Exception as exc:  # noqa: BLE001 - reporting all of them at once
            broken.append(f"{case_key}: {type(exc).__name__}: {exc}")
    assert not broken, "\n  ".join(broken)


def test_the_notebooks_do_not_read_the_source():
    """The property the whole exercise rests on.

    A notebook that imports pyanalytica is no longer an independent
    computation, and the comparison becomes the tool agreeing with itself.
    """
    notebooks = VALIDATION / "notebooks"
    if not notebooks.is_dir():
        pytest.skip("no notebooks yet")

    offenders = []
    for path in sorted(notebooks.rglob("*.ipynb")):
        text = path.read_text(encoding="utf-8")
        if "pyanalytica" in text:
            offenders.append(path.name)
    assert not offenders, (
        "these notebooks mention pyanalytica, so they are not independent of it: "
        + ", ".join(offenders)
    )
