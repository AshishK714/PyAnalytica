"""Column type classification for DataFrames."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

import pandas as pd


class ColumnType(Enum):
    """Semantic column types for analytics."""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"
    ID = "id"
    TEXT = "text"


def classify_column(series: pd.Series) -> ColumnType:
    """Classify a single column by its semantic type.

    Logic:
    - datetime dtype → DATETIME
    - numeric dtype with all unique + name contains 'id' → ID
    - numeric dtype → NUMERIC
    - object/category with <30 unique or <5% unique → CATEGORICAL
    - else → TEXT
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return ColumnType.DATETIME

    if pd.api.types.is_numeric_dtype(series):
        n_unique = series.nunique()
        col_name = series.name if series.name else ""
        if (
            n_unique == len(series.dropna())
            and isinstance(col_name, str)
            and "id" in col_name.lower()
        ):
            return ColumnType.ID
        return ColumnType.NUMERIC

    if isinstance(series.dtype, pd.CategoricalDtype) or series.dtype == object or pd.api.types.is_string_dtype(series):
        n_unique = series.nunique()
        n_total = len(series.dropna())
        if n_total == 0:
            return ColumnType.CATEGORICAL
        if n_unique < 30 or (n_unique / n_total) < 0.05:
            return ColumnType.CATEGORICAL
        return ColumnType.TEXT

    return ColumnType.TEXT


_classify_cache: dict[int, tuple[pd.DataFrame, dict[str, ColumnType]]] = {}


def classify_columns(df: pd.DataFrame) -> dict[str, ColumnType]:
    """Classify all columns in a DataFrame.

    A single-entry cache keyed by ``id(df)``. An id is unique only among
    live objects: once a frame is freed, the next frame can be given the
    same id, and the cache used to hand it the dead frame's column types.
    CI caught it at random (titanic was offered a column "b" from another
    frame); in the app it could fill a dropdown with another dataset's
    columns after a transform replaced a frame. The entry now holds the
    frame itself and is used only for that same frame, with the same
    columns. Holding it keeps at most one extra frame alive.
    """
    entry = _classify_cache.get(id(df))
    if entry is not None:
        cached_df, cached = entry
        if cached_df is df and list(cached) == list(df.columns):
            return cached
    result = {col: classify_column(df[col]) for col in df.columns}
    _classify_cache.clear()
    _classify_cache[id(df)] = (df, result)
    return result


def get_numeric_columns(df: pd.DataFrame) -> list[str]:
    """Return column names classified as NUMERIC."""
    return [col for col, ct in classify_columns(df).items() if ct == ColumnType.NUMERIC]


def get_categorical_columns(df: pd.DataFrame) -> list[str]:
    """Return column names classified as CATEGORICAL."""
    return [col for col, ct in classify_columns(df).items() if ct == ColumnType.CATEGORICAL]


# A numeric column with this many distinct whole-number values or fewer is
# offered as a grouping variable. Survived (2) and Pclass (3) qualify; Age (88)
# and Fare do not.
MAX_GROUPABLE_LEVELS = 12


def is_groupable(series: pd.Series, max_levels: int = MAX_GROUPABLE_LEVELS) -> bool:
    """Whether a column can sensibly be grouped or cross-tabulated by.

    Categorical and boolean columns always qualify. A numeric column qualifies
    when it holds a small number of whole numbers -- a 0/1 outcome or a 1-2-3
    class is a category to a student, whatever its dtype says.

    Deliberately separate from :func:`classify_column`, which stays as it is:
    `Survived` must remain NUMERIC so it can be a regression target or enter a
    correlation. This answers the different question of what belongs in a
    dropdown asking for a grouping variable.
    """
    if series.dropna().empty:
        return False

    kind = classify_column(series)
    if kind in (ColumnType.CATEGORICAL, ColumnType.DATETIME):
        return True
    if kind != ColumnType.NUMERIC:
        return False

    values = series.dropna()
    if values.nunique() > max_levels:
        return False
    if pd.api.types.is_bool_dtype(values):
        return True
    try:
        return bool((values == values.round()).all())
    except (TypeError, ValueError):
        return False


def get_groupable_columns(
    df: pd.DataFrame, max_levels: int = MAX_GROUPABLE_LEVELS
) -> list[str]:
    """Columns a student can group or cross-tabulate by.

    Categorical columns plus low-cardinality integer ones. A tester could not
    cross-tabulate `Sex` against `Survived` because a 0/1 integer classifies as
    numeric and was filtered out of the variable list -- nothing errored, the
    option simply was not offered.
    """
    return [col for col in df.columns if is_groupable(df[col], max_levels)]


def get_datetime_columns(df: pd.DataFrame) -> list[str]:
    """Return column names classified as DATETIME."""
    return [col for col, ct in classify_columns(df).items() if ct == ColumnType.DATETIME]


def get_id_columns(df: pd.DataFrame) -> list[str]:
    """Return column names classified as ID."""
    return [col for col, ct in classify_columns(df).items() if ct == ColumnType.ID]


def get_text_columns(df: pd.DataFrame) -> list[str]:
    """Return column names classified as TEXT."""
    return [col for col, ct in classify_columns(df).items() if ct == ColumnType.TEXT]
