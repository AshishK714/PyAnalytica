"""Findings from two student-style HW4 runs on 0.10.6, one test each."""

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from pyanalytica.ask import describe_one, relate_two
from pyanalytica.data.export import to_csv_bytes
from pyanalytica.ui.components.download_result import file_slug


@pytest.fixture(scope="module")
def df():
    # Two regions with the same smoker share (2 of 10), as northwest and
    # southwest had in the assignment's data (17.8% each).
    region = ["ne"] * 10 + ["nw"] * 10 + ["se"] * 10 + ["sw"] * 10
    smoker = (["yes"] * 3 + ["no"] * 7 + ["yes"] * 2 + ["no"] * 8
              + ["yes"] * 4 + ["no"] * 6 + ["yes"] * 2 + ["no"] * 8)
    return pd.DataFrame({
        "region": region, "smoker": smoker,
        # Many distinct values, so it reads as a number; nw and sw share a mean.
        "charges": np.r_[50 + np.arange(10), 30 + np.arange(10), 90 + np.arange(10), 30 + np.arange(10)],
    })


def test_a_tied_lowest_share_names_both_groups(df):
    sentence = relate_two(df, "smoker", "region").answer.sentence
    assert "20.0% (region = nw and sw)" in sentence


def test_a_tied_lowest_mean_names_both_groups(df):
    sentence = relate_two(df, "charges", "region").answer.sentence
    assert "lowest for region = nw and sw" in sentence


def test_tied_categories_are_named_together(df):
    assert "Every category has 10 rows" in describe_one(df, "region").answer.sentence
    sentence = describe_one(df.iloc[:30], "smoker").answer.sentence
    assert "the rarest is yes" in sentence


def test_csv_writes_the_decimals_it_is_given():
    frame = pd.DataFrame({"g": ["a", "b"], "n": [3, 4], "mean": [8434.268297856202, 30679.0]})
    text = to_csv_bytes(frame, decimals=2).decode()
    assert "8434.27" in text and "30679.00" in text and ",3," in text
    assert "8434.268297856202" in to_csv_bytes(frame).decode()


def test_file_names_come_from_the_description():
    assert file_slug("charges by region, split by smoker") == "charges_by_region_split_by_smoker"
    assert file_slug("") == "result"
