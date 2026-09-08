"""The Timeline date axis -- issue 2.

This is the one defect in the sweep that manufactured a plausible wrong answer
rather than failing. `pd.to_datetime` accepted a column of month names with no
year, dated them all to year 1, and the panel drew a confident seasonal chart
titled "subscribed_pct over Time" with no warning anywhere.

Probing pandas turned up two more of the same shape that were never filed:

  * a column of years (2019, 2020) is read as *nanoseconds* since 1970, so every
    point lands within a microsecond of 1 January 1970;
  * clock times ("10:30") silently pick up today's date.

Each draws a smooth chart of data that does not exist, so all three are tested
here together.
"""

from __future__ import annotations

import matplotlib
import pandas as pd
import pytest

from pyanalytica.data.dates import date_like_rate
from pyanalytica.visualize.timeline import (
    _reject_degenerate,
    prepare_time_axis,
    time_series,
)


@pytest.fixture
def real_dates():
    return pd.DataFrame({
        "when": pd.date_range("2026-01-01", periods=30, freq="D"),
        "value": range(30),
    })


# --------------------------------------------------------------- refusals


def test_month_names_are_refused():
    """The filed defect: 'mar', 'apr' became 0001-03, 0001-04 and were plotted."""
    df = pd.DataFrame({"month": ["mar", "apr", "may", "jun"], "value": [1, 2, 3, 4]})
    with pytest.raises(ValueError, match="carries no year"):
        time_series(df, "month", "value")


def test_month_names_message_shows_the_values():
    df = pd.DataFrame({"month": ["mar", "apr", "may", "jun"], "value": [1, 2, 3, 4]})
    with pytest.raises(ValueError) as exc:
        prepare_time_axis(df["month"], "month")
    assert "'mar'" in str(exc.value)
    assert "Data > Transform" in str(exc.value)


def test_a_measurement_column_is_refused():
    """age, campaign, price -- read as dates these are nanoseconds since 1970."""
    df = pd.DataFrame({"age": [23.5, 41.2, 57.9, 30.1], "value": [1, 2, 3, 4]})
    with pytest.raises(ValueError, match="nanoseconds"):
        time_series(df, "age", "value")


def test_a_categorical_outcome_is_refused():
    df = pd.DataFrame({"subscribed": ["No", "Yes", "No", "No"], "value": [1, 2, 3, 4]})
    with pytest.raises(ValueError, match="does not hold dates"):
        time_series(df, "subscribed", "value")


def test_times_of_day_are_refused():
    """Read as dates these all land on today, which is one day, not a timeline."""
    df = pd.DataFrame({"t": ["10:30", "11:45", "12:00", "13:15"], "value": [1, 2, 3, 4]})
    with pytest.raises(ValueError):
        time_series(df, "t", "value")


def test_mostly_dates_says_so_rather_than_denying_the_column():
    """Wrong advice sends the reader to the wrong screen."""
    values = [f"2026-01-{d:02d}" for d in range(1, 9)] + ["oops"]
    df = pd.DataFrame({"d": values, "value": range(9)})
    with pytest.raises(ValueError, match="Only 8 of 9"):
        time_series(df, "d", "value")


def test_too_few_values_to_judge():
    df = pd.DataFrame({"d": ["2026-01-01", None], "value": [1, 2]})
    with pytest.raises(ValueError, match="too few values"):
        prepare_time_axis(df["d"], "d")


# ----------------------------------------------------------- what still works


def test_real_datetimes_pass_through_untouched(real_dates):
    parsed, notes = prepare_time_axis(real_dates["when"], "when")
    assert notes == []
    assert parsed.equals(real_dates["when"])


def test_dates_stored_as_text_are_accepted():
    values = [f"2026-01-{d:02d}" for d in range(1, 11)]
    df = pd.DataFrame({"d": values, "value": range(10)})
    fig, snippet = time_series(df, "d", "value")
    assert fig is not None
    assert "errors=\"coerce\"" in snippet.code


def test_a_year_column_is_read_as_years_and_says_so():
    """The reading is defensible, so it is allowed -- and disclosed."""
    df = pd.DataFrame({"year": [2019, 2020, 2021, 2022, 2023], "value": [1, 2, 3, 4, 5]})
    parsed, notes = prepare_time_axis(df["year"], "year")
    assert list(parsed.dt.year) == [2019, 2020, 2021, 2022, 2023]
    assert notes and "calendar years" in notes[0]


def test_the_assumption_is_written_on_the_chart():
    """A note in a toast is gone in five seconds; a note on the figure travels
    with it into the report, the export and the screenshot."""
    df = pd.DataFrame({"year": [2019, 2020, 2021, 2022, 2023], "value": [1, 2, 3, 4, 5]})
    fig, _ = time_series(df, "year", "value")
    printed = " ".join(t.get_text() for t in fig.texts)
    assert "calendar years" in printed


def test_year_column_code_matches_what_ran():
    df = pd.DataFrame({"year": [2019, 2020, 2021, 2022, 2023], "value": [1, 2, 3, 4, 5]})
    _, snippet = time_series(df, "year", "value")
    assert 'format="%Y"' in snippet.code


def test_aggregation_still_works_on_a_real_axis(real_dates):
    fig, snippet = time_series(real_dates, "when", "value", agg_level="weekly")
    assert isinstance(fig, matplotlib.figure.Figure)
    assert "resample" in snippet.code


# ------------------------------------------------- the guard behind the guard


def test_degenerate_guard_rejects_year_one_directly():
    """Belt and braces: pandas parsing behaviour moves between versions."""
    original = pd.Series(["mar", "apr", "may"])
    parsed = pd.to_datetime(pd.Series(["0001-03-01", "0001-04-01", "0001-05-01"]))
    with pytest.raises(ValueError, match="year 1"):
        _reject_degenerate(parsed, original, "month")


def test_degenerate_guard_rejects_implausible_years():
    original = pd.Series(["a", "b", "c"])
    parsed = pd.to_datetime(pd.Series(["1200-01-01", "1201-01-01", "1202-01-01"]))
    with pytest.raises(ValueError, match="outside"):
        _reject_degenerate(parsed, original, "code")


def test_degenerate_guard_rejects_everything_landing_on_today():
    original = pd.Series(["10:30", "11:45", "12:00"])
    today = pd.Timestamp.today().normalize()
    parsed = pd.Series([today + pd.Timedelta(hours=h) for h in (10, 11, 12)])
    with pytest.raises(ValueError, match="times of day"):
        _reject_degenerate(parsed, original, "t")


def test_degenerate_guard_allows_a_single_real_day():
    """A dataset that genuinely covers one day is not the same failure."""
    original = pd.Series(["2020-05-01 10:30", "2020-05-01 11:45", "2020-05-01 12:00"])
    parsed = pd.to_datetime(original)
    assert _reject_degenerate(parsed, original, "t") is parsed


# ------------------------------------------------------ the shared rate helper


@pytest.mark.parametrize(
    "values,expected",
    [
        ([f"2026-01-{d:02d}" for d in range(1, 6)], 1.0),
        (["mar", "apr", "may", "jun"], 0.0),
        ([1, 2, 3, 4], 0.0),
        ([f"2026-01-{d:02d}" for d in range(1, 5)] + ["x"] * 4, 0.5),
    ],
)
def test_date_like_rate(values, expected):
    assert date_like_rate(pd.Series(values)) == pytest.approx(expected)
