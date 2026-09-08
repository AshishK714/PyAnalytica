"""Filters that cannot mean what was typed -- Data > View, sweep section A.

Everything typed into the filter box arrives as text, and the same mistake used
to produce three different answers, none of them a message. On the 41,188-row
campaign file:

    age == "Mobile"    ->  0 rows, which reads as "no records match"
    age >  "Mobile"    ->  a raw TypeError traceback
    channel > "60"     ->  all 41,188 rows, because "Mobile" sorts after "60"

The third is the one that matters. A filter that cannot mean anything silently
returned the entire dataset, and every count taken afterwards was wrong while
looking completely ordinary.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pyanalytica.data.view import FilterCondition, apply_filters, check_filter


@pytest.fixture
def df():
    return pd.DataFrame({
        "age": [23, 34, 41, 52, 29, 38, 47, 61, 19, 55],
        "channel": ["Mobile", "Landline"] * 5,
        "campaign": [1, 2, 3, 1, 2, 1, 4, 2, 1, 3],
        "job": ["admin.", "services", "technician", "admin.", "services",
                "technician", "admin.", "services", "technician", "admin."],
    })


def _filter(df, column, operator, value, value2=None):
    f = FilterCondition(column=column, operator=operator, value=value, value2=value2)
    return apply_filters(df, [f])


# ------------------------------------------------------------- what must work


@pytest.mark.parametrize(
    "column,operator,value,expected",
    [
        ("channel", "==", "Mobile", 5),
        ("channel", "!=", "Mobile", 5),
        ("age", ">", "40", 5),
        ("age", ">=", "41", 5),
        ("age", "<", "30", 3),
        ("age", "<=", "29", 3),
        ("job", "contains", "ADMIN", 4),
        ("age", "isnull", None, 0),
        ("age", "notnull", None, 10),
        ("job", "==", "doctor", 0),
    ],
)
def test_the_operators_agree_with_pandas(df, column, operator, value, expected):
    out, _ = _filter(df, column, operator, value)
    assert len(out) == expected


def test_numbers_typed_as_text_still_compare_as_numbers(df):
    """The UI has no numeric input; everything arrives as a string."""
    out, snippet = _filter(df, "age", ">", "40")
    assert len(out) == 5
    assert "40.0" in snippet.code


def test_in_coerces_its_values_like_every_other_operator(df):
    """"in 34, 41" against a numeric column used to match nothing, silently."""
    f = FilterCondition(column="age", operator="in", value=["34", "41"])
    out, snippet = apply_filters(df, [f])
    assert len(out) == 2
    assert "34.0" in snippet.code


def test_two_filters_stack(df):
    fs = [
        FilterCondition(column="channel", operator="==", value="Mobile"),
        FilterCondition(column="age", operator=">", value="30"),
    ]
    out, _ = apply_filters(df, fs, logic="AND")
    expected = int(((df.channel == "Mobile") & (df.age > 30)).sum())
    assert len(out) == expected


# ------------------------------------------------------- what must be refused


def test_text_against_a_numeric_column_is_refused(df):
    with pytest.raises(ValueError, match="holds numbers"):
        _filter(df, "age", "==", "Mobile")


def test_the_same_mistake_is_refused_for_every_comparison(df):
    """Not just ==: the operator should not change whether it is caught."""
    for operator in ("==", "!=", ">", "<", ">=", "<="):
        with pytest.raises(ValueError, match="holds numbers"):
            _filter(df, "age", operator, "Mobile")


def test_ordering_a_text_column_by_a_number_is_refused(df):
    """This is the one that quietly returned every row."""
    with pytest.raises(ValueError) as exc:
        _filter(df, "channel", ">", "60")
    message = str(exc.value)
    assert "alphabetically" in message
    assert "'channel'" in message


def test_the_refusal_shows_a_real_value_from_the_column(df):
    with pytest.raises(ValueError) as exc:
        _filter(df, "channel", ">", "60")
    assert "'Mobile'" in str(exc.value) or "'Landline'" in str(exc.value)


def test_between_checks_both_ends(df):
    with pytest.raises(ValueError, match="holds numbers"):
        _filter(df, "age", "between", "20", "Mobile")


def test_a_missing_column_says_what_happened(df):
    with pytest.raises(ValueError, match="no column called"):
        _filter(df, "salery", "==", "1")


def test_ordering_text_against_text_is_still_allowed(df):
    """Alphabetical comparison is a real thing to want; only the mixed-up
    number-against-text case is a mistake."""
    out, _ = _filter(df, "job", ">", "s")
    assert len(out) == int((df.job > "s").sum())


def test_contains_works_on_a_numeric_column(df):
    """Searching digits in a number is unusual but well defined."""
    out, _ = _filter(df, "age", "contains", "4")
    assert len(out) == int(df.age.astype(str).str.contains("4").sum())


# ------------------------------------------------------------- the UI's guard


def test_check_filter_refuses_before_the_filter_is_stored(df):
    """The panel calls this as the filter is added, so a bad one never enters
    the list and cannot break the table, the row count and the download."""
    bad = FilterCondition(column="channel", operator=">", value="60")
    with pytest.raises(ValueError):
        check_filter(df, bad)

    good = FilterCondition(column="age", operator=">", value="40")
    assert check_filter(df, good) is None
