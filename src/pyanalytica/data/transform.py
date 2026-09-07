"""Data transformation — missing values, dtypes, duplicates, new columns, string ops."""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from pyanalytica.core.codegen import CodeSnippet


# --- Expression validation ---

_FORBIDDEN_NAMES = frozenset({
    "import", "exec", "eval", "compile", "open", "getattr",
    "setattr", "delattr", "globals", "locals", "vars", "dir",
    "breakpoint", "exit", "quit", "input", "print",
})

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _validate_expr(expr: str) -> None:
    """Reject expressions containing dangerous names for df.eval().

    Matching is on whole identifiers rather than substrings, so ordinary column
    names such as ``open_rate``, ``direct_cost`` or ``exit_survey`` are allowed.
    """
    if "__" in expr:
        raise ValueError(
            "Expression may not contain '__'. "
            "Only arithmetic on column names is allowed."
        )
    for name in _IDENT_RE.findall(expr):
        if name in _FORBIDDEN_NAMES:
            raise ValueError(
                f"Expression contains forbidden name '{name}'. "
                "Only arithmetic on column names is allowed."
            )


# --- Column type helpers ---

def _dtype_label(s: pd.Series) -> str:
    """Human-readable description of a column's type, for error messages."""
    if pd.api.types.is_bool_dtype(s):
        return "true/false"
    if pd.api.types.is_numeric_dtype(s):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "datetime"
    if isinstance(s.dtype, pd.CategoricalDtype):
        return "categorical"
    return "text"


def _require_numeric(df: pd.DataFrame, col: str, what: str) -> None:
    """Raise a readable error if *col* is not numeric."""
    if not pd.api.types.is_numeric_dtype(df[col]):
        raise ValueError(
            f"{what} needs a numeric column, but '{col}' is "
            f"{_dtype_label(df[col])}. Convert it with Convert Data Type first."
        )


def _require_text(df: pd.DataFrame, col: str, what: str) -> None:
    """Raise a readable error if *col* holds numbers or dates rather than text."""
    s = df[col]
    if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s):
        raise ValueError(
            f"{what} needs a text column, but '{col}' is {_dtype_label(s)}."
        )


def _reject_coercion_loss(
    original: pd.Series, converted: pd.Series, col: str, kind: str, hint: str
) -> None:
    """Raise if a coercion silently turned real values into nulls.

    pandas' ``errors="coerce"`` is convenient but destructive: an unparseable
    value becomes NaN with no signal. Refuse the conversion instead.
    """
    lost_mask = converted.isna() & original.notna()
    lost = int(lost_mask.sum())
    if not lost:
        return
    total = int(original.notna().sum())
    sample = original[lost_mask].iloc[0]
    raise ValueError(
        f"Cannot convert '{col}' to {kind}: {lost} of {total} values are not "
        f"valid (for example {sample!r}). The column was left unchanged. {hint}"
    )


_TRUE_TOKENS = frozenset({"true", "t", "yes", "y", "1"})
_FALSE_TOKENS = frozenset({"false", "f", "no", "n", "0"})


def _to_boolean(s: pd.Series, col: str) -> pd.Series:
    """Convert a column to nullable booleans by meaning, not by truthiness.

    ``astype(bool)`` maps every non-empty string to True, so "No" and "False"
    would both become True. Map recognised tokens instead and refuse the rest.
    """
    if pd.api.types.is_bool_dtype(s):
        return s.astype("boolean")
    if pd.api.types.is_numeric_dtype(s):
        return s.astype("boolean")

    tokens = s.astype("string").str.strip().str.lower()
    mapped = tokens.map(
        lambda t: True if t in _TRUE_TOKENS else (False if t in _FALSE_TOKENS else pd.NA),
        na_action="ignore",
    )
    unrecognised = mapped.isna() & s.notna()
    if unrecognised.any():
        examples = sorted({str(v) for v in s[unrecognised]})[:4]
        raise ValueError(
            f"Cannot convert '{col}' to true/false: {int(unrecognised.sum())} values "
            f"are not recognisable (for example {examples}). "
            "Recognised values are yes/no, true/false, y/n and 1/0."
        )
    return mapped.astype("boolean")


# --- Missing values ---

def fill_missing(
    df: pd.DataFrame, col: str, method: str, value: Any = None
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Fill missing values in a column.

    Methods: 'value', 'mean', 'median', 'mode', 'ffill', 'bfill'
    """
    result = df.copy()

    if method == "value":
        result[col] = result[col].fillna(value)
        code = f'df["{col}"] = df["{col}"].fillna({_repr_val(value)})'
    elif method == "mean":
        _require_numeric(df, col, "Filling with the mean")
        fill_val = result[col].mean()
        result[col] = result[col].fillna(fill_val)
        code = f'df["{col}"] = df["{col}"].fillna(df["{col}"].mean())'
    elif method == "median":
        _require_numeric(df, col, "Filling with the median")
        fill_val = result[col].median()
        result[col] = result[col].fillna(fill_val)
        code = f'df["{col}"] = df["{col}"].fillna(df["{col}"].median())'
    elif method == "mode":
        modes = result[col].mode()
        if modes.empty:
            raise ValueError(
                f"Column '{col}' has no non-missing values, so it has no mode."
            )
        result[col] = result[col].fillna(modes.iloc[0])
        code = f'df["{col}"] = df["{col}"].fillna(df["{col}"].mode().iloc[0])'
    elif method == "ffill":
        result[col] = result[col].ffill()
        code = f'df["{col}"] = df["{col}"].ffill()'
    elif method == "bfill":
        result[col] = result[col].bfill()
        code = f'df["{col}"] = df["{col}"].bfill()'
    else:
        raise ValueError(f"Unknown fill method: {method}")

    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


def drop_missing(
    df: pd.DataFrame, cols: list[str] | None = None, how: str = "any"
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Drop rows with missing values."""
    if cols:
        result = df.dropna(subset=cols, how=how).copy()
        code = f'df = df.dropna(subset={cols!r}, how="{how}")'
    else:
        result = df.dropna(how=how).copy()
        code = f'df = df.dropna(how="{how}")'

    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


# --- Data types ---

def convert_dtype(
    df: pd.DataFrame, col: str, target_dtype: str
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Convert a column to a different dtype.

    target_dtype: 'int', 'float', 'str', 'category', 'datetime', 'bool'

    Conversions that would turn real values into nulls are refused rather than
    applied, so a column is never silently emptied.
    """
    result = df.copy()
    numeric_hint = (
        "Remove stray characters first — String: Replace will strip things "
        "like '%', ',' or '$'."
    )

    if target_dtype == "int":
        numeric = pd.to_numeric(result[col], errors="coerce")
        _reject_coercion_loss(result[col], numeric, col, "a whole number", numeric_hint)
        fractional = numeric.dropna() % 1 != 0
        if fractional.any():
            raise ValueError(
                f"Cannot convert '{col}' to a whole number: {int(fractional.sum())} "
                "values have decimals and would be silently truncated. "
                "Convert to float instead, or round the column first."
            )
        result[col] = numeric.astype("Int64")
        code = f'df["{col}"] = pd.to_numeric(df["{col}"]).astype("Int64")'
    elif target_dtype == "float":
        numeric = pd.to_numeric(result[col], errors="coerce")
        _reject_coercion_loss(result[col], numeric, col, "a number", numeric_hint)
        result[col] = numeric.astype(float)
        code = f'df["{col}"] = pd.to_numeric(df["{col}"]).astype(float)'
    elif target_dtype == "str":
        result[col] = result[col].astype(str)
        code = f'df["{col}"] = df["{col}"].astype(str)'
    elif target_dtype == "category":
        result[col] = result[col].astype("category")
        code = f'df["{col}"] = df["{col}"].astype("category")'
    elif target_dtype == "datetime":
        converted = pd.to_datetime(result[col], errors="coerce")
        _reject_coercion_loss(
            result[col], converted, col, "a date",
            "Check the date format is consistent down the column.",
        )
        result[col] = converted
        code = f'df["{col}"] = pd.to_datetime(df["{col}"])'
    elif target_dtype == "bool":
        result[col] = _to_boolean(result[col], col)
        code = (
            f'_true = {{"true", "t", "yes", "y", "1"}}\n'
            f'df["{col}"] = (\n'
            f'    df["{col}"].astype("string").str.strip().str.lower().isin(_true)\n'
            f")"
        )
    else:
        raise ValueError(f"Unknown target dtype: {target_dtype}")

    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


# --- Rename column ---

def rename_column(
    df: pd.DataFrame, old_name: str, new_name: str
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Rename a single column."""
    result = df.rename(columns={old_name: new_name})
    code = f'df = df.rename(columns={{"{old_name}": "{new_name}"}})'
    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


# --- Drop columns ---

def drop_columns(
    df: pd.DataFrame, cols: list[str]
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Drop one or more columns from a DataFrame."""
    result = df.drop(columns=cols).copy()
    code = f"df = df.drop(columns={cols!r})"
    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


# --- Duplicates ---

def drop_duplicates(
    df: pd.DataFrame, cols: list[str] | None = None, keep: str = "first"
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Drop duplicate rows."""
    if cols:
        result = df.drop_duplicates(subset=cols, keep=keep).copy()
        code = f'df = df.drop_duplicates(subset={cols!r}, keep="{keep}")'
    else:
        result = df.drop_duplicates(keep=keep).copy()
        code = f'df = df.drop_duplicates(keep="{keep}")'

    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


# --- New columns ---

def add_column_arithmetic(
    df: pd.DataFrame, new_col: str, expr: str
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Add a new column from an arithmetic expression using existing columns.

    expr should reference columns by name, e.g. "salary * 12" or "revenue - cost"
    The expression is evaluated using DataFrame.eval() with input validation.
    """
    _validate_expr(expr)
    result = df.copy()
    result[new_col] = result.eval(expr)
    code = f'df["{new_col}"] = df.eval("{expr}")'
    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


def add_column_conditional(
    df: pd.DataFrame, new_col: str, condition: str,
    true_val: Any, false_val: Any
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Add a column with values based on a condition.

    condition: pandas eval expression, e.g. "salary > 50000"
    """
    _validate_expr(condition)
    result = df.copy()
    mask = result.eval(condition)
    result[new_col] = np.where(mask, true_val, false_val)

    code = (
        f'df["{new_col}"] = np.where(\n'
        f'    df.eval("{condition}"),\n'
        f"    {_repr_val(true_val)},\n"
        f"    {_repr_val(false_val)}\n"
        f")"
    )
    return result, CodeSnippet(code=code, imports=["import numpy as np", "import pandas as pd"])


def _bin_labels(intervals) -> list[str]:
    """Name bins the way a reader would say them: "37.2 to 57.5".

    Uses the coarsest rounding that still tells the bins apart, so narrow bins
    do not all collapse to the same name.
    """
    for places in (1, 2, 3, 4, 6):
        names = [
            f"{round(float(iv.left), places):g} to {round(float(iv.right), places):g}"
            for iv in intervals
        ]
        if len(set(names)) == len(names):
            return names
    return [str(iv) for iv in intervals]


def add_column_binned(
    df: pd.DataFrame, new_col: str, source_col: str,
    bins: int | list, labels: list[str] | None = None
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Add a column with binned/discretized values."""
    _require_numeric(df, source_col, "Binning")
    if labels is not None:
        n_bins = bins if isinstance(bins, int) else len(bins) - 1
        if len(labels) != n_bins:
            raise ValueError(
                f"Got {len(labels)} label(s) for {n_bins} bin(s). "
                "Give one label per bin, or leave the labels blank."
            )
    result = df.copy()
    binned = pd.cut(result[source_col], bins=bins, labels=labels)
    shown = labels
    if labels is None:
        # pd.cut names the bins with pandas Interval objects. They are correct,
        # but nothing downstream can serialise them: the data grid raises
        # "Object of type Interval is not JSON serializable" from inside Shiny's
        # renderer, after this module's error handling, so the session wedges with
        # no message at all and the reload it takes to recover costs the student
        # their whole workbench. Name the bins in text, keeping their order.
        shown = _bin_labels(binned.cat.categories)
        binned = binned.cat.rename_categories(shown)
    result[new_col] = binned

    code = (
        f'df["{new_col}"] = pd.cut(df["{source_col}"], '
        f'bins={bins!r}, labels={shown!r})'
    )
    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


def add_column_log(
    df: pd.DataFrame, new_col: str, source_col: str
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Add a log-transformed column."""
    _require_numeric(df, source_col, "A log column")
    result = df.copy()
    source = result[source_col]
    non_positive = int((source.dropna() <= 0).sum())
    if non_positive:
        raise ValueError(
            f"'{source_col}' has {non_positive} value(s) that are zero or negative, "
            "and the logarithm is undefined there. Filter or shift the column first."
        )
    result[new_col] = np.log(source)
    code = f'df["{new_col}"] = np.log(df["{source_col}"])'
    return result, CodeSnippet(code=code, imports=["import numpy as np", "import pandas as pd"])


def add_column_zscore(
    df: pd.DataFrame, new_col: str, source_col: str
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Add a z-score normalized column."""
    _require_numeric(df, source_col, "A z-score column")
    result = df.copy()
    mean = result[source_col].mean()
    std = result[source_col].std()
    if not std or pd.isna(std):
        raise ValueError(
            f"'{source_col}' has no spread (standard deviation is 0), "
            "so a z-score is undefined."
        )
    result[new_col] = (result[source_col] - mean) / std

    code = (
        f'df["{new_col}"] = (\n'
        f'    (df["{source_col}"] - df["{source_col}"].mean()) / df["{source_col}"].std()\n'
        f")"
    )
    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


def add_column_rank(
    df: pd.DataFrame, new_col: str, source_col: str
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Add a rank column."""
    _require_numeric(df, source_col, "A rank column")
    result = df.copy()
    result[new_col] = result[source_col].rank()
    code = f'df["{new_col}"] = df["{source_col}"].rank()'
    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


# --- String operations ---

def str_lower(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, CodeSnippet]:
    """Convert string column to lowercase."""
    _require_text(df, col, "String: Lowercase")
    result = df.copy()
    result[col] = result[col].str.lower()
    code = f'df["{col}"] = df["{col}"].str.lower()'
    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


def str_upper(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, CodeSnippet]:
    """Convert string column to uppercase."""
    _require_text(df, col, "String: Uppercase")
    result = df.copy()
    result[col] = result[col].str.upper()
    code = f'df["{col}"] = df["{col}"].str.upper()'
    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


def str_strip(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, CodeSnippet]:
    """Strip whitespace from string column."""
    _require_text(df, col, "String: Strip Whitespace")
    result = df.copy()
    result[col] = result[col].str.strip()
    code = f'df["{col}"] = df["{col}"].str.strip()'
    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


def str_replace(
    df: pd.DataFrame, col: str, pattern: str, replacement: str = "",
    regex: bool = False
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Replace text within a string column, in place.

    The usual reason to reach for this is clearing characters that stop a column
    being read as a number — a '%' suffix, a thousands comma, a currency symbol.
    """
    _require_text(df, col, "String: Replace")
    if not pattern:
        raise ValueError("Type the text to find.")
    result = df.copy()
    result[col] = (
        result[col].astype("string").str.replace(pattern, replacement, regex=regex)
    )
    code = (
        f'df["{col}"] = df["{col}"].astype("string").str.replace('
        f"{pattern!r}, {replacement!r}, regex={regex})"
    )
    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


def str_extract(
    df: pd.DataFrame, new_col: str, col: str, pattern: str
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Extract substring using regex pattern."""
    _require_text(df, col, "String: Extract")
    if not pattern:
        raise ValueError("Type a pattern to extract.")
    result = df.copy()
    result[new_col] = result[col].astype("string").str.extract(f"({pattern})", expand=False)
    code = (
        f'df["{new_col}"] = df["{col}"].astype("string")'
        f'.str.extract(r"({pattern})", expand=False)'
    )
    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


# --- Encoding ---

def dummy_encode(
    df: pd.DataFrame, column: str, drop_first: bool = False,
    keep_original: bool = False
) -> tuple[pd.DataFrame, CodeSnippet]:
    """One-hot / dummy encode a categorical column.

    By default pandas replaces the source column with its indicator columns.
    Pass ``keep_original=True`` to retain it alongside them.
    """
    result = pd.get_dummies(df, columns=[column], drop_first=drop_first)
    drop_str = ", drop_first=True" if drop_first else ""
    code = f'df = pd.get_dummies(df, columns=["{column}"]{drop_str})'

    if keep_original:
        result.insert(df.columns.get_loc(column), column, df[column])
        code = (
            f"{column}_original = df[\"{column}\"]\n"
            f'df = pd.get_dummies(df, columns=["{column}"]{drop_str})\n'
            f'df.insert({df.columns.get_loc(column)}, "{column}", {column}_original)'
        )

    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


def ordinal_encode(
    df: pd.DataFrame, column: str, order: list[str] | None = None
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Map categories to integers (0, 1, 2, ...).

    If *order* is given, categories are mapped in that order and every category
    present must appear in it — otherwise the omitted ones would silently
    become nulls. If *order* is omitted, sorted unique values are used, which is
    alphabetical and therefore rarely the right ranking for an ordered
    dimension: pass the order explicitly for those.
    """
    result = df.copy()
    present = set(result[column].dropna().unique())

    if order is None:
        order = sorted(present)
    else:
        unlisted = present - set(order)
        if unlisted:
            raise ValueError(
                f"Category order for '{column}' does not mention "
                f"{sorted(str(v) for v in unlisted)}. Every category must be "
                "listed, or leave the order blank to use alphabetical order."
            )

    mapping = {val: i for i, val in enumerate(order)}
    result[column] = result[column].map(mapping)

    code = (
        f'{column}_map = {mapping!r}\n'
        f'df["{column}"] = df["{column}"].map({column}_map)'
    )
    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


def _repr_val(val: Any) -> str:
    """Represent a value for code generation."""
    return repr(val)
