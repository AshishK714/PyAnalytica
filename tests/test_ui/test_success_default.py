"""The Success Value default -- issue 12.

Sorting the levels and taking the first put "No" ahead of "Yes" in every Yes/No
outcome, so the test silently answered the inverse question and the result
sentence read plausibly either way.
"""

import pandas as pd

from pyanalytica.ui.modules.analyze.mod_proportions import (
    SUCCESS_LABEL,
    _success_choices,
)


def test_binary_outcome_defaults_to_the_minority_level():
    subscribed = pd.Series(["No"] * 900 + ["Yes"] * 100)
    levels, default = _success_choices(subscribed)
    assert levels == ["No", "Yes"]
    assert default == "Yes"


def test_default_does_not_depend_on_alphabetical_order():
    """Fail/Pass, True/False and Yes/No all put the non-event first."""
    for rare, common in (("Pass", "Fail"), ("True", "False"), ("Yes", "No")):
        series = pd.Series([common] * 80 + [rare] * 20)
        _, default = _success_choices(series)
        assert default == rare


def test_more_than_two_levels_keeps_a_stable_first_choice():
    levels, default = _success_choices(pd.Series(["b", "c", "a", "a"]))
    assert levels == ["a", "b", "c"]
    assert default == "a"


def test_empty_column_does_not_raise():
    levels, default = _success_choices(pd.Series([], dtype=object))
    assert levels == []
    assert default == ""


def test_label_says_the_control_is_load_bearing():
    assert SUCCESS_LABEL == 'Which value counts as a "success"?'
