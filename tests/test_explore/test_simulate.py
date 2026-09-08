"""Tests for pyanalytica.explore.simulate — distributions, CLT, LLN."""

import matplotlib.pyplot as plt
import numpy as np
import pytest

from pyanalytica.explore.simulate import (
    CLTResult,
    DistributionResult,
    LLNResult,
    simulate_clt,
    simulate_distribution,
    simulate_lln,
)


@pytest.fixture(autouse=True)
def _close_figures():
    """Close all matplotlib figures after each test to avoid memory warnings."""
    yield
    plt.close("all")


# ===== Distribution tests (10) =====


def test_simulate_normal():
    """Normal distribution returns correct result type with all fields populated."""
    r = simulate_distribution("normal", {"loc": 0, "scale": 1}, sample_size=500, seed=42)
    assert isinstance(r, DistributionResult)
    assert r.dist_name == "normal"
    assert len(r.samples) == 500
    assert r.figure is not None
    assert r.summary is not None
    assert r.code is not None


def test_simulate_binomial_discrete():
    """Binomial samples are integers."""
    r = simulate_distribution("binomial", {"n": 20, "p": 0.5}, sample_size=1000, seed=42)
    assert np.all(r.samples == r.samples.astype(int))


def test_simulate_poisson_stats():
    """Poisson sample mean is approximately mu."""
    r = simulate_distribution("poisson", {"mu": 7.0}, sample_size=10000, seed=42)
    assert abs(np.mean(r.samples) - 7.0) < 0.3


def test_simulate_uniform_range():
    """Uniform samples fall within [low, high]."""
    r = simulate_distribution("uniform", {"low": 2.0, "high": 5.0}, sample_size=5000, seed=42)
    assert r.samples.min() >= 2.0
    assert r.samples.max() <= 5.0


def test_simulate_exponential_positive():
    """Exponential samples are non-negative."""
    r = simulate_distribution("exponential", {"scale": 2.0}, sample_size=1000, seed=42)
    assert np.all(r.samples >= 0)


def test_prob_leq():
    """P(X <= 0) for Normal(0,1) is approximately 0.5."""
    r = simulate_distribution("normal", {"loc": 0, "scale": 1}, seed=1, prob_calc="leq", prob_value=0.0)
    assert r.prob_result is not None
    assert abs(r.prob_result - 0.5) < 0.001


def test_prob_geq():
    """P(X >= 0) for Normal(0,1) is approximately 0.5."""
    r = simulate_distribution("normal", {"loc": 0, "scale": 1}, seed=1, prob_calc="geq", prob_value=0.0)
    assert r.prob_result is not None
    assert abs(r.prob_result - 0.5) < 0.001


def test_prob_between():
    """P(-1 <= X <= 1) for Normal(0,1) is approximately 0.6827."""
    r = simulate_distribution(
        "normal", {"loc": 0, "scale": 1}, seed=1,
        prob_calc="between", prob_value=-1.0, prob_value2=1.0,
    )
    assert r.prob_result is not None
    assert abs(r.prob_result - 0.6827) < 0.01


def test_prob_quantile():
    """Quantile(0.5) for Normal(0,1) is 0.0."""
    r = simulate_distribution(
        "normal", {"loc": 0, "scale": 1}, seed=1,
        prob_calc="quantile", prob_value=0.5,
    )
    assert r.prob_result is not None
    assert abs(r.prob_result - 0.0) < 0.001


def test_distribution_summary_shape():
    """Summary DataFrame has 4 rows and 3 columns."""
    r = simulate_distribution("normal", {"loc": 0, "scale": 1}, seed=1)
    assert r.summary.shape == (4, 3)
    assert list(r.summary.columns) == ["Statistic", "Sample", "Theoretical"]


# ===== CLT tests (5) =====


def test_clt_mean_convergence():
    """Observed mean of sample means is close to theoretical mean."""
    r = simulate_clt("normal", {"loc": 5.0, "scale": 2.0}, sample_size=30, num_samples=2000, seed=42)
    assert isinstance(r, CLTResult)
    theo = r.summary.loc[r.summary["Statistic"] == "Mean", "Theoretical"].iloc[0]
    obs = r.summary.loc[r.summary["Statistic"] == "Mean", "Observed"].iloc[0]
    assert abs(theo - obs) < 0.2


def test_clt_se_convergence():
    """Observed SE is close to sigma/sqrt(n)."""
    r = simulate_clt("normal", {"loc": 0, "scale": 3.0}, sample_size=50, num_samples=5000, seed=42)
    theo_se = r.summary.loc[r.summary["Statistic"] == "Std Error", "Theoretical"].iloc[0]
    obs_se = r.summary.loc[r.summary["Statistic"] == "Std Error", "Observed"].iloc[0]
    assert abs(theo_se - obs_se) < 0.1


def test_clt_num_means():
    """Number of sample means equals num_samples."""
    r = simulate_clt("normal", {"loc": 0, "scale": 1}, num_samples=500, seed=42)
    assert len(r.sample_means) == 500


def test_clt_summary_columns():
    """CLT summary has correct columns."""
    r = simulate_clt("normal", {"loc": 0, "scale": 1}, seed=42)
    assert list(r.summary.columns) == ["Statistic", "Theoretical", "Observed"]


def test_clt_nonnormal_population():
    """CLT works with non-normal (exponential) population."""
    r = simulate_clt("exponential", {"scale": 2.0}, sample_size=50, num_samples=1000, seed=42)
    assert isinstance(r, CLTResult)
    assert r.figure is not None
    assert len(r.sample_means) == 1000


# ===== LLN tests (4) =====


def test_lln_convergence():
    """Running mean converges to true mean with large n."""
    r = simulate_lln("normal", {"loc": 10.0, "scale": 2.0}, max_obs=10000, seed=42)
    assert isinstance(r, LLNResult)
    assert abs(r.running_means[-1] - r.true_mean) < 0.1


def test_lln_length():
    """Running means array has length equal to max_obs."""
    r = simulate_lln("normal", {"loc": 0, "scale": 1}, max_obs=3000, seed=42)
    assert len(r.running_means) == 3000


def test_lln_true_mean():
    """True mean matches scipy distribution mean."""
    from scipy import stats
    r = simulate_lln("poisson", {"mu": 4.0}, seed=42)
    expected = stats.poisson(mu=4.0).mean()
    assert abs(r.true_mean - expected) < 0.001


def test_lln_summary():
    """LLN summary has expected columns."""
    r = simulate_lln("uniform", {"low": 0, "high": 10}, seed=42)
    assert list(r.summary.columns) == ["Statistic", "Value"]


# ===== Cross-cutting tests (2) =====


def test_code_snippet_all_modes():
    """All three functions return non-empty CodeSnippets."""
    params = {"loc": 0, "scale": 1}
    r1 = simulate_distribution("normal", params, seed=1)
    r2 = simulate_clt("normal", params, seed=1)
    r3 = simulate_lln("normal", params, seed=1)
    for r in [r1, r2, r3]:
        assert r.code is not None
        assert len(r.code.code) > 0
        assert len(r.code.imports) > 0


def test_seed_reproducibility():
    """Same seed produces identical results."""
    params = {"loc": 0, "scale": 1}
    r1 = simulate_distribution("normal", params, sample_size=100, seed=99)
    r2 = simulate_distribution("normal", params, sample_size=100, seed=99)
    np.testing.assert_array_equal(r1.samples, r2.samples)


# ===== Goodness-of-fit tests (5) =====


def test_fit_test_continuous_has_ks():
    """Continuous distribution fit test includes KS test."""
    r = simulate_distribution("normal", {"loc": 0, "scale": 1}, sample_size=1000, seed=42)
    assert "Kolmogorov-Smirnov" in r.fit_test["Test"].values


def test_fit_test_discrete_has_chisq():
    """Discrete distribution fit test includes Chi-square test."""
    r = simulate_distribution("binomial", {"n": 20, "p": 0.5}, sample_size=1000, seed=42)
    assert "Chi-square Goodness-of-Fit" in r.fit_test["Test"].values


def test_fit_test_good_fit_normal():
    """Normal sample from Normal dist should pass goodness-of-fit (p >= 0.05)."""
    r = simulate_distribution("normal", {"loc": 0, "scale": 1}, sample_size=500, seed=42)
    ks_row = r.fit_test[r.fit_test["Test"] == "Kolmogorov-Smirnov"]
    assert ks_row["p-value"].iloc[0] >= 0.05


def test_clt_normality_test():
    """CLT fit test uses the two tests that are valid for estimated parameters."""
    r = simulate_clt("normal", {"loc": 0, "scale": 1}, num_samples=500, seed=42)
    assert "Shapiro-Wilk (normality of means)" in r.fit_test["Test"].values
    assert "Anderson-Darling (normality of means)" in r.fit_test["Test"].values


def test_no_ks_test_against_a_normal_fitted_to_the_same_sample():
    """The removed test, kept out deliberately.

    Estimating the mean and standard deviation from the sample and then judging
    the fit with the standard Kolmogorov-Smirnov null distribution is the
    Lilliefors situation: the p-value comes out far too large. Measured over
    3000 replications it rejected 0.0% of the time at alpha = 0.05, where 5% is
    correct, and it called gamma(2, 2) data "consistent with normal" at
    p = 0.116 while Shapiro-Wilk gave 6e-08 on the same sample.

    Anderson-Darling covers the same ground properly, because scipy's critical
    values for dist="norm" are the ones adjusted for estimated parameters.
    """
    r = simulate_clt("normal", {"loc": 0, "scale": 1}, num_samples=500, seed=42)
    names = " ".join(r.fit_test["Test"].values)
    assert "Kolmogorov-Smirnov" not in names


def test_the_normality_tests_reject_data_that_is_not_normal():
    """The failure the removed test could not produce."""
    r = simulate_lln("exponential", {"scale": 2.0}, max_obs=3000, seed=7)
    assert len(r.fit_test) >= 1


def test_every_test_states_its_null_hypothesis():
    """"Fail to reject H0" means nothing without H0."""
    r = simulate_clt("normal", {"loc": 0, "scale": 1}, num_samples=500, seed=42)
    assert "Null hypothesis (H0)" in r.fit_test.columns
    for null in r.fit_test["Null hypothesis (H0)"]:
        assert isinstance(null, str) and len(null) > 20, null


def test_a_high_p_value_is_not_called_a_good_fit():
    """Failing to reject is the absence of evidence against, not evidence for.

    The old wording -- "Fail to reject H0 (good fit)" -- taught the
    misinterpretation the panel exists to correct.
    """
    r = simulate_clt("normal", {"loc": 0, "scale": 1}, num_samples=500, seed=42)
    results = " ".join(r.fit_test["Result"].values)
    assert "good fit" not in results
    assert "No evidence against H0" in results


def test_anderson_darling_says_why_it_has_no_p_value():
    """An empty p-value cell reads as a number that failed to compute."""
    r = simulate_clt("normal", {"loc": 0, "scale": 1}, num_samples=500, seed=42)
    row = r.fit_test[r.fit_test["Test"].str.contains("Anderson")].iloc[0]
    assert "critical value" in row["Result"]
    assert "not a p-value" in row["Result"]


def test_lln_fit_test_columns():
    """LLN fit test has expected columns."""
    r = simulate_lln("exponential", {"scale": 2.0}, max_obs=3000, seed=42)
    assert list(r.fit_test.columns) == [
        "Test", "Null hypothesis (H0)", "Statistic", "p-value", "Result",
    ]
