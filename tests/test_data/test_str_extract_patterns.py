"""String: Extract, and the expression box's error -- sweep cases A27 and A29.

Extract wrapped the typed pattern in its own brackets to give it a group. That
is right for a pattern with no group in it, and wrong for every pattern that
has one -- which is how anyone who knows regex writes it, and what the sweep
plan itself specifies: `^(\\w+)`. Two groups meant `str.extract` returned a
two-column frame, and assigning that to one column raised

    Cannot set a DataFrame with multiple columns to the single column edu_first

so the menu action failed on the ordinary case and named an internal pandas
concept while doing it.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pyanalytica.data.transform import (
    _has_capture_group,
    add_column_arithmetic,
    str_extract,
)


@pytest.fixture
def df():
    return pd.DataFrame({
        "education": ["university.degree", "high.school", "basic.4y", "professional.course"],
        "job": ["admin.", "services", "technician", "admin."],
        "channel": ["Mobile", "Landline", "Mobile", "Mobile"],
        "age": [25, 34, 41, 52],
    })


# ------------------------------------------------------------- what must work


@pytest.mark.parametrize(
    "pattern,expected",
    [
        (r"^(\w+)", ["university", "high", "basic", "professional"]),   # the plan's A27
        (r"\w+", ["university", "high", "basic", "professional"]),      # no group at all
        (r"^(.)", ["u", "h", "b", "p"]),
        (r"^(?:\w+)\.(\w+)", ["degree", "school", "4y", "course"]),     # non-capturing first
        (r"(?P<word>\w+)", ["university", "high", "basic", "professional"]),
    ],
)
def test_patterns_written_the_ordinary_way(df, pattern, expected):
    out, _ = str_extract(df, "first", "education", pattern)
    assert list(out["first"]) == expected


def test_the_shown_code_reproduces_the_column(df):
    out, snippet = str_extract(df, "first", "education", r"^(\w+)")
    scope = {"df": df.copy(), "pd": pd}
    exec(snippet.code, scope)  # noqa: S102 - the snippet is what we are testing
    assert list(scope["df"]["first"]) == list(out["first"])


def test_a_pattern_that_matches_nothing_gives_blanks_not_an_error(df):
    out, _ = str_extract(df, "none", "education", r"^(zzz)")
    assert out["none"].isna().all()


def test_two_groups_are_refused_in_words(df):
    with pytest.raises(ValueError) as exc:
        str_extract(df, "both", "education", r"(\w+)\.(\w+)")
    message = str(exc.value)
    assert "2 groups" in message
    assert "(?:" in message, "say how to fix it"
    assert "DataFrame" not in message


def test_a_numeric_column_is_still_refused(df):
    with pytest.raises(ValueError, match="text column"):
        str_extract(df, "x", "age", r"(\d)")


def test_an_empty_pattern_is_refused(df):
    with pytest.raises(ValueError, match="pattern"):
        str_extract(df, "x", "education", "")


# ------------------------------------------------- the group detector itself


@pytest.mark.parametrize(
    "pattern,has_group",
    [
        (r"(\w+)", True),
        (r"\w+", False),
        (r"(?:\w+)", False),
        (r"(?=\w)", False),
        (r"(?P<name>\w+)", True),
        (r"\(literal\)", False),      # escaped brackets are not a group
        (r"[(]", False),              # a bracket inside a character class
        (r"[\]](\d)", True),
        (r"a\\(b)", True),            # escaped backslash, then a real group
    ],
)
def test_capture_group_detection(pattern, has_group):
    assert _has_capture_group(pattern) is has_group


# ------------------------------------------------------- A29, the expression


def test_joining_two_text_columns_works(df):
    out, _ = add_column_arithmetic(df, "combo", "job + channel")
    assert list(out["combo"])[0] == "admin.Mobile"


def test_quoted_text_is_explained_rather_than_raised(df):
    """The raw message names neither the column nor the operation."""
    with pytest.raises(ValueError) as exc:
        add_column_arithmetic(df, "combo", 'job + " | " + channel')
    message = str(exc.value)
    assert "quotes" in message
    assert "String: Replace" in message
    assert "unsupported operand" not in message


def test_arithmetic_still_works(df):
    out, _ = add_column_arithmetic(df, "double", "age * 2")
    assert list(out["double"]) == [50, 68, 82, 104]
