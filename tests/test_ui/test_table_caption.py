"""What the caption over a table says -- and what it must not say.

A table reading 32.2581 / 67.7419 / 100 is percentages or counts depending on a
sidebar dropdown, and nothing in the output said which. Scroll, screenshot or
export it and even that clue was gone.

The caption has to describe what the table *did*, which is not the same as what
the controls were set to: `create_pivot_table` applies Normalize only when the
aggregation is a count, so Mean + Row % produces means. A caption that read
"row percentages" over those would be worse than no caption at all.
"""

from __future__ import annotations

import pytest

from pyanalytica.ui.components.table_caption import table_caption


class TestPercentages:

    def test_row_percentages_name_the_total(self):
        text = table_caption("index", aggfunc="count", value_col="Age")
        assert "Row percentages" in text
        assert "each row totals 100" in text

    def test_column_percentages(self):
        text = table_caption("columns", aggfunc="count", value_col="Age")
        assert "Column percentages" in text
        assert "each column totals 100" in text

    def test_percentages_of_the_whole_table(self):
        text = table_caption("all", aggfunc="count", value_col="Age")
        assert "all cells total 100" in text

    def test_margins_are_explained_as_outside_the_base(self):
        """The halving bug lived exactly here: the All column was in the base."""
        text = table_caption("index", aggfunc="count", value_col="Age", margins=True)
        assert '"All"' in text
        assert "not part of the base" in text

    def test_no_margins_no_margin_sentence(self):
        text = table_caption("index", aggfunc="count", value_col="Age", margins=False)
        assert '"All"' not in text


class TestCountsAndAggregations:

    def test_counts_say_counts(self):
        assert table_caption(None, aggfunc="count", value_col="Age").startswith("Counts of Age")

    def test_an_aggregation_is_named(self):
        assert table_caption(None, aggfunc="mean", value_col="Fare") == "Mean of Fare."

    def test_crosstab_has_no_aggregation_to_name(self):
        text = table_caption("index", margins=True)
        assert "Row percentages" in text
        assert "Based on counts of" not in text


class TestTheCaptionDoesNotLie:

    @pytest.mark.parametrize("aggfunc", ["mean", "median", "sum", "min", "max"])
    def test_normalize_with_a_non_count_aggregation_is_not_called_percentages(self, aggfunc):
        """Normalize is silently ignored for these, so the caption must not
        describe the result as percentages."""
        text = table_caption("index", aggfunc=aggfunc, value_col="Fare")
        assert "percentages" not in text.lower().replace("not percentages", "")
        assert "Row percentages" not in text

    def test_and_it_says_the_control_had_no_effect(self):
        text = table_caption("index", aggfunc="mean", value_col="Fare")
        assert "counts only" in text
        assert "not percentages" in text

    def test_a_count_with_normalize_is_still_percentages(self):
        assert "Row percentages" in table_caption("index", aggfunc="count", value_col="Age")
