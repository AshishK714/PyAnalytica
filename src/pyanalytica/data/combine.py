"""Data combining — merge/join, append, reshape (wide/long)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from pyanalytica.core.codegen import CodeSnippet


@dataclass
class OverlapInfo:
    """Diagnostics for a single overlapping (non-key) column."""
    column: str
    total_comparable: int   # rows where both sides have non-null values
    n_same: int             # values that match
    n_different: int        # values that differ
    pct_same: float         # percentage same (0-100)


@dataclass
class MergeResult:
    """Result of a merge operation with diagnostics."""
    merged: pd.DataFrame
    left_unmatched: int
    right_unmatched: int
    result_rows: int
    code: CodeSnippet


def detect_overlapping_columns(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on: str | list[str],
) -> list[OverlapInfo]:
    """Find non-key columns common to both DataFrames and compare values.

    Returns one OverlapInfo per overlapping column with match statistics.
    """
    on_list = [on] if isinstance(on, str) else list(on)
    left_cols = set(left.columns) - set(on_list)
    right_cols = set(right.columns) - set(on_list)
    overlap = sorted(left_cols & right_cols)

    if not overlap:
        return []

    # Inner join to get comparable rows
    joined = pd.merge(
        left[on_list + overlap], right[on_list + overlap],
        on=on_list, how="inner", suffixes=("_L", "_R"),
    )

    results: list[OverlapInfo] = []
    for col in overlap:
        left_vals = joined[f"{col}_L"]
        right_vals = joined[f"{col}_R"]
        # Only compare where both are non-null
        both_present = left_vals.notna() & right_vals.notna()
        total = int(both_present.sum())
        if total > 0:
            same = int((left_vals[both_present] == right_vals[both_present]).sum())
        else:
            same = 0
        diff = total - same
        pct = (same / total * 100) if total > 0 else 0.0
        results.append(OverlapInfo(
            column=col,
            total_comparable=total,
            n_same=same,
            n_different=diff,
            pct_same=round(pct, 1),
        ))
    return results


def merge_dataframes(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on: str | list[str],
    how: str = "inner",
    left_name: str = "left",
    right_name: str = "right",
    keep: dict[str, str] | None = None,
    suffixes: tuple[str, str] = ("_x", "_y"),
) -> MergeResult:
    """Merge two DataFrames with diagnostics.

    how: 'inner', 'left', 'right', 'outer'
    keep: dict mapping overlapping column names to
          "left" (keep left copy), "right" (keep right copy),
          or "both" (keep both with suffixes).
    suffixes: tuple of suffixes for overlapping columns kept as "both".
    """
    on_list = [on] if isinstance(on, str) else list(on)
    keep = keep or {}

    # Drop columns according to keep preferences
    drop_from_left = [c for c, side in keep.items() if side == "right"]
    drop_from_right = [c for c, side in keep.items() if side == "left"]

    left_use = left.drop(columns=drop_from_left) if drop_from_left else left
    right_use = right.drop(columns=drop_from_right) if drop_from_right else right

    merged = pd.merge(left_use, right_use, on=on_list, how=how, suffixes=suffixes)

    # Calculate unmatched rows
    indicator_df = pd.merge(left_use, right_use, on=on_list, how="outer", indicator=True)
    left_unmatched = int((indicator_df["_merge"] == "left_only").sum())
    right_unmatched = int((indicator_df["_merge"] == "right_only").sum())

    # Generate code
    on_str = f'"{on}"' if isinstance(on, str) else repr(on)
    code_lines: list[str] = []

    if drop_from_left:
        cols_str = repr(drop_from_left)
        code_lines.append(
            f"{left_name} = {left_name}.drop(columns={cols_str})"
        )
    if drop_from_right:
        cols_str = repr(drop_from_right)
        code_lines.append(
            f"{right_name} = {right_name}.drop(columns={cols_str})"
        )

    suffixes_str = ""
    if suffixes != ("_x", "_y"):
        suffixes_str = f',\n    suffixes={suffixes!r}'

    code_lines.append(
        f"merged = pd.merge(\n"
        f"    {left_name}, {right_name},\n"
        f"    on={on_str},\n"
        f'    how="{how}"{suffixes_str}\n'
        f")\n"
        f"df = merged  # the dataset every later step works on"
    )

    code = "\n".join(code_lines)

    return MergeResult(
        merged=merged,
        left_unmatched=left_unmatched,
        right_unmatched=right_unmatched,
        result_rows=len(merged),
        code=CodeSnippet(code=code, imports=["import pandas as pd"]),
    )


def append_dataframes(
    dfs: list[pd.DataFrame],
    names: list[str],
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Append (concatenate) multiple DataFrames vertically."""
    result = pd.concat(dfs, ignore_index=True)

    names_str = ", ".join(names)
    code = (
        f"combined = pd.concat([{names_str}], ignore_index=True)\n"
        f"df = combined  # the dataset every later step works on"
    )

    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


def pivot_wider(
    df: pd.DataFrame,
    id_cols: str | list[str],
    names_from: str,
    values_from: str,
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Reshape from long to wide format."""
    result = df.pivot_table(
        index=id_cols, columns=names_from, values=values_from, aggfunc="first"
    ).reset_index()

    # Flatten multi-level column index
    if hasattr(result.columns, "levels"):
        result.columns = [
            col[1] if col[1] else col[0]
            for col in result.columns
        ]

    id_str = f'"{id_cols}"' if isinstance(id_cols, str) else repr(id_cols)
    code = (
        f"wide = df.pivot_table(\n"
        f"    index={id_str},\n"
        f'    columns="{names_from}",\n'
        f'    values="{values_from}",\n'
        f'    aggfunc="first"\n'
        f").reset_index()"
    )

    return result, CodeSnippet(code=code, imports=["import pandas as pd"])


def pivot_longer(
    df: pd.DataFrame,
    id_cols: str | list[str],
    value_vars: list[str],
    var_name: str = "variable",
    value_name: str = "value",
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Reshape from wide to long format."""
    id_list = [id_cols] if isinstance(id_cols, str) else id_cols

    result = pd.melt(
        df,
        id_vars=id_list,
        value_vars=value_vars,
        var_name=var_name,
        value_name=value_name,
    )

    id_str = repr(id_list)
    code = (
        f"long = pd.melt(\n"
        f"    df,\n"
        f"    id_vars={id_str},\n"
        f"    value_vars={value_vars!r},\n"
        f'    var_name="{var_name}",\n'
        f'    value_name="{value_name}"\n'
        f")"
    )

    return result, CodeSnippet(code=code, imports=["import pandas as pd"])
