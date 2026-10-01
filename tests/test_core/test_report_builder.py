"""Tests for core.report_builder and report export functions."""

from __future__ import annotations

import json

import pytest

from pyanalytica.core.codegen import CodeSnippet
from pyanalytica.core.procedure import ProcedureRecorder
from pyanalytica.core.report_builder import CellType, ReportBuilder, ReportCell
from pyanalytica.report.export import (
    _render_markdown,
    export_report_html,
    export_report_jupyter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def recorder():
    """Procedure recorder with 2 sample steps."""
    rec = ProcedureRecorder()
    rec.start_recording()
    rec.record_step("load", "Load tips dataset", CodeSnippet(
        code='df = pd.read_csv("tips.csv")',
        imports=["import pandas as pd"],
    ))
    rec.record_step("transform", "Add tip_pct column", CodeSnippet(
        code='df["tip_pct"] = df["tip"] / df["total_bill"]',
        imports=["import pandas as pd"],
    ))
    rec.stop_recording()
    return rec


@pytest.fixture
def builder():
    return ReportBuilder()


# ---------------------------------------------------------------------------
# ReportCell / CellType
# ---------------------------------------------------------------------------

class TestCellType:
    def test_values(self):
        assert CellType.CODE.value == "code"
        assert CellType.MARKDOWN.value == "markdown"


class TestReportCell:
    def test_default_values(self):
        cell = ReportCell()
        assert cell.cell_type == CellType.CODE
        assert cell.enabled is True
        assert cell.code == ""
        assert cell.markdown == ""
        assert len(cell.id) == 8


# ---------------------------------------------------------------------------
# ReportBuilder — basic ops
# ---------------------------------------------------------------------------

class TestReportBuilderBasic:
    def test_empty(self, builder):
        assert builder.cell_count() == 0
        assert builder.get_cells() == []

    def test_import_from_recorder(self, builder, recorder):
        count = builder.import_from_recorder(recorder)
        assert count == 2
        assert builder.cell_count() == 2
        cells = builder.get_cells()
        assert cells[0].cell_type == CellType.CODE
        assert cells[0].action == "load"
        assert cells[1].action == "transform"
        assert cells[0].order == 1
        assert cells[1].order == 2

    def test_add_markdown_cell_at_end(self, builder):
        cell = builder.add_markdown_cell(markdown="# Hello")
        assert cell.cell_type == CellType.MARKDOWN
        assert cell.markdown == "# Hello"
        assert builder.cell_count() == 1

    def test_add_markdown_cell_after_id(self, builder, recorder):
        builder.import_from_recorder(recorder)
        first_id = builder.get_cells()[0].id
        cell = builder.add_markdown_cell(after_cell_id=first_id, markdown="Note here")
        cells = builder.get_cells()
        assert cells[1].id == cell.id
        assert cells[1].markdown == "Note here"
        assert len(cells) == 3

    def test_add_title_cell(self, builder):
        builder.title = "My Report"
        builder.author = "Test"
        builder.add_markdown_cell(markdown="Some text")
        builder.add_title_cell()
        cells = builder.get_cells()
        assert cells[0].cell_type == CellType.MARKDOWN
        assert "My Report" in cells[0].markdown
        assert cells[0].order == 1


class TestAddCodeCell:
    def test_add_code_cell_basic(self, builder):
        cell = builder.add_code_cell(
            action="analyze", description="Run t-test",
            code="from scipy import stats\nstats.ttest_1samp(df['x'], 0)",
            imports=["import pandas as pd"],
        )
        assert builder.cell_count() == 1
        assert cell.cell_type == CellType.CODE
        assert cell.action == "analyze"
        assert cell.description == "Run t-test"
        assert "ttest_1samp" in cell.code
        assert cell.imports == ["import pandas as pd"]

    def test_add_code_cell_ordering(self, builder):
        builder.add_code_cell(action="load", description="Step 1", code="x = 1")
        builder.add_code_cell(action="transform", description="Step 2", code="x = 2")
        builder.add_code_cell(action="visualize", description="Step 3", code="x = 3")
        cells = builder.get_cells()
        assert len(cells) == 3
        assert cells[0].order == 1
        assert cells[1].order == 2
        assert cells[2].order == 3

    def test_add_code_cell_imports_preserved(self, builder):
        cell = builder.add_code_cell(
            imports=["import numpy as np", "import pandas as pd"],
        )
        assert cell.imports == ["import numpy as np", "import pandas as pd"]

    def test_add_code_cell_empty_defaults(self, builder):
        cell = builder.add_code_cell()
        assert cell.action == ""
        assert cell.description == ""
        assert cell.code == ""
        assert cell.imports == []
        assert cell.cell_type == CellType.CODE
        assert cell.enabled is True


class TestReportBuilderMutations:
    def test_remove_cell(self, builder, recorder):
        builder.import_from_recorder(recorder)
        cid = builder.get_cells()[0].id
        builder.remove_cell(cid)
        assert builder.cell_count() == 1
        assert builder.get_cells()[0].order == 1

    def test_move_cell_down(self, builder, recorder):
        builder.import_from_recorder(recorder)
        first = builder.get_cells()[0]
        builder.move_cell(first.id, "down")
        cells = builder.get_cells()
        assert cells[1].id == first.id

    def test_move_cell_up(self, builder, recorder):
        builder.import_from_recorder(recorder)
        second = builder.get_cells()[1]
        builder.move_cell(second.id, "up")
        cells = builder.get_cells()
        assert cells[0].id == second.id

    def test_toggle_cell(self, builder, recorder):
        builder.import_from_recorder(recorder)
        cid = builder.get_cells()[0].id
        assert builder.get_cells()[0].enabled is True
        builder.toggle_cell(cid)
        assert builder.get_cells()[0].enabled is False
        builder.toggle_cell(cid)
        assert builder.get_cells()[0].enabled is True

    def test_update_markdown(self, builder):
        cell = builder.add_markdown_cell(markdown="old")
        builder.update_markdown(cell.id, "new text")
        assert builder.get_cells()[0].markdown == "new text"

    def test_clear(self, builder, recorder):
        builder.import_from_recorder(recorder)
        builder.clear()
        assert builder.cell_count() == 0


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------

class TestReportBuilderJSON:
    def test_roundtrip(self, builder, recorder):
        builder.title = "Test Report"
        builder.author = "Tester"
        builder.import_from_recorder(recorder)
        builder.add_markdown_cell(markdown="# Section 1")

        json_str = builder.export_json()
        data = json.loads(json_str)
        assert data["title"] == "Test Report"
        assert data["author"] == "Tester"
        assert len(data["cells"]) == 3

        # Import into a fresh builder
        b2 = ReportBuilder()
        b2.import_json(json_str)
        assert b2.title == "Test Report"
        assert b2.author == "Tester"
        assert b2.cell_count() == 3
        assert b2.get_cells()[2].cell_type == CellType.MARKDOWN


# ---------------------------------------------------------------------------
# Export functions
# ---------------------------------------------------------------------------

class TestRenderMarkdown:
    def test_heading(self):
        result = _render_markdown("# Hello")
        assert "<h1>" in result

    def test_paragraph(self):
        result = _render_markdown("Some text")
        assert "<p>" in result

    def test_emphasis(self):
        result = _render_markdown("*italic text*")
        assert "<em>" in result or "<p>" in result


class TestExportReportHTML:
    def test_basic_output(self, builder, recorder):
        builder.import_from_recorder(recorder)
        html = export_report_html(builder)
        assert "<!DOCTYPE html>" in html
        assert "Load tips dataset" in html
        assert "tips.csv" in html

    def test_hide_code(self, builder, recorder):
        builder.import_from_recorder(recorder)
        html = export_report_html(builder, show_code=False)
        assert "tips.csv" not in html
        assert "Load tips dataset" in html

    def test_disabled_cells_excluded(self, builder, recorder):
        builder.import_from_recorder(recorder)
        builder.toggle_cell(builder.get_cells()[0].id)
        html = export_report_html(builder)
        assert "Load tips dataset" not in html
        assert "Add tip_pct column" in html

    def test_markdown_cells_rendered(self, builder):
        builder.add_markdown_cell(markdown="# My Section")
        html = export_report_html(builder)
        assert "My Section" in html

    def test_empty_report(self, builder):
        html = export_report_html(builder)
        assert "No cells in report" in html


class TestExportReportJupyter:
    def test_basic_structure(self, builder, recorder):
        builder.import_from_recorder(recorder)
        nb_json = export_report_jupyter(builder)
        nb = json.loads(nb_json)
        assert nb["nbformat"] == 4
        assert len(nb["cells"]) >= 3  # imports + 2*(desc+code)

    def test_markdown_cells_included(self, builder):
        builder.add_markdown_cell(markdown="# Intro")
        nb_json = export_report_jupyter(builder)
        nb = json.loads(nb_json)
        md_cells = [c for c in nb["cells"] if c["cell_type"] == "markdown"]
        assert len(md_cells) >= 1


# ---------------------------------------------------------------------------
# Code execution
# ---------------------------------------------------------------------------

class TestExecuteAll:
    def test_execute_simple_code(self, builder):
        import pandas as pd
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        cell = ReportCell(
            cell_type=CellType.CODE,
            code='result = df.describe()',
            imports=["import pandas as pd"],
        )
        builder._cells.append(cell)
        builder._renumber()
        msgs = builder.execute_all(df)
        assert len(msgs) == 1
        assert "OK" in msgs[0]
        assert cell.output_html  # Should have table output

    def test_execute_with_print(self, builder):
        import pandas as pd
        df = pd.DataFrame({"x": [1]})
        cell = ReportCell(
            cell_type=CellType.CODE,
            code='print("hello world")',
            imports=[],
        )
        builder._cells.append(cell)
        builder._renumber()
        msgs = builder.execute_all(df)
        assert "OK" in msgs[0]
        assert "hello world" in cell.output_html

    def test_execute_error_captured(self, builder):
        import pandas as pd
        df = pd.DataFrame({"x": [1]})
        cell = ReportCell(
            cell_type=CellType.CODE,
            code='1 / 0',
            imports=[],
        )
        builder._cells.append(cell)
        builder._renumber()
        msgs = builder.execute_all(df)
        assert "Error" in msgs[0]
        assert "ZeroDivisionError" in cell.output_html

    def test_execute_skips_disabled(self, builder):
        import pandas as pd
        df = pd.DataFrame({"x": [1]})
        cell = ReportCell(
            cell_type=CellType.CODE,
            code='print("should not run")',
            enabled=False,
        )
        builder._cells.append(cell)
        builder._renumber()
        msgs = builder.execute_all(df)
        assert len(msgs) == 0
        assert cell.output_html == ""

    def test_execute_none_df(self, builder):
        """Should work even if no dataframe is provided."""
        cell = ReportCell(
            cell_type=CellType.CODE,
            code='result = pd.DataFrame({"a": [1, 2]})',
            imports=["import pandas as pd"],
        )
        builder._cells.append(cell)
        builder._renumber()
        msgs = builder.execute_all(None)
        assert "OK" in msgs[0]

    def test_result_does_not_leak_into_later_cells(self, builder):
        """A table set in cell 1 was re-shown under every cell after it."""
        import pandas as pd
        df = pd.DataFrame({"x": [1, 2, 3]})
        first = ReportCell(cell_type=CellType.CODE, code="result = df.describe()")
        second = ReportCell(cell_type=CellType.CODE, code="y = df['x'].sum()")
        builder._cells.extend([first, second])
        builder._renumber()
        msgs = builder.execute_all(df)
        assert all("OK" in m for m in msgs)
        assert "<table" in first.output_html
        assert "<table" not in second.output_html
        assert "no output" in second.output_html

    def test_df_still_carries_between_cells(self, builder):
        """Clearing ``result`` must not clear the shared dataframe."""
        import pandas as pd
        df = pd.DataFrame({"x": [1, 2, 3]})
        first = ReportCell(cell_type=CellType.CODE, code='df["y"] = df["x"] * 2')
        second = ReportCell(cell_type=CellType.CODE, code='print(int(df["y"].sum()))')
        builder._cells.extend([first, second])
        builder._renumber()
        builder.execute_all(df)
        assert "12" in second.output_html

    def test_stdout_block_sets_its_own_text_colour(self, builder):
        """The export's global <pre> rule is white-on-dark; the stdout block
        is light, so it must carry a colour of its own or print() vanishes."""
        import pandas as pd
        cell = ReportCell(cell_type=CellType.CODE, code='print("visible")')
        builder._cells.append(cell)
        builder._renumber()
        builder.execute_all(pd.DataFrame({"x": [1]}))
        assert "color:#212121" in cell.output_html

    def test_output_in_html_export(self, builder):
        import pandas as pd
        df = pd.DataFrame({"x": [1, 2, 3]})
        cell = ReportCell(
            cell_type=CellType.CODE,
            code='print("test output")',
            imports=[],
            action="test",
            description="Test cell",
        )
        builder._cells.append(cell)
        builder._renumber()
        builder.execute_all(df)
        html = export_report_html(builder)
        assert "test output" in html
