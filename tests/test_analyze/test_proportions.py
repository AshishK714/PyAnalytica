"""Tests for analyze/proportions.py."""

import pandas as pd
import pytest

from pyanalytica.analyze.proportions import (
    GoodnessOfFitResult, OnePropResult, ProportionsResult, TwoPropResult,
    chi_square_test, goodness_of_fit_test, one_proportion_ztest, two_proportion_ztest,
)


@pytest.fixture
def df():
    return pd.DataFrame({
        "gender": ["M", "F", "M", "F", "M", "F", "M", "F"] * 10,
        "preference": ["A", "B", "A", "A", "B", "B", "A", "B"] * 10,
    })


def test_chi_square_returns_result(df):
    result = chi_square_test(df, "gender", "preference")
    assert isinstance(result, ProportionsResult)
    assert result.chi2 >= 0
    assert 0 <= result.p_value <= 1
    assert result.dof >= 1


def test_chi_square_observed_table(df):
    result = chi_square_test(df, "gender", "preference")
    assert isinstance(result.observed, pd.DataFrame)
    assert result.observed.shape[0] == 2  # M, F
    assert result.observed.shape[1] == 2  # A, B


def test_chi_square_expected_table(df):
    result = chi_square_test(df, "gender", "preference")
    assert isinstance(result.expected, pd.DataFrame)
    assert result.expected.shape == result.observed.shape


def test_chi_square_residuals(df):
    result = chi_square_test(df, "gender", "preference")
    assert isinstance(result.residuals, pd.DataFrame)
    assert result.residuals.shape == result.observed.shape


def test_chi_square_interpretation(df):
    result = chi_square_test(df, "gender", "preference")
    assert "association" in result.interpretation.lower()
    assert "gender" in result.interpretation
    assert "preference" in result.interpretation


def test_chi_square_code_snippet(df):
    result = chi_square_test(df, "gender", "preference")
    assert "crosstab" in result.code.code
    assert "chi2_contingency" in result.code.code


def test_chi_square_significant():
    """Test with data that has a strong association."""
    df = pd.DataFrame({
        "x": ["A"] * 50 + ["B"] * 50,
        "y": ["yes"] * 45 + ["no"] * 5 + ["no"] * 45 + ["yes"] * 5,
    })
    result = chi_square_test(df, "x", "y")
    assert result.p_value < 0.05
    assert "significant" in result.interpretation.lower()


def test_chi_square_not_significant():
    """Test with data that has no association."""
    df = pd.DataFrame({
        "x": ["A", "A", "B", "B"] * 25,
        "y": ["yes", "no", "yes", "no"] * 25,
    })
    result = chi_square_test(df, "x", "y")
    assert "no statistically significant" in result.interpretation.lower()


def test_cramers_v_returned(df):
    result = chi_square_test(df, "gender", "preference")
    assert result.cramers_v is not None
    assert 0 <= result.cramers_v <= 1


def test_cramers_v_strong_association():
    """Strong association should produce high Cramer's V."""
    df = pd.DataFrame({
        "x": ["A"] * 50 + ["B"] * 50,
        "y": ["yes"] * 45 + ["no"] * 5 + ["no"] * 45 + ["yes"] * 5,
    })
    result = chi_square_test(df, "x", "y")
    assert result.cramers_v > 0.3


def test_cramers_v_in_interpretation(df):
    result = chi_square_test(df, "gender", "preference")
    assert "Cramer's V" in result.interpretation


# --- Goodness-of-fit tests ---

@pytest.fixture
def gof_df():
    return pd.DataFrame({
        "color": ["red"] * 30 + ["blue"] * 30 + ["green"] * 30,
    })


def test_gof_uniform(gof_df):
    """Default uniform expected, result fields correct."""
    result = goodness_of_fit_test(gof_df, "color")
    assert isinstance(result, GoodnessOfFitResult)
    assert result.chi2 >= 0
    assert 0 <= result.p_value <= 1
    assert result.dof >= 1


def test_gof_custom_probs(gof_df):
    """User-provided proportions produce correct expected counts."""
    probs = {"blue": 0.5, "green": 0.25, "red": 0.25}
    result = goodness_of_fit_test(gof_df, "color", expected_probs=probs)
    expected_vals = result.table.set_index("Category")["Expected"]
    assert expected_vals["blue"] == pytest.approx(45.0, abs=0.1)
    assert expected_vals["green"] == pytest.approx(22.5, abs=0.1)
    assert expected_vals["red"] == pytest.approx(22.5, abs=0.1)


def test_gof_significant():
    """Data deviating from expected -> p < 0.05."""
    df = pd.DataFrame({"x": ["A"] * 80 + ["B"] * 10 + ["C"] * 10})
    result = goodness_of_fit_test(df, "x")
    assert result.p_value < 0.05
    assert "differs significantly" in result.interpretation


def test_gof_not_significant(gof_df):
    """Data matching expected -> p >= 0.05."""
    result = goodness_of_fit_test(gof_df, "color")
    assert result.p_value >= 0.05
    assert "does not differ significantly" in result.interpretation


def test_gof_result_table(gof_df):
    """Table has correct columns and row count."""
    result = goodness_of_fit_test(gof_df, "color")
    assert list(result.table.columns) == ["Category", "Observed", "Expected", "Residual"]
    assert len(result.table) == 3  # red, blue, green


def test_gof_code_snippet(gof_df):
    """Code contains chisquare."""
    result = goodness_of_fit_test(gof_df, "color")
    assert "chisquare" in result.code.code


def test_gof_interpretation(gof_df):
    """Interpretation text mentions variable name."""
    result = goodness_of_fit_test(gof_df, "color")
    assert "color" in result.interpretation


def test_gof_dof(gof_df):
    """dof = number of categories - 1."""
    result = goodness_of_fit_test(gof_df, "color")
    n_categories = gof_df["color"].nunique()
    assert result.dof == n_categories - 1


# --- One-sample proportion z-test ---

@pytest.fixture
def titanic_df():
    return pd.DataFrame({
        "Survived": [1] * 342 + [0] * 549,
        "Sex": ["female"] * 233 + ["male"] * 109 + ["female"] * 81 + ["male"] * 468,
        "Pclass": [1] * 200 + [2] * 200 + [3] * 491,
    })


def test_one_prop_returns_result(titanic_df):
    result = one_proportion_ztest(titanic_df, "Survived", "1", p0=0.5)
    assert isinstance(result, OnePropResult)
    assert result.z_stat != 0
    assert 0 <= result.p_value <= 1


def test_one_prop_survival_rate(titanic_df):
    """Survival rate ~38.4%, significantly different from 50%."""
    result = one_proportion_ztest(titanic_df, "Survived", "1", p0=0.5)
    assert result.sample_proportion == pytest.approx(342 / 891, abs=0.001)
    assert result.p_value < 0.05


def test_one_prop_not_significant():
    """50/100 successes against p0=0.5 -> not significant."""
    df = pd.DataFrame({"x": ["yes"] * 50 + ["no"] * 50})
    result = one_proportion_ztest(df, "x", "yes", p0=0.5)
    assert result.p_value >= 0.05


def test_one_prop_confidence_interval(titanic_df):
    result = one_proportion_ztest(titanic_df, "Survived", "1", p0=0.5)
    lo, hi = result.confidence_interval
    assert lo < result.sample_proportion < hi
    assert lo > 0
    assert hi < 1


def test_one_prop_summary_table(titanic_df):
    result = one_proportion_ztest(titanic_df, "Survived", "1", p0=0.5)
    assert len(result.summary) == 7
    assert "n" in result.summary["Statistic"].values


def test_one_prop_names_the_level_it_tested(titanic_df):
    """Which level counts as success changes the answer, so it has to be visible."""
    result = one_proportion_ztest(titanic_df, "Survived", "1", p0=0.5)
    assert "Survived = 1" in result.summary["Value"].astype(str).tolist()
    assert result.interpretation.startswith("Testing Survived = 1.")


def test_two_prop_names_the_level_it_tested(titanic_df):
    result = two_proportion_ztest(titanic_df, "Survived", "1", "Sex")
    assert result.interpretation.startswith("Testing Survived = 1.")
    assert "Survived = 1" in result.summary.columns


def test_one_prop_interpretation(titanic_df):
    result = one_proportion_ztest(titanic_df, "Survived", "1", p0=0.5)
    assert "Survived" in result.interpretation
    assert "1" in result.interpretation


def test_one_prop_alternative_less():
    """90/100 with p0=0.5, alt='less' -> not significant (proportion > 0.5)."""
    df = pd.DataFrame({"x": ["yes"] * 90 + ["no"] * 10})
    result = one_proportion_ztest(df, "x", "yes", p0=0.5, alternative="less")
    assert result.p_value > 0.05


def test_one_prop_alternative_greater():
    """90/100 with p0=0.5, alt='greater' -> significant."""
    df = pd.DataFrame({"x": ["yes"] * 90 + ["no"] * 10})
    result = one_proportion_ztest(df, "x", "yes", p0=0.5, alternative="greater")
    assert result.p_value < 0.05


def test_one_prop_code_snippet(titanic_df):
    result = one_proportion_ztest(titanic_df, "Survived", "1", p0=0.5)
    assert "norm.sf" in result.code.code
    assert "Survived" in result.code.code


# --- Two-sample proportion z-test ---

def test_two_prop_returns_result(titanic_df):
    result = two_proportion_ztest(titanic_df, "Survived", "1", "Sex")
    assert isinstance(result, TwoPropResult)
    assert result.z_stat != 0
    assert 0 <= result.p_value <= 1


def test_two_prop_sex_survival(titanic_df):
    """Female vs male survival should be significantly different."""
    result = two_proportion_ztest(titanic_df, "Survived", "1", "Sex")
    assert result.p_value < 0.05
    assert "differs significantly" in result.interpretation


def test_two_prop_no_difference():
    """Equal proportions -> not significant."""
    df = pd.DataFrame({
        "outcome": ["yes"] * 50 + ["no"] * 50 + ["yes"] * 50 + ["no"] * 50,
        "group": ["A"] * 100 + ["B"] * 100,
    })
    result = two_proportion_ztest(df, "outcome", "yes", "group")
    assert result.p_value >= 0.05


def test_two_prop_summary_shape(titanic_df):
    result = two_proportion_ztest(titanic_df, "Survived", "1", "Sex")
    assert len(result.summary) == 2
    assert "Proportion" in result.summary.columns


def test_two_prop_confidence_interval(titanic_df):
    result = two_proportion_ztest(titanic_df, "Survived", "1", "Sex")
    lo, hi = result.confidence_interval
    assert lo < result.diff < hi


def test_two_prop_code_snippet(titanic_df):
    result = two_proportion_ztest(titanic_df, "Survived", "1", "Sex")
    assert "p_pool" in result.code.code
    assert "Sex" in result.code.code


def test_two_prop_requires_two_groups():
    """Should raise ValueError if group_var has != 2 unique values."""
    df = pd.DataFrame({
        "outcome": ["yes", "no"] * 15,
        "group": ["A"] * 10 + ["B"] * 10 + ["C"] * 10,
    })
    with pytest.raises(ValueError, match="exactly 2"):
        two_proportion_ztest(df, "outcome", "yes", "group")


def test_two_prop_alternative_less():
    """Group A has 90% success, Group B has 10%. A < B should not be significant."""
    df = pd.DataFrame({
        "outcome": ["yes"] * 90 + ["no"] * 10 + ["yes"] * 10 + ["no"] * 90,
        "group": ["A"] * 100 + ["B"] * 100,
    })
    result = two_proportion_ztest(df, "outcome", "yes", "group", alternative="less")
    assert result.p_value > 0.05  # A's proportion is HIGHER, not less
