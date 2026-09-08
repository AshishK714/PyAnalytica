"""Probability distributions, Central Limit Theorem, and Law of Large Numbers simulations."""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings

import numpy as np
import pandas as pd
from scipy import stats

from pyanalytica.core.codegen import CodeSnippet

Figure = matplotlib.figure.Figure

# ---------------------------------------------------------------------------
# Distribution registry
# ---------------------------------------------------------------------------

DISTRIBUTIONS: dict[str, dict] = {
    "normal": {
        "type": "continuous",
        "params": {"loc": ("Mean", 0.0), "scale": ("Std Dev", 1.0)},
        "rv": "X = a continuous measurement (e.g. height, test score, temperature)",
        "description": (
            "The Normal (Gaussian) distribution is the most common continuous "
            "distribution. It is symmetric and bell-shaped, fully described by "
            "its mean and standard deviation. Use it when data clusters around "
            "a central value with symmetric spread — e.g. exam scores, "
            "measurement errors, or biological measurements like height."
        ),
    },
    "binomial": {
        "type": "discrete",
        "params": {"n": ("Trials", 10), "p": ("Probability", 0.5)},
        "rv": "X = number of successes in n independent yes/no trials",
        "description": (
            "The Binomial distribution counts the number of successes in a "
            "fixed number of independent trials, each with the same probability "
            "of success. Use it for questions like: 'Out of 20 coin flips, how "
            "many are heads?' or 'Out of 100 patients, how many respond to treatment?'"
        ),
    },
    "poisson": {
        "type": "discrete",
        "params": {"mu": ("Rate", 5.0)},
        "rv": "X = number of events in a fixed interval of time or space",
        "description": (
            "The Poisson distribution counts the number of events occurring in "
            "a fixed interval when events happen independently at a constant "
            "average rate. Use it for: 'How many emails arrive per hour?', "
            "'How many accidents occur at an intersection per month?', or "
            "'How many typos per page?'"
        ),
    },
    "uniform": {
        "type": "continuous",
        "params": {"low": ("Low", 0.0), "high": ("High", 1.0)},
        "rv": "X = a value equally likely anywhere in the range [low, high]",
        "description": (
            "The Uniform distribution assigns equal probability to all values "
            "in a range. Every outcome is equally likely. Use it for random "
            "number generation, modeling complete uncertainty within bounds, "
            "or situations like 'a bus arrives at a random time within a "
            "10-minute window.'"
        ),
    },
    "exponential": {
        "type": "continuous",
        "params": {"scale": ("Scale (1/lambda)", 1.0)},
        "rv": "X = waiting time until the next event occurs",
        "description": (
            "The Exponential distribution models the time between independent "
            "events that occur at a constant average rate. It is the continuous "
            "counterpart of the Poisson distribution. Use it for: 'How long "
            "until the next customer arrives?', 'How long until a light bulb "
            "burns out?', or 'Time between earthquakes.'"
        ),
    },
}

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DistributionResult:
    dist_name: str
    samples: np.ndarray
    summary: pd.DataFrame
    figure: Figure
    prob_result: float | None
    prob_description: str
    fit_test: pd.DataFrame
    code: CodeSnippet


@dataclass
class CLTResult:
    sample_means: np.ndarray
    summary: pd.DataFrame
    figure: Figure
    interpretation: str
    fit_test: pd.DataFrame
    code: CodeSnippet


@dataclass
class LLNResult:
    running_means: np.ndarray
    true_mean: float
    summary: pd.DataFrame
    figure: Figure
    interpretation: str
    fit_test: pd.DataFrame
    code: CodeSnippet


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SCIPY_MAP = {
    "normal": "norm",
    "binomial": "binom",
    "poisson": "poisson",
    "uniform": "uniform",
    "exponential": "expon",
}


def _get_dist(dist_name: str, params: dict):
    """Return a frozen scipy distribution."""
    scipy_name = _SCIPY_MAP[dist_name]
    dist_cls = getattr(stats, scipy_name)

    if dist_name == "uniform":
        low = params.get("low", 0.0)
        high = params.get("high", 1.0)
        return dist_cls(loc=low, scale=high - low)
    elif dist_name == "binomial":
        return dist_cls(n=int(params["n"]), p=params["p"])
    elif dist_name == "poisson":
        return dist_cls(mu=params["mu"])
    else:
        return dist_cls(**params)


def _param_str(dist_name: str, params: dict) -> str:
    """Build human-readable parameter string for code snippets."""
    if dist_name == "uniform":
        return f'loc={params.get("low", 0.0)}, scale={params.get("high", 1.0) - params.get("low", 0.0)}'
    elif dist_name == "binomial":
        return f'n={int(params["n"])}, p={params["p"]}'
    elif dist_name == "poisson":
        return f'mu={params["mu"]}'
    else:
        return ", ".join(f"{k}={v}" for k, v in params.items())


def _describe(dist) -> str:
    """Name the distribution being tested, the way the sidebar names it."""
    try:
        name = dist.dist.name
        args = ", ".join(f"{v:g}" for v in dist.args) if dist.args else ""
        kwds = ", ".join(f"{k}={v:g}" for k, v in dist.kwds.items())
        shown = ", ".join(part for part in (args, kwds) if part)
        return f"{name}({shown})" if shown else name
    except Exception:
        return "the distribution you specified"


def _verdict(p: float, alpha: float = 0.05) -> str:
    """Say what a p-value licenses, and no more.

    "Fail to reject H0 (good fit)" reads as evidence the distribution matches.
    It is not: it is the absence of evidence against it, and a small sample
    fails to reject almost anything. The distinction is the whole point of the
    panel, so the wording carries it.
    """
    shown = "p < .0001" if p < 0.0001 else f"p = {p:.4f}"
    if p >= alpha:
        return f"No evidence against H0 ({shown})"
    return f"Reject H0 at 5% ({shown})"


def _goodness_of_fit(samples: np.ndarray, dist, is_discrete: bool) -> pd.DataFrame:
    """Run goodness-of-fit tests: KS for continuous, Chi-square for discrete."""
    rows: list[dict] = []

    if is_discrete:
        # Chi-square goodness-of-fit
        n = len(samples)
        lo = int(dist.ppf(0.001))
        hi = int(dist.ppf(0.999))
        all_vals = np.arange(lo, hi + 1)
        expected_probs = dist.pmf(all_vals)
        expected_counts = expected_probs * n
        # Count observed for each value in the range
        observed_counts = np.zeros(len(all_vals), dtype=float)
        unique_vals, unique_counts = np.unique(samples, return_counts=True)
        for v, c in zip(unique_vals, unique_counts):
            idx = int(v) - lo
            if 0 <= idx < len(observed_counts):
                observed_counts[idx] = c
        # Pool bins with expected count < 5 into a tail bin
        mask = expected_counts >= 5
        if mask.sum() < 2:
            mask[:2] = True
        obs = np.append(observed_counts[mask], observed_counts[~mask].sum())
        exp = np.append(expected_counts[mask], expected_counts[~mask].sum())
        # Adjust expected to match observed total (accounts for out-of-range values)
        exp = exp * (obs.sum() / exp.sum())
        # Drop bins where expected is still ~0
        valid = exp > 0.5
        obs, exp = obs[valid], exp[valid]
        chi2_stat, chi2_p = stats.chisquare(obs, f_exp=exp)
        rows.append({
            "Test": "Chi-square Goodness-of-Fit",
            "Null hypothesis (H0)": f"The sample came from {_describe(dist)}",
            "Statistic": float(chi2_stat),
            "p-value": float(chi2_p),
            "Result": _verdict(chi2_p),
        })
    else:
        # Kolmogorov-Smirnov test
        # Valid here, and only here: the null distribution is the one the user
        # specified, with no parameter estimated from the sample being tested.
        ks_stat, ks_p = stats.kstest(samples, dist.cdf)
        rows.append({
            "Test": "Kolmogorov-Smirnov",
            "Null hypothesis (H0)": f"The sample came from {_describe(dist)}",
            "Statistic": float(ks_stat),
            "p-value": float(ks_p),
            "Result": _verdict(ks_p),
        })

    # Anderson-Darling for normality (always useful context)
    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ad_result = stats.anderson(samples, dist="norm")
        # Use the 5% significance level (index 2)
        ad_stat = float(ad_result.statistic)
        ad_cv = float(ad_result.critical_values[2])
        rows.append({
            "Test": "Anderson-Darling (normality)",
            "Null hypothesis (H0)": "The sample came from a normal distribution",
            "Statistic": ad_stat,
            # This test has no p-value: it is judged against tabulated critical
            # values. An empty cell reads as a number that failed to compute, so
            # the Result column says how the call was made instead.
            "p-value": float("nan"),
            "Result": (
                f"{'Reject H0 at 5%' if ad_stat > ad_cv else 'No evidence against H0'}"
                f" -- statistic {ad_stat:.4f} vs 5% critical value {ad_cv:.4f}"
                f" (this test uses critical values, not a p-value)"
            ),
        })
    except Exception:
        pass

    return pd.DataFrame(rows)


def _normality_test(samples: np.ndarray) -> pd.DataFrame:
    """Test whether sample means follow a normal distribution (for CLT)."""
    rows: list[dict] = []

    # Shapiro-Wilk (limited to 5000 observations)
    test_data = samples[:5000] if len(samples) > 5000 else samples
    sw_stat, sw_p = stats.shapiro(test_data)
    rows.append({
        "Test": "Shapiro-Wilk (normality of means)",
        "Null hypothesis (H0)": "The sample means came from a normal distribution",
        "Statistic": float(sw_stat),
        "p-value": float(sw_p),
        "Result": _verdict(sw_p) + (
            f" -- computed on {len(test_data):,} of {len(samples):,} values"
            if len(test_data) < len(samples) else ""
        ),
    })

    # Anderson-Darling, whose critical values for dist="norm" are the ones
    # adjusted for a mean and variance estimated from the sample. A plain KS
    # test against a normal fitted to the same data used to sit here; that is
    # the Lilliefors situation, its p-value is far too large, and over 3000
    # replications it rejected 0.0% of the time where 5% is correct. It called
    # gamma(2, 2) data "consistent with normal" at p = 0.116 while Shapiro-Wilk
    # gave 6e-08 on the same sample, so it has been removed rather than
    # explained away.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ad = stats.anderson(samples, dist="norm")
    ad_stat = float(ad.statistic)
    ad_cv = float(ad.critical_values[2])
    rows.append({
        "Test": "Anderson-Darling (normality of means)",
        "Null hypothesis (H0)": "The sample means came from a normal distribution",
        "Statistic": ad_stat,
        "p-value": float("nan"),
        "Result": (
            f"{'Reject H0 at 5%' if ad_stat > ad_cv else 'No evidence against H0'}"
            f" -- statistic {ad_stat:.4f} vs 5% critical value {ad_cv:.4f}"
            f" (this test uses critical values, not a p-value)"
        ),
    })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def simulate_distribution(
    dist_name: str,
    params: dict,
    sample_size: int = 1000,
    seed: int | None = None,
    prob_calc: str | None = None,
    prob_value: float | None = None,
    prob_value2: float | None = None,
) -> DistributionResult:
    """Sample from a distribution, visualize, and optionally compute a probability.

    Parameters
    ----------
    dist_name : str
        One of the keys in ``DISTRIBUTIONS``.
    params : dict
        Distribution parameters (e.g. ``{"loc": 0, "scale": 1}``).
    sample_size : int
        Number of random draws.
    seed : int | None
        Random seed for reproducibility.
    prob_calc : str | None
        One of ``"leq"``, ``"geq"``, ``"between"``, ``"quantile"``, or ``None``.
    prob_value, prob_value2 : float | None
        Values used for probability calculations.
    """
    rng = np.random.default_rng(seed)
    dist = _get_dist(dist_name, params)
    samples = dist.rvs(size=sample_size, random_state=rng)
    is_discrete = DISTRIBUTIONS[dist_name]["type"] == "discrete"

    # --- Summary statistics ---
    theo_mean = float(dist.mean())
    theo_std = float(dist.std())
    try:
        theo_skew = float(dist.stats(moments="s"))
    except Exception:
        theo_skew = float("nan")
    try:
        theo_kurt = float(dist.stats(moments="k"))
    except Exception:
        theo_kurt = float("nan")

    from scipy.stats import kurtosis as sp_kurt, skew as sp_skew

    summary = pd.DataFrame({
        "Statistic": ["Mean", "Std Dev", "Skewness", "Kurtosis"],
        "Sample": [
            float(np.mean(samples)),
            float(np.std(samples, ddof=1)),
            float(sp_skew(samples)),
            float(sp_kurt(samples)),
        ],
        "Theoretical": [theo_mean, theo_std, theo_skew, theo_kurt],
    })

    # --- Probability calculation ---
    prob_result: float | None = None
    prob_description = ""
    if prob_calc == "leq" and prob_value is not None:
        prob_result = float(dist.cdf(prob_value))
        prob_description = f"P(X <= {prob_value}) = {prob_result:.4f}"
    elif prob_calc == "geq" and prob_value is not None:
        prob_result = float(1 - dist.cdf(prob_value))
        prob_description = f"P(X >= {prob_value}) = {prob_result:.4f}"
    elif prob_calc == "between" and prob_value is not None and prob_value2 is not None:
        prob_result = float(dist.cdf(prob_value2) - dist.cdf(prob_value))
        prob_description = f"P({prob_value} <= X <= {prob_value2}) = {prob_result:.4f}"
    elif prob_calc == "quantile" and prob_value is not None:
        prob_result = float(dist.ppf(prob_value))
        prob_description = f"Quantile({prob_value}) = {prob_result:.4f}"

    # --- Figure ---
    fig, ax = plt.subplots(figsize=(8, 5))
    scipy_name = _SCIPY_MAP[dist_name]

    if is_discrete:
        lo = int(samples.min())
        hi = int(samples.max())
        bins_range = np.arange(lo, hi + 2) - 0.5
        counts, _, _ = ax.hist(samples, bins=bins_range, density=True, alpha=0.6,
                               color="steelblue", edgecolor="white", label="Sample")
        x_vals = np.arange(lo, hi + 1)
        ax.plot(x_vals, dist.pmf(x_vals), "ro-", label="PMF", markersize=5)
    else:
        ax.hist(samples, bins=50, density=True, alpha=0.6,
                color="steelblue", edgecolor="white", label="Sample")
        x_lo = float(dist.ppf(0.001))
        x_hi = float(dist.ppf(0.999))
        x_vals = np.linspace(x_lo, x_hi, 300)
        ax.plot(x_vals, dist.pdf(x_vals), "r-", linewidth=2, label="PDF")

        # Shade probability region
        if prob_calc == "leq" and prob_value is not None:
            x_fill = np.linspace(x_lo, prob_value, 200)
            ax.fill_between(x_fill, dist.pdf(x_fill), alpha=0.3, color="orange", label=prob_description)
        elif prob_calc == "geq" and prob_value is not None:
            x_fill = np.linspace(prob_value, x_hi, 200)
            ax.fill_between(x_fill, dist.pdf(x_fill), alpha=0.3, color="orange", label=prob_description)
        elif prob_calc == "between" and prob_value is not None and prob_value2 is not None:
            x_fill = np.linspace(prob_value, prob_value2, 200)
            ax.fill_between(x_fill, dist.pdf(x_fill), alpha=0.3, color="orange", label=prob_description)

    ax.set_title(f"{dist_name.title()} Distribution (n={sample_size})")
    ax.set_xlabel("Value")
    ax.set_ylabel("Density")
    ax.legend()
    fig.set_layout_engine("tight", pad=1.5)

    # --- Code snippet ---
    seed_str = f"\nrng = np.random.default_rng({seed})" if seed is not None else "\nrng = np.random.default_rng()"
    code_text = (
        f"{seed_str}\n"
        f"dist = stats.{scipy_name}({_param_str(dist_name, params)})\n"
        f"samples = dist.rvs(size={sample_size}, random_state=rng)\n\n"
        f"fig, ax = plt.subplots(figsize=(8, 5))\n"
        f"ax.hist(samples, bins=50, density=True, alpha=0.6, label='Sample')\n"
    )
    if is_discrete:
        code_text += f"x = np.arange(samples.min(), samples.max() + 1)\nax.plot(x, dist.pmf(x), 'ro-', label='PMF')\n"
    else:
        code_text += f"x = np.linspace(dist.ppf(0.001), dist.ppf(0.999), 300)\nax.plot(x, dist.pdf(x), 'r-', lw=2, label='PDF')\n"
    code_text += (
        f"ax.set_title('{dist_name.title()} Distribution')\n"
        f"ax.legend()\nplt.tight_layout()\nplt.show()"
    )

    snippet = CodeSnippet(
        code=code_text.strip(),
        imports=["import numpy as np", "from scipy import stats", "import matplotlib.pyplot as plt"],
    )

    fit_test = _goodness_of_fit(samples, dist, is_discrete)

    return DistributionResult(
        dist_name=dist_name,
        samples=samples,
        summary=summary,
        figure=fig,
        prob_result=prob_result,
        prob_description=prob_description,
        fit_test=fit_test,
        code=snippet,
    )


def simulate_clt(
    dist_name: str,
    params: dict,
    sample_size: int = 30,
    num_samples: int = 1000,
    seed: int | None = None,
) -> CLTResult:
    """Demonstrate the Central Limit Theorem.

    Draw *num_samples* samples each of size *sample_size* from the given
    distribution and plot the distribution of sample means.
    """
    rng = np.random.default_rng(seed)
    dist = _get_dist(dist_name, params)
    scipy_name = _SCIPY_MAP[dist_name]

    all_samples = dist.rvs(size=(num_samples, sample_size), random_state=rng)
    sample_means = all_samples.mean(axis=1)
    one_sample = all_samples[0]  # keep one sample for the population panel
    is_discrete = DISTRIBUTIONS[dist_name]["type"] == "discrete"

    theo_mean = float(dist.mean())
    theo_se = float(dist.std() / np.sqrt(sample_size))
    obs_mean = float(np.mean(sample_means))
    obs_se = float(np.std(sample_means, ddof=1))

    summary = pd.DataFrame({
        "Statistic": ["Mean", "Std Error"],
        "Theoretical": [theo_mean, theo_se],
        "Observed": [obs_mean, obs_se],
    })

    # --- Figure: two panels ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Left panel: one sample from the population
    if is_discrete:
        lo, hi = int(one_sample.min()), int(one_sample.max())
        bins_range = np.arange(lo, hi + 2) - 0.5
        ax1.hist(one_sample, bins=bins_range, density=True, alpha=0.6,
                 color="steelblue", edgecolor="white")
        x_pop = np.arange(lo, hi + 1)
        ax1.plot(x_pop, dist.pmf(x_pop), "ro-", markersize=4, label="PMF")
    else:
        ax1.hist(one_sample, bins=30, density=True, alpha=0.6,
                 color="steelblue", edgecolor="white")
        x_lo = float(dist.ppf(0.001))
        x_hi = float(dist.ppf(0.999))
        x_pop = np.linspace(x_lo, x_hi, 300)
        ax1.plot(x_pop, dist.pdf(x_pop), "r-", linewidth=2, label="PDF")
    ax1.set_title(f"One Sample (n={sample_size})\nfrom {dist_name.title()} population")
    ax1.set_xlabel("Value")
    ax1.set_ylabel("Density")
    ax1.legend(fontsize=8)

    # Right panel: distribution of sample means
    ax2.hist(sample_means, bins=50, density=True, alpha=0.6,
             color="steelblue", edgecolor="white", label="Sample Means")
    x = np.linspace(sample_means.min(), sample_means.max(), 300)
    ax2.plot(x, stats.norm.pdf(x, theo_mean, theo_se), "r-", linewidth=2, label="Normal Approx")
    ax2.axvline(theo_mean, color="green", linestyle="--", label=f"True Mean = {theo_mean:.3f}")
    ax2.set_title(f"Sampling Distribution of Means\n(k={num_samples} samples)")
    ax2.set_xlabel("Sample Mean")
    ax2.set_ylabel("Density")
    ax2.legend(fontsize=8)

    fig.suptitle(f"Central Limit Theorem: {dist_name.title()}", fontsize=13, fontweight="bold")
    fig.set_layout_engine("tight", pad=1.5)

    interpretation = (
        f"The Central Limit Theorem states that the sampling distribution of the mean "
        f"approaches a normal distribution as sample size increases, regardless of the "
        f"population distribution.\n\n"
        f"Population: {dist_name.title()}({_param_str(dist_name, params)})\n"
        f"Sample size (n): {sample_size}, Number of samples (k): {num_samples}\n"
        f"Theoretical mean: {theo_mean:.4f}, Observed mean: {obs_mean:.4f}\n"
        f"Theoretical SE: {theo_se:.4f}, Observed SE: {obs_se:.4f}"
    )

    seed_str = f"\nrng = np.random.default_rng({seed})" if seed is not None else "\nrng = np.random.default_rng()"
    pdf_or_pmf = "pmf" if is_discrete else "pdf"
    code_text = (
        f"{seed_str}\n"
        f"dist = stats.{scipy_name}({_param_str(dist_name, params)})\n"
        f"all_samples = dist.rvs(size=({num_samples}, {sample_size}), random_state=rng)\n"
        f"sample_means = all_samples.mean(axis=1)\n"
        f"one_sample = all_samples[0]\n\n"
        f"fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))\n\n"
        f"# Left: one sample from the population\n"
        f"ax1.hist(one_sample, bins=30, density=True, alpha=0.6)\n"
        f"x_pop = np.linspace(dist.ppf(0.001), dist.ppf(0.999), 300)\n"
        f"ax1.plot(x_pop, dist.{pdf_or_pmf}(x_pop), 'r-', lw=2, label='{pdf_or_pmf.upper()}')\n"
        f"ax1.set_title('One Sample (n={sample_size})')\n"
        f"ax1.legend()\n\n"
        f"# Right: sampling distribution of means\n"
        f"ax2.hist(sample_means, bins=50, density=True, alpha=0.6, label='Sample Means')\n"
        f"x = np.linspace(sample_means.min(), sample_means.max(), 300)\n"
        f"mu, se = dist.mean(), dist.std() / np.sqrt({sample_size})\n"
        f"ax2.plot(x, stats.norm.pdf(x, mu, se), 'r-', lw=2, label='Normal Approx')\n"
        f"ax2.set_title('Sampling Distribution of Means')\n"
        f"ax2.legend()\n\n"
        f"fig.suptitle('Central Limit Theorem: {dist_name.title()}')\n"
        f"plt.tight_layout()\nplt.show()"
    )

    snippet = CodeSnippet(
        code=code_text.strip(),
        imports=["import numpy as np", "from scipy import stats", "import matplotlib.pyplot as plt"],
    )

    fit_test = _normality_test(sample_means)

    return CLTResult(
        sample_means=sample_means,
        summary=summary,
        figure=fig,
        interpretation=interpretation,
        fit_test=fit_test,
        code=snippet,
    )


def simulate_lln(
    dist_name: str,
    params: dict,
    max_obs: int = 5000,
    seed: int | None = None,
) -> LLNResult:
    """Demonstrate the Law of Large Numbers.

    Plot the running cumulative mean as observations increase.
    """
    rng = np.random.default_rng(seed)
    dist = _get_dist(dist_name, params)
    scipy_name = _SCIPY_MAP[dist_name]

    is_discrete = DISTRIBUTIONS[dist_name]["type"] == "discrete"
    samples = dist.rvs(size=max_obs, random_state=rng)
    running_means = np.cumsum(samples) / np.arange(1, max_obs + 1)
    true_mean = float(dist.mean())

    final_mean = float(running_means[-1])
    abs_diff = abs(final_mean - true_mean)

    summary = pd.DataFrame({
        "Statistic": ["True Mean", "Final Running Mean", "Absolute Difference", "Observations"],
        "Value": [true_mean, final_mean, abs_diff, max_obs],
    })

    # --- Figure ---
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(running_means, color="steelblue", linewidth=0.8, label="Running Mean")
    ax.axhline(true_mean, color="red", linestyle="--", linewidth=1.5,
               label=f"True Mean = {true_mean:.3f}")
    ax.set_title(f"LLN: {dist_name.title()} (n={max_obs})")
    ax.set_xlabel("Number of Observations")
    ax.set_ylabel("Running Mean")
    ax.legend()
    fig.set_layout_engine("tight", pad=1.5)

    interpretation = (
        f"The Law of Large Numbers states that as the number of observations increases, "
        f"the sample mean converges to the population mean.\n\n"
        f"Population: {dist_name.title()}({_param_str(dist_name, params)})\n"
        f"True mean: {true_mean:.4f}\n"
        f"Running mean after {max_obs} observations: {final_mean:.4f}\n"
        f"Absolute difference: {abs_diff:.4f}"
    )

    seed_str = f"\nrng = np.random.default_rng({seed})" if seed is not None else "\nrng = np.random.default_rng()"
    code_text = (
        f"{seed_str}\n"
        f"dist = stats.{scipy_name}({_param_str(dist_name, params)})\n"
        f"samples = dist.rvs(size={max_obs}, random_state=rng)\n"
        f"running_means = np.cumsum(samples) / np.arange(1, {max_obs} + 1)\n\n"
        f"fig, ax = plt.subplots(figsize=(8, 5))\n"
        f"ax.plot(running_means, lw=0.8, label='Running Mean')\n"
        f"ax.axhline(dist.mean(), color='red', ls='--', label='True Mean')\n"
        f"ax.set_title('Law of Large Numbers')\n"
        f"ax.legend()\nplt.tight_layout()\nplt.show()"
    )

    snippet = CodeSnippet(
        code=code_text.strip(),
        imports=["import numpy as np", "from scipy import stats", "import matplotlib.pyplot as plt"],
    )

    fit_test = _goodness_of_fit(samples, dist, is_discrete)

    return LLNResult(
        running_means=running_means,
        true_mean=true_mean,
        summary=summary,
        figure=fig,
        interpretation=interpretation,
        fit_test=fit_test,
        code=snippet,
    )
