"""Which columns a student may group or cross-tabulate by.

A 0/1 integer is a category to a student and a number to a regression. The
classification stays numeric; the *pickers* ask a different question.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pyanalytica.core.types import (
    ColumnType,
    classify_column,
    get_categorical_columns,
    get_groupable_columns,
    is_groupable,
)
from pyanalytica.data.load import load_bundled


class TestIsGroupable:
    def test_binary_integer_is_groupable(self):
        """Survived: the column a tester could not cross-tabulate by."""
        assert is_groupable(pd.Series([0, 1, 1, 0, 1]))

    def test_binary_integer_is_still_numeric(self):
        """It must stay numeric, or it cannot be a regression target."""
        assert classify_column(pd.Series([0, 1, 1, 0, 1])) == ColumnType.NUMERIC

    def test_small_integer_class_is_groupable(self):
        assert is_groupable(pd.Series([1, 2, 3, 1, 2, 3]))

    def test_text_is_groupable(self):
        assert is_groupable(pd.Series(["a", "b", "a"]))

    def test_boolean_is_groupable(self):
        assert is_groupable(pd.Series([True, False, True]))

    def test_continuous_numeric_is_not(self):
        assert not is_groupable(pd.Series(np.linspace(0, 100, 500)))

    def test_many_distinct_integers_are_not(self):
        assert not is_groupable(pd.Series(range(200)))

    def test_decimals_are_not_even_when_few(self):
        """Few distinct values but not whole numbers -- still a measurement."""
        assert not is_groupable(pd.Series([1.5, 2.5, 1.5, 2.5]))

    def test_empty_column_is_not(self):
        assert not is_groupable(pd.Series([np.nan, np.nan], dtype=float))

    def test_threshold_is_adjustable(self):
        series = pd.Series(list(range(15)) * 2)
        assert not is_groupable(series)
        assert is_groupable(series, max_levels=20)


class TestTheClassificationCacheCannotServeAnotherFrame:
    """CI failed at random: titanic was offered a column "b" that belonged to
    a frame freed earlier, whose id the new frame had been given."""

    def test_an_entry_for_a_different_object_with_the_same_id_is_ignored(self):
        from pyanalytica.core import types

        df = pd.DataFrame({"real": ["x", "y"]})
        stale = pd.DataFrame({"b": ["p", "q"]})
        # What id reuse produces: an entry under this frame's id, built for
        # another frame.
        types._classify_cache.clear()
        types._classify_cache[id(df)] = (stale, {"b": types.ColumnType.CATEGORICAL})
        assert list(types.classify_columns(df)) == ["real"]

    def test_a_column_added_in_place_is_seen(self):
        from pyanalytica.core.types import classify_columns

        df = pd.DataFrame({"a": [1.5, 2.5]})
        assert list(classify_columns(df)) == ["a"]
        df["g"] = ["x", "y"]
        assert list(classify_columns(df)) == ["a", "g"]

    def test_the_same_frame_hits_the_cache(self):
        from pyanalytica.core.types import classify_columns

        df = pd.DataFrame({"a": [1.5, 2.5]})
        assert classify_columns(df) is classify_columns(df)


class TestBundledDatasets:
    def test_titanic_offers_survived_and_pclass(self):
        df, _ = load_bundled("titanic")
        groupable = get_groupable_columns(df)
        assert "Survived" in groupable
        assert "Pclass" in groupable
        # and still excludes the genuinely continuous ones
        assert "Age" not in groupable
        assert "Fare" not in groupable

    def test_tips_offers_size(self):
        """The column whose absence broke a pivot the tester tried."""
        df, _ = load_bundled("tips")
        assert "size" in get_groupable_columns(df)

    def test_groupable_is_a_superset_of_categorical(self):
        for name in ("titanic", "tips"):
            df, _ = load_bundled(name)
            assert set(get_categorical_columns(df)) <= set(get_groupable_columns(df))

    def test_identifier_columns_stay_out(self):
        df, _ = load_bundled("titanic")
        assert "Name" not in get_groupable_columns(df)
        assert "PassengerId" not in get_groupable_columns(df)
