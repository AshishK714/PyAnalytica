"""Assumption checks a student can read -- issues 8 and 12.

The panel used to print the dictionary it was given:

    normality_shapiro_stat: 0.6365
    normality_shapiro_p: 0.0
    normality_ok: False
    n: 891

Internal names in snake_case; a p-value of 1e-16 shown as `0.0`, which says the
probability is zero; and a bare `False` under a headline announcing a
significant result, with nothing to say whether the violation changes anything.
"""

from __future__ import annotations

import pytest

from pyanalytica.ui.components.assumptions import assumption_lines


class TestPValues:

    def test_a_tiny_p_value_is_not_reported_as_zero(self):
        lines = assumption_lines({"normality_shapiro_p": 1e-16}, n=800)
        assert any("p < .0001" in line for line in lines)
        assert not any("p = 0.0000" in line for line in lines)

    def test_an_ordinary_p_value_is_shown_to_four_places(self):
        lines = assumption_lines({"levene_p": 0.9712}, test_name="Two-sample t-test")
        assert any("p = 0.9712" in line for line in lines)


class TestEqualSpread:

    def test_a_t_test_says_welch_is_applied_because_it_is(self):
        lines = assumption_lines({"levene_p": 0.001}, test_name="Two-sample t-test")
        joined = " ".join(lines)
        assert "Welch" in joined

    def test_an_anova_does_not_claim_a_correction_it_does_not_make(self):
        """scipy's f_oneway assumes equal spread and does not correct for its
        absence. Saying "Welch's correction is used" under an ANOVA would be a
        comforting sentence that is false."""
        lines = assumption_lines({"levene_p": 0.0038}, test_name="One-way ANOVA")
        joined = " ".join(lines)
        assert "Welch" not in joined
        assert "does not correct" in joined
        assert "Kruskal-Wallis" in joined

    def test_no_evidence_against_it_reads_as_such(self):
        lines = assumption_lines({"levene_p": 0.4}, test_name="One-way ANOVA")
        assert any("no evidence against it" in line for line in lines)


class TestNormality:

    def test_per_group_normality_names_the_group(self):
        lines = assumption_lines(
            {"shapiro_female_p": 0.0071, "shapiro_male_p": 1e-20}, n=714
        )
        joined = " ".join(lines)
        assert "Normality of female" in joined
        assert "Normality of male" in joined

    def test_a_large_sample_is_told_the_violation_may_not_matter(self):
        lines = assumption_lines({"normality_shapiro_p": 1e-16}, n=714)
        joined = " ".join(lines)
        assert "not a reason to abandon" in joined
        assert "histogram" in joined

    def test_a_small_sample_is_told_to_take_it_seriously(self):
        lines = assumption_lines({"normality_shapiro_p": 0.001}, n=18)
        joined = " ".join(lines)
        assert "worth taking seriously" in joined
        assert "Mann-Whitney" in joined


class TestNothingIsDropped:

    def test_an_unrecognised_key_still_appears(self):
        """Better a plain line than a silently missing check."""
        lines = assumption_lines({"something_new": 3}, n=10)
        assert any("something new" in line for line in lines)

    def test_no_snake_case_internals_survive(self):
        checks = {
            "normality_shapiro_stat": 0.6365,
            "normality_shapiro_p": 0.0,
            "normality_ok": False,
            "n": 891,
        }
        joined = " ".join(assumption_lines(checks))
        for internal in ("normality_shapiro_stat", "normality_ok", "shapiro_p"):
            assert internal not in joined
        assert "891" in joined

    def test_empty_checks_produce_nothing(self):
        assert assumption_lines({}) == []


class TestShapiroSubsampling:
    """Issue 8: the reported n was the frame's, not the test's."""

    def test_the_tested_n_is_reported_separately(self):
        import numpy as np
        import pandas as pd

        from pyanalytica.analyze.normality import SHAPIRO_MAX_N, shapiro_wilk_test

        big = pd.DataFrame({"x": np.random.default_rng(0).normal(size=41_188)})
        r = shapiro_wilk_test(big, "x")
        assert r.n == 41_188
        assert r.n_tested == SHAPIRO_MAX_N
        assert "random sample of 5,000 of the 41,188" in r.interpretation

    def test_a_small_column_says_nothing_about_sampling(self):
        import numpy as np
        import pandas as pd

        from pyanalytica.analyze.normality import shapiro_wilk_test

        small = pd.DataFrame({"x": np.random.default_rng(0).normal(size=400)})
        r = shapiro_wilk_test(small, "x")
        assert r.n == r.n_tested == 400
        assert "random sample" not in r.interpretation

    def test_the_shown_code_samples_the_way_the_panel_did(self):
        import numpy as np
        import pandas as pd

        from pyanalytica.analyze.normality import shapiro_wilk_test

        big = pd.DataFrame({"x": np.random.default_rng(0).normal(size=41_188)})
        code = shapiro_wilk_test(big, "x").code.code
        assert "RandomState(42).choice" in code
        assert "size=5000" in code
