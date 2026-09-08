"""Data viewing — filter, sort, sample."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from pyanalytica.core.codegen import CodeSnippet


@dataclass
class FilterCondition:
    """A single filter condition."""
    column: str
    operator: str   # "==", "!=", ">", "<", ">=", "<=", "between", "in", "contains", "isnull", "notnull"
    value: Any = None
    value2: Any = None  # For "between"


def apply_filters(
    df: pd.DataFrame,
    filters: list[FilterCondition],
    logic: str = "AND",
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Apply a list of filter conditions to a DataFrame."""
    if not filters:
        return df, CodeSnippet(code="# No filters applied")

    masks = []
    code_parts = []

    for f in filters:
        mask, code = _build_filter(df, f)
        masks.append(mask)
        code_parts.append(code)

    if logic.upper() == "AND":
        combined = masks[0]
        for m in masks[1:]:
            combined = combined & m
        logic_str = " & "
    else:
        combined = masks[0]
        for m in masks[1:]:
            combined = combined | m
        logic_str = " | "

    result = df[combined].copy()

    if len(code_parts) == 1:
        filter_code = code_parts[0]
    else:
        filter_code = logic_str.join(f"({c})" for c in code_parts)

    code = f"df = df[{filter_code}]"
    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


ORDERING = (">", "<", ">=", "<=", "between")


def _is_number(value) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _check_comparable(df: pd.DataFrame, col: str, operator: str, value) -> None:
    """Refuse a comparison that cannot mean what was typed.

    The same mistake used to produce three different answers, none of them a
    message. On a 41,188-row campaign file:

      age == "Mobile"     -> 0 rows, which reads as "no records match"
      age >  "Mobile"     -> a raw TypeError traceback
      channel > "60"      -> all 41,188 rows, because "Mobile" sorts after "60"

    The last is the dangerous one: a filter that cannot mean anything silently
    returns the whole dataset, and every count taken afterwards is wrong.
    """
    if value is None:
        return
    series = df[col]

    if pd.api.types.is_numeric_dtype(series) and not _is_number(value):
        raise ValueError(
            f"'{col}' holds numbers, and {value!r} is not one, so this filter "
            f"cannot match anything. Type a number, or filter a text column "
            f"instead."
        )

    is_text = pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)
    if is_text and operator in ORDERING and _is_number(value):
        example = series.dropna().astype(str)
        sample = repr(example.iloc[0]) if len(example) else "a value"
        raise ValueError(
            f"'{col}' holds text, so {operator} compares it alphabetically, not "
            f"by size: {sample} counts as greater than {str(value)!r} and this "
            f"filter would return nearly every row. Use = or contains on a text "
            f"column, or {operator} on a numeric one."
        )


def check_filter(df: pd.DataFrame, f: FilterCondition) -> None:
    """Raise ValueError if *f* cannot mean anything against *df*.

    Public so the panel can refuse a filter as it is added, rather than
    accepting it and breaking every output that reads the frame afterwards.
    """
    _build_filter(df, f)


def _build_filter(df: pd.DataFrame, f: FilterCondition) -> tuple[pd.Series, str]:
    """Build a boolean mask and code string for a single filter."""
    col = f.column
    if col not in df.columns:
        raise ValueError(
            f"There is no column called '{col}' in this dataset. It may have "
            f"been renamed or dropped since the filter was added."
        )
    if f.operator not in ("isnull", "notnull", "contains", "in"):
        _check_comparable(df, col, f.operator, f.value)
        if f.operator == "between":
            _check_comparable(df, col, f.operator, f.value2)

    if f.operator == "==":
        val = _coerce(f.value, df[col].dtype)
        return df[col] == val, f'df["{col}"] == {_repr_val(val)}'

    elif f.operator == "!=":
        val = _coerce(f.value, df[col].dtype)
        return df[col] != val, f'df["{col}"] != {_repr_val(val)}'

    elif f.operator == ">":
        val = _coerce(f.value, df[col].dtype)
        return df[col] > val, f'df["{col}"] > {_repr_val(val)}'

    elif f.operator == "<":
        val = _coerce(f.value, df[col].dtype)
        return df[col] < val, f'df["{col}"] < {_repr_val(val)}'

    elif f.operator == ">=":
        val = _coerce(f.value, df[col].dtype)
        return df[col] >= val, f'df["{col}"] >= {_repr_val(val)}'

    elif f.operator == "<=":
        val = _coerce(f.value, df[col].dtype)
        return df[col] <= val, f'df["{col}"] <= {_repr_val(val)}'

    elif f.operator == "between":
        lo = _coerce(f.value, df[col].dtype)
        hi = _coerce(f.value2, df[col].dtype)
        return df[col].between(lo, hi), f'df["{col}"].between({_repr_val(lo)}, {_repr_val(hi)})'

    elif f.operator == "in":
        vals = f.value if isinstance(f.value, list) else [f.value]
        # Everything typed into the UI arrives as text. Without this, "in
        # 60, 61" against a numeric column matched nothing and said nothing,
        # while == 60 on the same column worked.
        vals = [_coerce(v, df[col].dtype) for v in vals]
        return df[col].isin(vals), f'df["{col}"].isin({vals!r})'

    elif f.operator == "contains":
        return (
            df[col].astype(str).str.contains(str(f.value), case=False, na=False),
            f'df["{col}"].str.contains("{f.value}", case=False, na=False)',
        )

    elif f.operator == "isnull":
        return df[col].isna(), f'df["{col}"].isna()'

    elif f.operator == "notnull":
        return df[col].notna(), f'df["{col}"].notna()'

    else:
        raise ValueError(f"Unknown operator: {f.operator}")


def sort_dataframe(
    df: pd.DataFrame,
    sort_cols: list[str],
    ascending: list[bool] | None = None,
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Sort a DataFrame by one or more columns."""
    if ascending is None:
        ascending = [True] * len(sort_cols)

    result = df.sort_values(sort_cols, ascending=ascending).copy()

    if len(sort_cols) == 1:
        asc_str = str(ascending[0])
        code = f'df = df.sort_values("{sort_cols[0]}", ascending={asc_str})'
    else:
        code = f"df = df.sort_values({sort_cols!r}, ascending={ascending!r})"

    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


def sample_dataframe(df: pd.DataFrame, n: int = 100) -> pd.DataFrame:
    """Return a random sample of the DataFrame."""
    if len(df) <= n:
        return df
    return df.sample(n=n, random_state=42)


def _coerce(value: Any, dtype: Any) -> Any:
    """Coerce a value to match column dtype."""
    try:
        if pd.api.types.is_numeric_dtype(dtype):
            return float(value)
    except (ValueError, TypeError):
        pass
    return value


def _repr_val(val: Any) -> str:
    """Represent a value for code generation."""
    if isinstance(val, str):
        return f'"{val}"'
    return repr(val)
