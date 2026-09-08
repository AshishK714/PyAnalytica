"""More than one row variable -- issue 14.

A pivot-table lesson is largely about nesting: sales by region *within* quarter.
`create_pivot_table` had accepted `str | list[str]` from the start and the
select simply did not allow a second choice, so the capability was there and
unreachable. Cross-tab needed the library widening as well, which pandas
supports directly.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pyanalytica.data.load import load_bundled
from pyanalytica.explore.crosstab import create_crosstab
from pyanalytica.explore.pivot import create_pivot_table


@pytest.fixture(scope="module")
def df():
    frame, _ = load_bundled("titanic")
    return frame


class TestNestedPivot:

    def test_two_row_variables_nest(self, df):
        table, _ = create_pivot_table(
            df, ["Pclass", "Sex"], "Survived", "Age", aggfunc="count", margins=False
        )
        assert isinstance(table.index, pd.MultiIndex)
        assert table.index.names == ["Pclass", "Sex"]
        assert len(table) == df.Pclass.nunique() * df.Sex.nunique()

    def test_row_percentages_still_total_100_when_nested(self, df):
        """The margins fix has to hold for a MultiIndex too."""
        table, _ = create_pivot_table(
            df, ["Pclass", "Sex"], "Survived", "Age",
            aggfunc="count", margins=True, normalize="index",
        )
        body = table[[c for c in table.columns if c != "All"]]
        for total in body.sum(axis=1):
            assert total == pytest.approx(100.0, abs=0.01)

    def test_one_row_variable_still_gives_a_flat_index(self, df):
        table, _ = create_pivot_table(
            df, ["Pclass"], "Survived", "Age", aggfunc="count", margins=False
        )
        assert not isinstance(table.index, pd.MultiIndex)

    def test_the_shown_code_names_both_columns(self, df):
        _, snippet = create_pivot_table(
            df, ["Pclass", "Sex"], "Survived", "Age", aggfunc="count"
        )
        assert "'Pclass'" in snippet.code and "'Sex'" in snippet.code


class TestNestedCrosstab:

    def test_two_row_variables_nest(self, df):
        result = create_crosstab(df, ["Pclass", "Sex"], "Survived")
        assert isinstance(result.table.index, pd.MultiIndex)
        assert result.table.index.names == ["Pclass", "Sex"]

    def test_the_counts_are_right(self, df):
        result = create_crosstab(df, ["Pclass", "Sex"], "Survived", margins=False)
        expected = pd.crosstab([df.Pclass, df.Sex], df.Survived)
        assert result.table.loc[(1, "female"), 1] == expected.loc[(1, "female"), 1]

    def test_a_single_name_still_works_as_a_string(self, df):
        """Every existing caller passes a string."""
        result = create_crosstab(df, "Pclass", "Survived")
        assert not isinstance(result.table.index, pd.MultiIndex)

    def test_nested_columns_too(self, df):
        result = create_crosstab(df, "Pclass", ["Survived", "Sex"], margins=False)
        assert isinstance(result.table.columns, pd.MultiIndex)

    def test_a_frequency_table_can_nest(self, df):
        result = create_crosstab(df, ["Pclass", "Sex"], None, margins=False)
        assert len(result.table) == df.Pclass.nunique() * df.Sex.nunique()
        assert result.table["Count"].sum() == len(df)

    def test_a_nested_frequency_table_shows_runnable_code(self, df):
        """It used to interpolate the list into a column name:
        df["['Pclass', 'Sex']"], which is not a column."""
        result = create_crosstab(df, ["Pclass", "Sex"], None)
        code = result.code.code
        assert "['Pclass', 'Sex']\"]" not in code
        scope = {"df": df, "pd": pd}
        exec(code, scope)  # noqa: S102 - the snippet is what we are testing
        assert len(scope["result"]) == df.Pclass.nunique() * df.Sex.nunique()

    def test_no_row_variable_is_refused_in_words(self, df):
        with pytest.raises(ValueError, match="at least one row variable"):
            create_crosstab(df, [], "Survived")

    def test_the_shown_code_names_both_columns(self, df):
        result = create_crosstab(df, ["Pclass", "Sex"], "Survived")
        assert 'df["Pclass"], df["Sex"]' in result.code.code

    def test_the_chi_square_still_runs_on_a_nested_table(self, df):
        result = create_crosstab(df, ["Pclass", "Sex"], "Survived")
        assert result.chi2 is not None
        assert result.p_value is not None
