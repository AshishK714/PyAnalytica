"""Say what the numbers in a table are.

A table of 32.2581 / 67.7419 / 100 is percentages or counts depending on a
dropdown in the sidebar, and nothing in the output says which. Scroll, export
it, or paste it into a report and even that clue is gone. The caption states the
reading in one line, above the table, where it travels with a screenshot.

Deliberately not a "%" suffix inside the cells: that turns the column into text,
so the grid stops sorting it numerically and `round_df()` -- which only touches
numeric columns -- stops honouring the decimals control on exactly the figures
that need it.

The caption describes what the table *did*, not what the controls were set to.
Those differ: `create_pivot_table` applies Normalize only when the aggregation
is a count, so asking for the mean and Row % gives means. Saying "row
percentages" over a table of means would be a caption that lies.
"""

from __future__ import annotations

NORMALIZE_READINGS = {
    "index": ("Row percentages", "each row totals 100"),
    "columns": ("Column percentages", "each column totals 100"),
    "all": ("Percentages of the whole table", "all cells total 100"),
}


def table_caption(
    normalize: str | None,
    *,
    aggfunc: str | None = None,
    value_col: str | None = None,
    margins: bool = False,
) -> str:
    """One line describing what a cell in this table holds."""
    # Cross-tab has no aggregation to choose: it counts, so a normalize
    # setting always applies. Pivot passes one, and there it only applies to
    # counts.
    normalize_applies = normalize and (aggfunc is None or aggfunc == "count")
    reading = NORMALIZE_READINGS.get(normalize or "") if normalize_applies else None

    parts: list[str] = []
    if reading:
        headline, total = reading
        parts.append(f"{headline} — {total}.")
        if value_col:
            parts.append(f"Based on counts of {value_col}.")
        if margins:
            parts.append(
                'The "All" row and column are totals; they are not part of the '
                "base each percentage is taken over."
            )
    elif normalize and aggfunc and aggfunc != "count":
        # The control was set and had no effect. Say so, rather than let the
        # sidebar imply a reading the table does not have.
        shown = f"{aggfunc.capitalize()} of {value_col}." if value_col else f"{aggfunc.capitalize()}."
        parts.append(shown)
        parts.append(
            f"Normalize applies to counts only, so these are {aggfunc} values, "
            f"not percentages."
        )
    elif aggfunc and aggfunc != "count":
        parts.append(f"{aggfunc.capitalize()} of {value_col}." if value_col
                     else f"{aggfunc.capitalize()}.")
    else:
        parts.append(f"Counts of {value_col}." if value_col else "Counts.")
        if margins:
            parts.append('The "All" row and column are totals.')

    return " ".join(parts)
