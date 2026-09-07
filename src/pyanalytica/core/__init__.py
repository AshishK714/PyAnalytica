"""PyAnalytica core module."""

import pandas as pd

from pyanalytica.core.codegen import CodeGenerator, CodeSnippet
from pyanalytica.core.types import ColumnType, classify_column, classify_columns


def display_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Make a frame safe to hand to a data grid.

    Pivoting or cross-tabulating by a numeric column produces non-string
    column labels -- pivoting tips by `size` gives labels 1..6 -- and the grid
    fails on those with "'DataFrame' object has no attribute 'dtype'", which
    reaches the student as raw text where a table should be. Flattens any
    MultiIndex and casts every label to a string.
    """
    result = df.copy()
    if isinstance(result.columns, pd.MultiIndex):
        result.columns = [
            " ".join(str(part) for part in label if str(part) != "").strip()
            for label in result.columns
        ]
    else:
        result.columns = [str(label) for label in result.columns]
    # Positional, because a flattened MultiIndex can leave duplicate labels and
    # result[label] would then hand back a frame rather than a column.
    for i, (_, col) in enumerate(result.items()):
        if not _grid_serializable(col):
            result.isetitem(i, col.astype(str))
    return result


def _grid_serializable(series: pd.Series) -> bool:
    """Can the grid's JSON encoder handle this column as it stands?

    Numbers, strings, booleans, datetimes and plain categoricals are fine.
    Anything else -- pandas Interval (which is what pd.cut returns), Period,
    Timedelta, complex, a dict or a list in an object column -- raises inside
    Shiny's serialiser, downstream of every module's try/except. Nothing catches
    it, no message reaches the student, and the session stops responding until a
    reload, which discards their dataset. Cheaper to render those as text.
    """
    dtype = series.dtype
    if isinstance(dtype, pd.CategoricalDtype):
        return not isinstance(dtype.categories, pd.IntervalIndex)
    if pd.api.types.is_numeric_dtype(dtype) or pd.api.types.is_bool_dtype(dtype):
        return not pd.api.types.is_complex_dtype(dtype)
    if dtype == object:
        # is_string_dtype() answers differently across pandas versions here, so
        # look at the values instead.
        sample = series.dropna().head(50)
        return all(isinstance(v, (str, int, float, bool)) for v in sample)
    return bool(
        pd.api.types.is_datetime64_any_dtype(dtype)
        or pd.api.types.is_string_dtype(dtype)
    )


def round_df(df: pd.DataFrame, decimals: int) -> pd.DataFrame:
    """Round numeric columns for display, and make the frame grid-safe."""
    result = display_frame(df)
    for col in result.select_dtypes(include="number").columns:
        result[col] = result[col].round(decimals)
    return result


__all__ = [
    "display_frame",
    "round_df",
    "CodeGenerator",
    "CodeSnippet",
    "ColumnType",
    "classify_column",
    "classify_columns",
]
