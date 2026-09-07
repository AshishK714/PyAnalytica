"""Pivot tables with margins and normalization."""

from __future__ import annotations

import pandas as pd

from pyanalytica.core.codegen import CodeSnippet


def create_pivot_table(
    df: pd.DataFrame,
    index: str | list[str],
    columns: str | None,
    values: str,
    aggfunc: str = "count",
    margins: bool = True,
    normalize: str | None = None,
) -> tuple[pd.DataFrame, CodeSnippet]:
    """Create a pivot table.

    normalize: None, 'index' (row %), 'columns' (col %), 'all' (total %)
    When columns is None, produces a simple groupby aggregation.
    """
    idx_str = f'"{index}"' if isinstance(index, str) else repr(index)

    if columns is None:
        # Simple groupby aggregation (no column variable)
        idx_list = [index] if isinstance(index, str) else index
        overlap = values in idx_list
        val_col = f"{values}_{aggfunc}" if overlap else values
        agg_series = df.groupby(idx_list, observed=True)[values].agg(aggfunc)
        agg_series.name = val_col
        result = agg_series.reset_index()

        if margins:
            total_row = {col: "Total" if col == idx_list[0] else "" for col in idx_list}
            if aggfunc in ("count", "sum"):
                total_row[val_col] = result[val_col].sum()
            elif aggfunc in ("mean", "median"):
                total_row[val_col] = getattr(df[values], aggfunc)()
            elif aggfunc == "min":
                total_row[val_col] = result[val_col].min()
            elif aggfunc == "max":
                total_row[val_col] = result[val_col].max()
            else:
                total_row[val_col] = result[val_col].sum()
            total_df = pd.DataFrame([total_row])
            result = pd.concat([result, total_df], ignore_index=True)

        if normalize and aggfunc == "count":
            data_rows = result.iloc[:-1] if margins else result
            total = data_rows[val_col].sum()
            if total > 0:
                result[val_col] = result[val_col].astype(float) / float(total) * 100

        code = (
            f"result = df.groupby({idx_str}, observed=True)"
            f'["{values}"].agg("{aggfunc}").reset_index()'
        )
        if normalize:
            code += f'\nresult["{values}"] = result["{values}"] / result["{values}"].sum() * 100'

        return result, CodeSnippet(code=code, imports=["import pandas as pd"])

    # Two-variable pivot table
    result = pd.pivot_table(
        df,
        index=index,
        columns=columns,
        values=values,
        aggfunc=aggfunc,
        margins=margins,
        observed=True,
    )

    if normalize and aggfunc == "count":
        # With margins on, the last column holds the row totals and the last row
        # the column totals. Dividing by a sum that includes them counts every
        # cell twice: that halved every percentage and made each row total 50%.
        body_cols = result.iloc[:, :-1] if margins else result
        body_rows = result.iloc[:-1, :] if margins else result
        if normalize == "index":
            # Row percentages
            result = result.div(body_cols.sum(axis=1), axis=0) * 100
        elif normalize == "columns":
            # Column percentages
            result = result.div(body_rows.sum(axis=0), axis=1) * 100
        elif normalize == "all":
            total = result.iloc[:-1, :-1].sum().sum() if margins else result.sum().sum()
            result = result / total * 100

    # Generate code
    margins_str = f", margins={margins}" if margins else ""
    code = (
        f"result = pd.pivot_table(\n"
        f"    df,\n"
        f"    index={idx_str},\n"
        f'    columns="{columns}",\n'
        f'    values="{values}",\n'
        f'    aggfunc="{aggfunc}"{margins_str}\n'
        f")"
    )

    if normalize:
        # The slices drop the margin row/column from the divisor only.
        body_c = "result.iloc[:, :-1]" if margins else "result"
        body_r = "result.iloc[:-1, :]" if margins else "result"
        body_a = "result.iloc[:-1, :-1]" if margins else "result"
        if normalize == "index":
            code += f"\nresult = result.div({body_c}.sum(axis=1), axis=0) * 100"
        elif normalize == "columns":
            code += f"\nresult = result.div({body_r}.sum(axis=0), axis=1) * 100"
        elif normalize == "all":
            code += f"\nresult = result / {body_a}.sum().sum() * 100"

    return result, CodeSnippet(code=code, imports=["import pandas as pd"])
