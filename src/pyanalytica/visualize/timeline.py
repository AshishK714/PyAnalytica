"""Time series visualizations.

The date axis is the dangerous part of this panel, and it is worth saying why
in one place.

``pd.to_datetime`` does not refuse much. Given month names with no year it
returns March through December of year 1; given a column of years like 2019 and
2020 it reads them as *nanoseconds* since 1970 and stacks every point on the
same instant; given clock times it silently attaches today's date. Each of those
draws a smooth, confident, publication-quality chart of data that does not
exist. Nothing else in this tool fabricates an answer that convincingly -- the
rest either errors or looks obviously wrong -- so this module refuses a date
axis it cannot justify, and says which values it could not read.

Where a reading is defensible but chosen (a column of four-digit years is read
as calendar years), the chart carries a note saying so. The assumption is on
the figure, not only in the docs.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from pyanalytica.core.codegen import CodeSnippet
from pyanalytica.data.dates import date_like_rate, looks_like_dates

Figure = matplotlib.figure.Figure

# A four-digit year outside this range is more likely a code than a date.
YEAR_MIN, YEAR_MAX = 1500, 2999

# Fewest values worth judging -- two that happen to parse are not evidence.
MIN_VALUES = 3

# Share of the values that must survive parsing for the axis to be trusted.
MIN_PARSE_RATE = 0.95


_MONTH_NAMES = {
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
    "dec", "january", "february", "march", "april", "june", "july", "august",
    "september", "october", "november", "december", "sept",
}
_DAY_NAMES = {
    "mon", "tue", "tues", "wed", "thu", "thur", "thurs", "fri", "sat", "sun",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
}


def _names_a_period_without_a_year(series: pd.Series) -> bool:
    """Month or weekday names, which carry no year to place them in.

    Detected here rather than inferred from what pandas does with them, because
    what pandas does with them changes: pandas 3 dates "mar" to year 1 and plots
    it, pandas 2 refuses it as out of bounds. The column is the same column
    either way, and the reader deserves the same sentence about it.
    """
    values = series.dropna()
    if len(values) < MIN_VALUES:
        return False
    text = values.astype(str).str.strip().str.lower()
    known = _MONTH_NAMES | _DAY_NAMES
    return bool(text.isin(known).mean() >= 0.9)


def _example_values(series: pd.Series, n: int = 3) -> str:
    """A few of the actual values, for a message the reader can act on."""
    shown = series.dropna().astype(str).unique()[:n]
    return ", ".join(repr(str(v)) for v in shown)


def _looks_like_years(series: pd.Series) -> bool:
    """Whole numbers that all sit in a plausible range of calendar years."""
    values = series.dropna()
    if len(values) < MIN_VALUES:
        return False
    if not pd.api.types.is_numeric_dtype(values):
        return False
    if pd.api.types.is_bool_dtype(values):
        return False
    as_float = values.astype(float)
    if not (as_float == as_float.round()).all():
        return False
    return bool(as_float.between(YEAR_MIN, YEAR_MAX).all())


def prepare_time_axis(series: pd.Series, col_name: str) -> tuple[pd.Series, list[str]]:
    """Turn *series* into a trustworthy date axis, or refuse and say why.

    Returns the parsed dates and any notes the reader needs to see on the
    chart. Raises ValueError -- with a message written for a student, naming
    the column and showing its own values -- when no honest axis exists.
    """
    notes: list[str] = []

    if pd.api.types.is_datetime64_any_dtype(series):
        return series, notes

    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        if _looks_like_years(series):
            years = series.dropna().astype(int).astype(str)
            parsed = pd.to_datetime(years, format="%Y").reindex(series.index)
            notes.append(
                f"'{col_name}' was read as calendar years, each plotted at 1 January."
            )
            return parsed, notes
        raise ValueError(
            f"'{col_name}' holds numbers, not dates. Read as dates they would be "
            f"counted as nanoseconds since 1970, which puts every point within a "
            f"fraction of a second of 1 January 1970 and draws a chart of nothing. "
            f"Pick a column of dates, or convert this one in Data > Transform."
        )

    values = series.dropna()
    if len(values) < MIN_VALUES:
        raise ValueError(
            f"'{col_name}' has too few values ({len(values)}) to plot over time."
        )

    rate = date_like_rate(series)
    if rate < MIN_PARSE_RATE:
        parsed_anyway = pd.to_datetime(series, errors="coerce", format="mixed")
        years = parsed_anyway.dropna()
        year_one = bool(len(years)) and bool((years.dt.year <= 1).all())
        if _names_a_period_without_a_year(series) or year_one:
            raise ValueError(
                f"'{col_name}' names months or days but carries no year "
                f"({_example_values(series)}), so there is no timeline to draw. "
                f"pandas would date these to year 1. Combine the month with a year "
                f"column in Data > Transform, or choose a column of full dates."
            )
        if rate > 0:
            # Most of the column is dates. Saying "this is not a date column"
            # would be wrong and would send the reader looking in the wrong place.
            dated = int(round(rate * len(values)))
            raise ValueError(
                f"Only {dated} of {len(values)} values in '{col_name}' are dates. "
                f"Fix or filter the rest in Data > Transform before plotting them "
                f"over time."
            )
        raise ValueError(
            f"'{col_name}' does not hold dates ({_example_values(series)}). "
            f"Choose a column of dates -- if the dataset has one that was loaded "
            f"as text, convert it in Data > Transform."
        )

    parsed = pd.to_datetime(series, errors="coerce", format="mixed")
    present = int(series.notna().sum())
    kept = int(parsed.notna().sum())
    if present and kept / present < MIN_PARSE_RATE:
        raise ValueError(
            f"Only {kept} of {present} values in '{col_name}' could be read as "
            f"dates. Fix or filter the rest before plotting them over time."
        )
    if kept < present:
        notes.append(
            f"{present - kept} row(s) whose '{col_name}' could not be read as a "
            f"date were left out."
        )
    return _reject_degenerate(parsed, series, col_name), notes


def _reject_degenerate(parsed: pd.Series, original: pd.Series, col_name: str) -> pd.Series:
    """Catch parses that succeeded but produced dates nobody meant.

    Belt and braces behind the checks above: pandas gains and loses parsing
    behaviour between versions, and the failure this guards against is silent.
    """
    dates = parsed.dropna()
    if dates.empty:
        raise ValueError(f"None of the values in '{col_name}' could be read as dates.")

    years = dates.dt.year
    if (years <= 1).all():
        raise ValueError(
            f"Reading '{col_name}' as dates puts every value in year 1 "
            f"({_example_values(original)}), which means the values carry no year."
        )
    if not years.between(YEAR_MIN, YEAR_MAX).all():
        raise ValueError(
            f"Reading '{col_name}' as dates gives years outside "
            f"{YEAR_MIN}-{YEAR_MAX}. Check the column -- these are unlikely to be "
            f"the dates you meant."
        )

    only_day = dates.dt.normalize().unique()
    today = pd.Timestamp.today().normalize()
    if len(only_day) == 1 and only_day[0] == today:
        text = original.dropna().astype(str)
        if not text.str.contains(str(today.year)).any():
            raise ValueError(
                f"'{col_name}' looks like times of day, not dates "
                f"({_example_values(original)}). Read as dates they all land on "
                f"today, so the chart would show one day, not a timeline."
            )
    return parsed


def time_series(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    group_by: str | None = None,
    agg_level: str = "raw",
    chart_type: str = "line",
    rolling_window: int | None = None,
) -> tuple[Figure, CodeSnippet]:
    """Create a time series chart.

    agg_level: 'raw', 'daily', 'weekly', 'monthly'
    chart_type: 'line', 'area', 'bar'
    """
    work_df = df.copy()
    parsed, notes = prepare_time_axis(work_df[date_col], str(date_col))
    work_df[date_col] = parsed
    dropped = int(work_df[date_col].isna().sum())
    if dropped:
        work_df = work_df.dropna(subset=[date_col])
    work_df = work_df.sort_values(date_col)

    if pd.api.types.is_numeric_dtype(df[date_col]):
        parse_code = (
            f'df["{date_col}"] = pd.to_datetime('
            f'df["{date_col}"].astype(int).astype(str), format="%Y")'
        )
    else:
        parse_code = (
            f'df["{date_col}"] = pd.to_datetime('
            f'df["{date_col}"], errors="coerce", format="mixed")'
        )
    code_lines = [parse_code]
    if dropped:
        code_lines.append(f'df = df.dropna(subset=["{date_col}"])')
    code_lines.append(f'df = df.sort_values("{date_col}")')

    # Aggregate if needed
    freq_map = {"daily": "D", "weekly": "W", "monthly": "ME"}
    if agg_level in freq_map:
        freq = freq_map[agg_level]
        if group_by:
            work_df = work_df.set_index(date_col).groupby(group_by)[value_col].resample(freq).mean().reset_index()
            code_lines.append(
                f'df = df.set_index("{date_col}").groupby("{group_by}")["{value_col}"]'
                f'.resample("{freq}").mean().reset_index()'
            )
        else:
            work_df = work_df.set_index(date_col)[value_col].resample(freq).mean().reset_index()
            code_lines.append(
                f'df = df.set_index("{date_col}")["{value_col}"]'
                f'.resample("{freq}").mean().reset_index()'
            )

    fig, ax = plt.subplots(figsize=(12, 5))

    if group_by and group_by in work_df.columns:
        for name, group in work_df.groupby(group_by):
            if chart_type == "line":
                ax.plot(group[date_col], group[value_col], label=str(name))
            elif chart_type == "area":
                ax.fill_between(group[date_col], group[value_col], alpha=0.5, label=str(name))
            elif chart_type == "bar":
                ax.bar(group[date_col], group[value_col], alpha=0.7, label=str(name))
        ax.legend()
    else:
        if chart_type == "line":
            ax.plot(work_df[date_col], work_df[value_col])
        elif chart_type == "area":
            ax.fill_between(work_df[date_col], work_df[value_col], alpha=0.5)
        elif chart_type == "bar":
            ax.bar(work_df[date_col], work_df[value_col])

    code_lines.append(f'fig, ax = plt.subplots(figsize=(12, 5))')
    code_lines.append(f'ax.plot(df["{date_col}"], df["{value_col}"])')

    # Rolling average
    if rolling_window and not group_by:
        rolling = work_df.set_index(date_col)[value_col].rolling(rolling_window).mean()
        ax.plot(rolling.index, rolling.values, "r-", linewidth=2,
                label=f"{rolling_window}-period rolling avg")
        ax.legend()
        code_lines.append(
            f'rolling = df.set_index("{date_col}")["{value_col}"].rolling({rolling_window}).mean()\n'
            f'ax.plot(rolling.index, rolling.values, "r-", linewidth=2, '
            f'label="{rolling_window}-period rolling avg")'
        )

    ax.set_title(f"{value_col} over Time")
    ax.set_xlabel(date_col)
    ax.set_ylabel(value_col)
    plt.xticks(rotation=45, ha="right")
    fig.set_layout_engine("tight", pad=1.5)

    if notes:
        # On the figure, not in a toast: the assumption travels with the chart
        # into the report, the export and the screenshot.
        #
        # supxlabel rather than a figure-coordinate text box: the layout engine
        # reserves room for it and moves it when the browser resizes the figure,
        # where a fixed 0.01/0.01 placement plus subplots_adjust would be
        # overridden by the engine and end up under the axis.
        fig.supxlabel(
            "  ".join(notes),
            fontsize=8, style="italic", color="#555555",
        )

    code_lines.extend([
        f'ax.set_title("{value_col} over Time")',
        f'plt.xticks(rotation=45, ha="right")',
        f'plt.tight_layout()',
        f'plt.show()',
    ])

    return fig, CodeSnippet(
        code="\n".join(code_lines),
        imports=["import matplotlib.pyplot as plt", "import pandas as pd"],
    )
