"""Report builder — notebook-style report with code + markdown cells."""

from __future__ import annotations

import base64
import html as html_mod
import io
import json
import logging
import sys
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    from pyanalytica.core.procedure import ProcedureRecorder


#: Output that speaks to the report's author, not its reader. The export
#: drops elements with this class when code is hidden.
NOTE_CLASS = "pa-author-note"


#: The screen's default precision (the decimals control on every panel).
#: Report tables use the same, so a number reads the same in both places.
REPORT_DECIMALS = 4


def _fmt_number(value, decimals: int = REPORT_DECIMALS) -> str:
    """A table cell the way the screen shows it, with thousands separators.

    Rounded to the screen's four decimals, trailing zeros dropped, so 1338
    reads "1,338" and not "1,338.00", and 0.29938 reads "0.2994" as it does
    on screen. A retest found the report and the screen disagreeing on the
    same numbers when the report formatted by its own rules. The one
    departure: a number that rounds to zero but is not zero (a tiny p-value)
    reads "< 0.0001" rather than a zero it is not.
    """
    import math
    import numbers

    if isinstance(value, bool) or not isinstance(value, numbers.Number):
        return str(value)
    v = float(value)
    if math.isnan(v):
        return ""
    floor = 0.5 * 10 ** -decimals
    if v != 0 and abs(v) < floor:
        limit = f"{10 ** -decimals:.{decimals}f}"
        return f"< {limit}" if v > 0 else f"> -{limit}"
    # numpy's rounding, which is what the screen's round_df uses. Python's
    # round() works from the exact binary value and numpy's scales first, so
    # on a value that sits on a half they could differ in the last place:
    # 8965.79575 showed as 8965.7958 on screen and 8,965.7957 in the report.
    import numpy as _np

    r = float(_np.round(v, decimals))
    if r == int(r) and abs(r) < 1e15:
        return f"{int(r):,}"
    return f"{r:,.{decimals}f}".rstrip("0").rstrip(".")


def _table_html(frame) -> str:
    """Render a result table the way a reader expects it.

    pandas' bare 0, 1, 2 row numbers go; a meaningful index (the groups of a
    groupby, the rows of a cross-tab) becomes an ordinary first column rather
    than a second header row; numbers read as they do on screen.
    """
    import pandas as _pd

    frame = frame.copy()
    if not isinstance(frame.index, _pd.RangeIndex):
        try:
            frame = frame.reset_index()
        except ValueError:
            pass  # an index name that is also a column: leave it as it is
    if not isinstance(frame.columns, _pd.MultiIndex):
        frame.columns.name = None
    show_index = not isinstance(frame.index, _pd.RangeIndex)
    return frame.to_html(
        classes="table table-sm table-striped",
        border=0,
        index=show_index,
        formatters={col: _fmt_number for col in frame.columns},
    )


def _error_html(e: Exception) -> str:
    return (
        f'<pre style="background:#fff3e0;border-left:3px solid #e53935;'
        f'padding:8px 12px;font-size:0.82rem;color:#c62828;'
        f'margin:4px 0;border-radius:0 4px 4px 0;">'
        f'{type(e).__name__}: {html_mod.escape(str(e))}</pre>'
    )


class CellType(Enum):
    """Type of cell in a report."""
    CODE = "code"
    MARKDOWN = "markdown"


@dataclass
class ReportCell:
    """A single cell in a report."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    order: int = 0
    cell_type: CellType = CellType.CODE
    enabled: bool = True
    # Code cell fields
    action: str = ""
    description: str = ""
    code: str = ""
    imports: list[str] = field(default_factory=list)
    # Markdown cell fields
    markdown: str = ""
    # Execution output (HTML fragment)
    output_html: str = ""


class ReportBuilder:
    """Builds a notebook-style report from procedure steps and markdown cells."""

    def __init__(self) -> None:
        self._cells: list[ReportCell] = []
        self.title: str = "PyAnalytica Report"
        self.author: str = ""

    def get_cells(self) -> list[ReportCell]:
        return list(self._cells)

    def cell_count(self) -> int:
        return len(self._cells)

    def _renumber(self) -> None:
        for i, c in enumerate(self._cells):
            c.order = i + 1

    def import_from_recorder(self, recorder: ProcedureRecorder) -> int:
        """Import procedure steps as code cells. Returns number imported."""
        steps = recorder.get_steps()
        count = 0
        for s in steps:
            cell = ReportCell(
                order=len(self._cells) + 1,
                cell_type=CellType.CODE,
                enabled=s.enabled,
                action=s.action,
                description=s.description,
                code=s.code,
                imports=list(s.imports),
            )
            self._cells.append(cell)
            count += 1
        self._renumber()
        return count

    def add_code_cell(self, *, action: str = "", description: str = "",
                      code: str = "", imports: list[str] | None = None) -> ReportCell:
        """Append a code cell directly (used by 'Add to Report' feature)."""
        cell = ReportCell(
            order=len(self._cells) + 1,
            cell_type=CellType.CODE,
            action=action,
            description=description,
            code=code,
            imports=list(imports or []),
        )
        self._cells.append(cell)
        self._renumber()
        return cell

    def add_markdown_cell(self, after_cell_id: str | None = None, markdown: str = "") -> ReportCell:
        """Insert a markdown cell. If after_cell_id is given, insert after that cell."""
        cell = ReportCell(
            cell_type=CellType.MARKDOWN,
            markdown=markdown,
        )
        if after_cell_id is None:
            self._cells.append(cell)
        else:
            idx = self._find_index(after_cell_id)
            if idx is not None:
                self._cells.insert(idx + 1, cell)
            else:
                self._cells.append(cell)
        self._renumber()
        return cell

    def add_title_cell(self) -> ReportCell:
        """Insert a title markdown cell at position 0."""
        cell = ReportCell(
            cell_type=CellType.MARKDOWN,
            markdown=f"# {self.title}\n\n*Author: {self.author or 'N/A'}*",
        )
        self._cells.insert(0, cell)
        self._renumber()
        return cell

    def remove_cell(self, cell_id: str) -> None:
        self._cells = [c for c in self._cells if c.id != cell_id]
        self._renumber()

    def move_cell_to(self, cell_id: str, position: int) -> None:
        """Move a cell to a 1-based position, clamped to the ends.

        One step per click was the only way to reorder, and arranging a
        report from cells added in the order the work happened took dozens
        of clicks, each redrawing the whole builder.
        """
        idx = self._find_index(cell_id)
        if idx is None:
            return
        cell = self._cells.pop(idx)
        target = max(0, min(int(position) - 1, len(self._cells)))
        self._cells.insert(target, cell)
        self._renumber()

    def move_cell(self, cell_id: str, direction: str) -> None:
        """Move a cell 'up' or 'down'."""
        idx = self._find_index(cell_id)
        if idx is None:
            return
        if direction == "up" and idx > 0:
            self._cells[idx], self._cells[idx - 1] = self._cells[idx - 1], self._cells[idx]
        elif direction == "down" and idx < len(self._cells) - 1:
            self._cells[idx], self._cells[idx + 1] = self._cells[idx + 1], self._cells[idx]
        self._renumber()

    def toggle_cell(self, cell_id: str) -> None:
        for c in self._cells:
            if c.id == cell_id:
                c.enabled = not c.enabled
                break

    def update_description(self, cell_id: str, text: str) -> None:
        """Rename a code cell. The description is the heading the reader view
        prints, so it has to be the author's to write, not only the panel's."""
        text = (text or "").strip()
        if not text:
            return  # an empty heading would leave the step unnamed in the editor
        for c in self._cells:
            if c.id == cell_id and c.cell_type == CellType.CODE:
                c.description = text
                break

    def update_markdown(self, cell_id: str, text: str) -> None:
        for c in self._cells:
            if c.id == cell_id and c.cell_type == CellType.MARKDOWN:
                c.markdown = text
                break

    def clear(self) -> None:
        self._cells = []

    def _find_index(self, cell_id: str) -> int | None:
        for i, c in enumerate(self._cells):
            if c.id == cell_id:
                return i
        return None

    # --- Code execution ---

    def execute_all(self, df: pd.DataFrame | None = None) -> list[str]:
        """Execute all enabled code cells in order, capturing output.

        Parameters
        ----------
        df : DataFrame or None
            The current dataset, made available as ``df`` in the code.

        Returns
        -------
        list[str]
            A message per executed cell (success or error).
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as _pd

        # Restrict builtins to prevent access to dangerous functions
        _blocked = {
            "exec", "eval", "compile",
            "open", "input", "breakpoint", "exit", "quit",
            "getattr", "setattr", "delattr", "globals", "locals",
            "vars",
        }
        _safe_builtins = {
            k: v for k, v in __builtins__.items()
            if k not in _blocked
        } if isinstance(__builtins__, dict) else {
            k: getattr(__builtins__, k) for k in dir(__builtins__)
            if k not in _blocked and not k.startswith("_")
        }
        # Allow __import__ so that import statements in cell code work
        import builtins as _bi
        _safe_builtins["__import__"] = _bi.__import__

        # Pre-import common libraries so cell code can use them
        try:
            import seaborn as _sns
        except ImportError:
            _sns = None
        try:
            from scipy import stats as _stats
        except ImportError:
            _stats = None

        namespace: dict = {
            "__builtins__": _safe_builtins,
            "pd": _pd,
            "np": np,
            "plt": plt,
        }
        if _sns is not None:
            namespace["sns"] = _sns
        if _stats is not None:
            namespace["stats"] = _stats
        # Provide the current dataframe
        if df is not None:
            namespace["df"] = df.copy()

        messages: list[str] = []

        for cell in self._cells:
            if not cell.enabled or cell.cell_type != CellType.CODE:
                continue

            # Execute imports (use real builtins so import statements work)
            import builtins as _builtins_mod
            _import_ns = {"__builtins__": _builtins_mod}
            for imp in cell.imports:
                try:
                    exec(imp, _import_ns)  # noqa: S102
                except Exception:
                    logging.getLogger(__name__).debug("Import failed: %s", imp, exc_info=True)
            # Merge imported names into execution namespace
            for k, v in _import_ns.items():
                if k != "__builtins__":
                    namespace[k] = v

            # ``result`` is how a cell hands back a table. The namespace is
            # shared so that ``df`` carries from one cell to the next, which
            # also carried ``result``: a table set in step 1 was shown again
            # under every chart that followed. Only a cell that sets it shows it.
            namespace.pop("result", None)

            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()
            plt.close("all")

            try:
                exec(cell.code, namespace)  # noqa: S102

                stdout_text = buffer.getvalue()
                parts: list[str] = []

                # Stdout output
                if stdout_text.strip():
                    # color is set inline: the HTML export styles every <pre>
                    # as a dark code block, and without it printed output came
                    # out white on this light background -- invisible.
                    parts.append(
                        f'<pre style="background:#f5f5f5;color:#212121;'
                        f'border-left:3px solid #90caf9;'
                        f'padding:8px 12px;font-size:0.82rem;overflow-x:auto;'
                        f'margin:4px 0;border-radius:0 4px 4px 0;">'
                        f'{html_mod.escape(stdout_text)}</pre>'
                    )

                # Check for result DataFrame
                if "result" in namespace and isinstance(namespace["result"], _pd.DataFrame):
                    result_df = namespace["result"]
                    nrows = len(result_df)
                    tbl = _table_html(result_df.head(15))
                    if nrows > 15:
                        tbl += f'<p style="color:#999;font-size:0.8rem;">Showing 15 of {nrows} rows</p>'
                    parts.append(tbl)

                # Check for matplotlib figures
                for fig_num in plt.get_fignums():
                    fig = plt.figure(fig_num)
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
                    buf.seek(0)
                    b64 = base64.b64encode(buf.read()).decode()
                    parts.append(
                        f'<img src="data:image/png;base64,{b64}" '
                        f'style="max-width:100%;margin:4px 0;border-radius:4px;">'
                    )
                    plt.close(fig)

                if parts:
                    cell.output_html = "\n".join(parts)
                else:
                    # Marked so the reader view of the export can leave it
                    # out: it tells the author the cell ran, and tells a
                    # report's reader nothing.
                    cell.output_html = (
                        f'<span class="{NOTE_CLASS}" style="color:#4CAF50;font-size:0.82rem;">'
                        'Executed successfully (no output)</span>'
                    )
                messages.append(f"Cell {cell.order}: OK")

            except FileNotFoundError as e:
                if cell.action != "load" or df is None:
                    cell.output_html = _error_html(e)
                    messages.append(f"Cell {cell.order}: Error - {e}")
                    continue
                # A load step names a file by its bare name, which is right
                # for the exported script run beside the file and wrong here,
                # where the app holds the dataset already and every later
                # cell reads it as ``df``. It used to fail in red with a raw
                # FileNotFoundError, which read as "the report is broken".
                cell.output_html = (
                    f'<p class="{NOTE_CLASS}" style="color:#616161;font-size:0.85rem;margin:4px 0;">'
                    f"Not run here: the app already holds this dataset as <code>df</code>, "
                    f"and the cells below use it. This line loads the file when the "
                    f"exported code runs on its own, next to the file.</p>"
                )
                messages.append(f"Cell {cell.order}: OK (load step not needed in the app)")
            except Exception as e:
                cell.output_html = (
                    f'<pre style="background:#fff3e0;border-left:3px solid #e53935;'
                    f'padding:8px 12px;font-size:0.82rem;color:#c62828;'
                    f'margin:4px 0;border-radius:0 4px 4px 0;">'
                    f'{type(e).__name__}: {html_mod.escape(str(e))}</pre>'
                )
                messages.append(f"Cell {cell.order}: Error - {e}")
            finally:
                sys.stdout = old_stdout

        return messages

    # --- Serialization ---

    def export_json(self) -> str:
        """Export the report as JSON."""
        data = {
            "title": self.title,
            "author": self.author,
            "cells": [
                {
                    "id": c.id,
                    "order": c.order,
                    "cell_type": c.cell_type.value,
                    "enabled": c.enabled,
                    "action": c.action,
                    "description": c.description,
                    "code": c.code,
                    "imports": c.imports,
                    "markdown": c.markdown,
                }
                for c in self._cells
            ],
        }
        return json.dumps(data, indent=2)

    def import_json(self, json_str: str) -> None:
        """Load a report from JSON, replacing current cells."""
        data = json.loads(json_str)
        self.title = data.get("title", "PyAnalytica Report")
        self.author = data.get("author", "")
        self._cells = []
        for c in data.get("cells", []):
            self._cells.append(ReportCell(
                id=c.get("id", str(uuid.uuid4())[:8]),
                order=c.get("order", 0),
                cell_type=CellType(c.get("cell_type", "code")),
                enabled=c.get("enabled", True),
                action=c.get("action", ""),
                description=c.get("description", ""),
                code=c.get("code", ""),
                imports=c.get("imports", []),
                markdown=c.get("markdown", ""),
            ))
        self._renumber()
