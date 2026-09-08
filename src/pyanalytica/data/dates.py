"""Recognising date columns when a file is loaded.

A CSV has no types. A `date` column arrives as text, classifies as TEXT, and
Timeline then has nothing to offer as a date axis — a tester loaded a file with
365 days of dates and Profile called the column `str`.

The temptation is to hand every text column to ``pd.to_datetime`` and keep
whatever sticks. That is how an order reference like ``2024-001`` silently
becomes the 1st of January 2024, and nobody notices until a chart is wrong.
So the rule here is deliberately narrow:

1. Only object/string columns are considered. Numbers are never reinterpreted,
   so ``20240115`` stays an integer even though it looks like a date.
2. The values must *look* like dates before pandas is asked — a strict pattern
   match, not a guess. ``2024-001`` does not match; ``2024-01-05`` does.
3. Nearly all the values must convert. One stray word is tolerated; a column
   that is half dates and half something else is left alone.
4. What was converted is reported, so the student sees it happened and can
   change it back in Transform.

Ambiguity is unavoidable with ``05/06/2024`` and is resolved month-first, the
pandas default. The generated code says so, so a student reading it can see
the assumption rather than inherit it silently.
"""

from __future__ import annotations

import re

import pandas as pd

from pyanalytica.core.codegen import CodeSnippet

# Fraction of non-null values that must convert for the column to be a date.
MIN_PARSE_RATE = 0.95

# Fewest non-null values worth judging. Two rows that happen to look like dates
# are not evidence.
MIN_VALUES = 3

# Shapes we accept. Anchored, and specific about digit counts, so identifiers
# like "2024-001" or "1-2-3" never match.
_DATE_PATTERNS = (
    r"\d{4}-\d{2}-\d{2}",                        # 2024-01-05
    r"\d{4}/\d{2}/\d{2}",                        # 2024/01/05
    r"\d{1,2}/\d{1,2}/\d{4}",                    # 5/1/2024
    r"\d{1,2}-\d{1,2}-\d{4}",                    # 5-1-2024
    r"\d{1,2} [A-Za-z]{3,9},? \d{4}",            # 5 January 2024
    r"[A-Za-z]{3,9} \d{1,2},? \d{4}",            # January 5, 2024
)

# Optional trailing time, so timestamps are recognised too.
_TIME = r"(?:[ T]\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?"

_DATE_LIKE = re.compile(
    r"^(?:" + "|".join(_DATE_PATTERNS) + r")" + _TIME + r"$"
)


def date_like_rate(series: pd.Series) -> float:
    """Share of the non-null values that are shaped like dates, 0.0 to 1.0.

    Returns 0.0 for anything not worth judging -- numbers, or too few values --
    so a caller can treat "not dates" and "no evidence" the same way.
    """
    if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
        return 0.0

    values = series.dropna()
    if len(values) < MIN_VALUES:
        return 0.0

    text = values.astype(str).str.strip()
    return float(text.map(lambda v: bool(_DATE_LIKE.match(v))).mean())


def looks_like_dates(series: pd.Series, min_rate: float = MIN_PARSE_RATE) -> bool:
    """Whether *series* is text whose values are shaped like dates."""
    return date_like_rate(series) >= min_rate


def try_parse_dates(
    series: pd.Series, min_rate: float = MIN_PARSE_RATE
) -> pd.Series | None:
    """Convert *series* to datetimes, or return None to leave it alone."""
    if not looks_like_dates(series, min_rate):
        return None

    converted = pd.to_datetime(series, errors="coerce", format="mixed")

    original_present = series.notna().sum()
    if original_present == 0:
        return None

    # Values that were there before and did not survive the conversion.
    kept = converted.notna().sum()
    if kept / original_present < min_rate:
        return None

    return converted


def detect_date_columns(df: pd.DataFrame, min_rate: float = MIN_PARSE_RATE) -> list[str]:
    """Names of the columns that would be converted to dates."""
    return [col for col in df.columns if looks_like_dates(df[col], min_rate)]


def parse_date_columns(
    df: pd.DataFrame, min_rate: float = MIN_PARSE_RATE
) -> tuple[pd.DataFrame, list[str], CodeSnippet]:
    """Convert every date-like text column.

    Returns the frame, the names converted, and the equivalent pandas code.
    The frame is returned unchanged when nothing qualifies.
    """
    result = df.copy()
    converted: list[str] = []

    for col in df.columns:
        parsed = try_parse_dates(df[col], min_rate)
        if parsed is not None:
            result[col] = parsed
            converted.append(str(col))

    if not converted:
        return df, [], CodeSnippet(code="# No date columns detected")

    lines = [
        "# Columns whose values were shaped like dates. Ambiguous forms such",
        "# as 05/06/2024 are read month-first; pass dayfirst=True to change that.",
    ]
    for col in converted:
        lines.append(f'df["{col}"] = pd.to_datetime(df["{col}"], errors="coerce")')

    return (
        result,
        converted,
        CodeSnippet(code="\n".join(lines), imports=["import pandas as pd"]),
    )
