"""What an Ask panel hands back: the answer, then the rungs below it.

The shape of a student's question picks the method. A top teaching tool
(JMP's "Fit Y by X" is the canonical case) reads the variable types and opens
the right analysis, then lays the result out as a ladder: describe it, draw
it, test it, model it. Each rung here is one step of that ladder, and the
panel shows the first and offers the rest behind disclosure sections.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pandas as pd

from pyanalytica.core.codegen import CodeSnippet
from pyanalytica.core.types import ColumnType, classify_column, is_groupable

if TYPE_CHECKING:
    from matplotlib.figure import Figure


#: How a column may be read. "auto" uses the groupable rule: a numeric column
#: with twelve or fewer whole-number levels is a category to a student.
TREAT_CHOICES = {"auto": "Auto", "number": "Number", "category": "Category"}

#: Above this many distinct values a column cannot be read as categories.
MAX_CATEGORY_LEVELS = 30


@dataclass
class Rung:
    """One step of the ladder: a sentence, a table, a figure, the code."""
    title: str
    sentence: str = ""
    table: pd.DataFrame | None = None
    figure: "Figure | None" = None
    code: CodeSnippet | None = None
    #: Assumption lines and caveats, one sentence each.
    notes: list[str] = field(default_factory=list)


@dataclass
class AskResult:
    """The whole ladder for one question."""
    kind: str
    question: str
    #: How the columns were read, and why, in one sentence a student can act on.
    reading: str
    answer: Rung
    picture: Rung | None = None
    test: Rung | None = None
    model: Rung | None = None
    next_steps: list[str] = field(default_factory=list)
    #: Every rung's code in order, for Show Code and Add to Report.
    code: CodeSnippet = field(default_factory=lambda: CodeSnippet(code=""))
    #: Short label for the procedure recorder and the report cell.
    description: str = ""

    def rungs(self) -> list[Rung]:
        return [r for r in (self.answer, self.picture, self.test, self.model) if r is not None]


def resolve_kind(series: pd.Series, treat: str = "auto") -> str:
    """Decide whether a column is read as a ``number`` or a ``category``.

    Raises ValueError with a sentence that names the column and says what to
    do instead, since the panel shows that sentence to the student.
    """
    name = series.name
    n_unique = int(series.dropna().nunique())

    if treat == "number":
        if not pd.api.types.is_numeric_dtype(series):
            raise ValueError(
                f'"{name}" holds text, so it cannot be read as a number. '
                f'Read it as a category, or convert it in Data > Transform.'
            )
        return "number"

    if treat == "category":
        if n_unique > MAX_CATEGORY_LEVELS:
            raise ValueError(
                f'"{name}" has {n_unique} distinct values, too many to read as '
                f'categories. Read it as a number, or bin it in Data > Transform.'
            )
        return "category"

    kind = classify_column(series)
    if kind == ColumnType.DATETIME:
        raise ValueError(
            f'"{name}" is a date. Describe > Timeline is the panel for how a '
            f'value changes over time.'
        )
    if kind == ColumnType.ID:
        raise ValueError(
            f'"{name}" looks like an identifier: every row is different, so '
            f'there is nothing to summarise. Choose another column.'
        )
    if kind == ColumnType.TEXT:
        raise ValueError(
            f'"{name}" is free text with {n_unique} distinct values. Choose a '
            f'column with a small number of categories, or a number.'
        )
    if is_groupable(series):
        return "category"
    return "number"


def reading_sentence(series: pd.Series, kind: str, treat: str, role: str) -> str:
    """Say how a column was read, and flag the case a student may not expect."""
    name = series.name
    numeric = pd.api.types.is_numeric_dtype(series)
    if treat == "auto" and kind == "category" and numeric:
        levels = int(series.dropna().nunique())
        return (
            f'"{name}" is numeric but has only {levels} distinct whole-number '
            f'values, so it is read as categories. Set "Treat {role} as" to '
            f'Number to change that.'
        )
    if treat != "auto":
        return f'"{name}" is read as a {kind}, as you asked.'
    return f'"{name}" is read as a {kind}.'


def combine_code(rungs: list[Rung]) -> CodeSnippet:
    """Every rung's code in order, each under a heading, imports merged."""
    parts: list[str] = []
    imports: list[str] = []
    for rung in rungs:
        if rung.code is None or not rung.code.code.strip():
            continue
        parts.append(f"# --- {rung.title} ---\n{rung.code.code}")
        imports.extend(rung.code.imports)
    return CodeSnippet(code="\n\n".join(parts), imports=sorted(set(imports)))


def fmt(value: float) -> str:
    """A number as a student would write it in a sentence."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    if abs(v) >= 10:
        return f"{v:,.1f}"
    return f"{v:.3g}"


def strength(r: float) -> str:
    """The same word scale Advanced > Correlation uses."""
    a = abs(r)
    if a < 0.1:
        return "negligible"
    if a < 0.3:
        return "weak"
    if a < 0.5:
        return "moderate"
    if a < 0.7:
        return "strong"
    return "very strong"
