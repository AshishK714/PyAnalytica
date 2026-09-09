"""The same quantity, through two different panels, must agree.

This is the one check that needs no oracle at all, and it is the one that found
the worst arithmetic defect in the tool. Cross-tab said channel x subscribed was
94.8 / 5.2; Pivot said 47.4 / 2.6 for the same cells. Neither number can be
checked without an external reference -- but they cannot both be right, and
noticing that took no reference whatever.

Reconciliation is cheap and it is not circular in the way a self-written test
is: two implementations that disagree prove a bug exists without anyone knowing
which is correct. That makes it the right complement to the validation
notebooks, which are expensive, external, and say which one is wrong.

Each test below computes one quantity two ways through the tool and requires
them to match.

Two things learned writing these, both encoded in the tolerances:

*Compare the same table.* The first draft compared a cross-tab of all 891 rows
against a pivot that counted `Age`, and `Age` has 177 missing values. The panels
disagreed by half a percentage point and neither was wrong. A reconciliation
test must hold everything but the panel constant, so these use a complete column
where the quantity is meant to be a count of rows.

*Panels round to different places.* Cross-tab returns percentages at 1dp and
chi-square at 2dp; the proportions panel returns chi-square at 3dp; Evaluate
returns accuracy at 3dp. The rounding is in the returned object, not in the
display layer, so it also reaches exports. Nothing here is wrong, but it means
agreement can only ever be asserted to the coarser panel's precision -- which is
what `DISPLAY_*` below are for, and why they are named rather than inlined.
"""

from __future__ import annotations

import pytest

from pyanalytica.analyze.means import one_way_anova, two_sample_ttest
from pyanalytica.analyze.proportions import chi_square_test, two_proportion_ztest
from pyanalytica.data.load import load_bundled
from pyanalytica.explore.crosstab import create_crosstab
from pyanalytica.explore.pivot import create_pivot_table
from pyanalytica.explore.summarize import group_summarize
from pyanalytica.model.classify import logistic_regression
from pyanalytica.model.evaluate import evaluate_classification


#: Cross-tab returns percentages rounded to one decimal place, so two panels
#: showing the same share can differ by up to half of the last place shown.
DISPLAY_PCT = 0.05

#: Test statistics come back at two decimals from one panel, three from
#: another.
DISPLAY_STAT = 0.005

#: Model metrics come back at three decimals.
DISPLAY_METRIC = 0.0005


@pytest.fixture(scope="module")
def titanic():
    df, _ = load_bundled("titanic")
    return df


@pytest.fixture(scope="module")
def tips():
    df, _ = load_bundled("tips")
    return df


class TestPercentagesAgreeBetweenPanels:
    """The defect this file exists for."""

    def test_row_percentages_match_between_crosstab_and_pivot(self, titanic):
        ct = create_crosstab(titanic, "Pclass", "Survived", normalize="index", margins=True)
        pivot, _ = create_pivot_table(
            titanic, "Pclass", "Survived", "PassengerId",
            aggfunc="count", margins=True, normalize="index",
        )
        for level in (1, 2, 3):
            for outcome in (0, 1):
                a = float(ct.table.loc[level, outcome])
                b = float(pivot.loc[level, outcome])
                assert a == pytest.approx(b, abs=DISPLAY_PCT), (
                    f"Pclass {level}, Survived {outcome}: cross-tab says {a:.2f}%, "
                    f"pivot says {b:.2f}%. One of them is wrong."
                )

    def test_column_percentages_match_between_crosstab_and_pivot(self, titanic):
        ct = create_crosstab(titanic, "Pclass", "Survived", normalize="columns", margins=True)
        pivot, _ = create_pivot_table(
            titanic, "Pclass", "Survived", "PassengerId",
            aggfunc="count", margins=True, normalize="columns",
        )
        for level in (1, 2, 3):
            for outcome in (0, 1):
                assert float(ct.table.loc[level, outcome]) == pytest.approx(
                    float(pivot.loc[level, outcome]), abs=DISPLAY_PCT
                )

    def test_margins_do_not_change_the_percentages_they_summarise(self, titanic):
        """Adding a total to a table must not move the numbers inside it."""
        with_margins, _ = create_pivot_table(
            titanic, "Pclass", "Survived", "PassengerId",
            aggfunc="count", margins=True, normalize="index",
        )
        without, _ = create_pivot_table(
            titanic, "Pclass", "Survived", "PassengerId",
            aggfunc="count", margins=False, normalize="index",
        )
        for level in (1, 2, 3):
            for outcome in (0, 1):
                assert float(with_margins.loc[level, outcome]) == pytest.approx(
                    float(without.loc[level, outcome]), abs=0.01
                )


class TestCountsAgree:

    def test_crosstab_counts_match_summarize(self, titanic):
        ct = create_crosstab(titanic, "Pclass", "Survived", margins=False)
        summary, _ = group_summarize(titanic, ["Pclass"], ["Survived"], ["count"])
        count_col = [c for c in summary.columns if "count" in str(c).lower()][0]
        for level in (1, 2, 3):
            from_crosstab = int(ct.table.loc[level].sum())
            from_summary = int(
                summary.loc[summary["Pclass"] == level, count_col].iloc[0]
            )
            assert from_crosstab == from_summary, (
                f"Pclass {level}: cross-tab counts {from_crosstab}, "
                f"summarize counts {from_summary}"
            )

    def test_pivot_counts_match_the_frame(self, titanic):
        pivot, _ = create_pivot_table(
            titanic, "Pclass", "Survived", "Age", aggfunc="count", margins=False
        )
        # Age has missing values, so a count of Age is not a count of rows --
        # which is exactly the kind of thing worth pinning.
        assert pivot.to_numpy().sum() == titanic["Age"].notna().sum()

    def test_summarize_group_means_match_a_direct_groupby(self, tips):
        summary, _ = group_summarize(tips, ["day"], ["total_bill"], ["mean"])
        mean_col = [c for c in summary.columns if "mean" in str(c).lower()][0]
        direct = tips.groupby("day", observed=True)["total_bill"].mean()
        for _, row in summary.iterrows():
            assert float(row[mean_col]) == pytest.approx(
                float(direct[row["day"]]), rel=1e-9
            )


class TestTestsAgreeWithEachOther:

    def test_chi_square_matches_between_crosstab_and_proportions(self, titanic):
        ct = create_crosstab(titanic, "Pclass", "Survived", margins=False)
        prop = chi_square_test(titanic, "Pclass", "Survived")
        assert float(ct.chi2) == pytest.approx(float(prop.chi2), abs=DISPLAY_STAT), (
            f"the same chi-square on the same table: cross-tab {ct.chi2}, "
            f"proportions {prop.chi2}"
        )
        assert int(ct.dof) == int(prop.dof)

    def test_a_two_group_comparison_agrees_with_anova_on_two_groups(self, titanic):
        """F on two groups is t squared. Two panels, one fact."""
        clean = titanic.dropna(subset=["Age"])
        t = two_sample_ttest(clean, "Age", "Sex")
        f = one_way_anova(clean, "Age", "Sex")
        # Only when the t-test assumed equal variances, which is the case ANOVA
        # is doing; the result names which it used.
        if "Welch" not in t.test_name:
            assert float(t.statistic) ** 2 == pytest.approx(
                float(f.statistic), abs=DISPLAY_STAT
            )
            assert float(t.p_value) == pytest.approx(float(f.p_value), abs=DISPLAY_STAT)

    def test_the_two_proportion_test_agrees_with_the_crosstab_it_summarises(self, titanic):
        """Same 2x2 table, two panels: the shares must match the counts."""
        ct = create_crosstab(titanic, "Sex", "Survived", margins=False)
        prop = two_proportion_ztest(titanic, "Survived", "1", "Sex")
        for group, share in zip(prop.summary["Group"], prop.summary["Proportion"]):
            row = ct.table.loc[group]
            expected = row[1] / row.sum()
            assert float(share) == pytest.approx(float(expected), abs=1e-4), (
                f"{group}: the proportion test says {share}, the cross-tab "
                f"implies {expected:.4f}"
            )


class TestModelMetricsAgree:

    def test_accuracy_matches_between_classify_and_evaluate(self, titanic):
        r = logistic_regression(
            titanic, "Survived", ["Pclass", "Age", "Fare"],
            test_size=0.3, random_state=42,
        )
        ev = evaluate_classification(r.y_test, r.model.predict(r.X_test), r.probabilities)
        assert float(r.test_accuracy) == pytest.approx(
            float(ev.accuracy), abs=DISPLAY_METRIC
        ), (
            f"Classify reports {r.test_accuracy} on the held-out rows, "
            f"Evaluate reports {ev.accuracy} for the same model and rows."
        )

    def test_the_confusion_matrix_totals_the_rows_it_scored(self, titanic):
        r = logistic_regression(
            titanic, "Survived", ["Pclass", "Age", "Fare"],
            test_size=0.3, random_state=42,
        )
        ev = evaluate_classification(r.y_test, r.model.predict(r.X_test), r.probabilities)
        assert int(ev.confusion_matrix.to_numpy().sum()) == len(r.y_test)

    def test_accuracy_matches_its_own_confusion_matrix(self, titanic):
        r = logistic_regression(
            titanic, "Survived", ["Pclass", "Age", "Fare"],
            test_size=0.3, random_state=42,
        )
        ev = evaluate_classification(r.y_test, r.model.predict(r.X_test), r.probabilities)
        matrix = ev.confusion_matrix.to_numpy()
        correct = matrix.diagonal().sum()
        assert float(ev.accuracy) == pytest.approx(
            correct / matrix.sum(), abs=DISPLAY_METRIC
        )
