"""Report Builder output fit for the report's reader.

From a student-style run that built a nine-question report: the load step
failed in red, tables printed six decimals with a 0, 1, 2 index, the export
carried step numbers, badges and "Executed successfully (no output)", and
moving a cell into place took one click per step.
"""

import pandas as pd
import pytest

from pyanalytica.core.report_builder import CellType, ReportBuilder, _fmt_number, _table_html
from pyanalytica.report.export import export_report_html


@pytest.fixture
def df():
    return pd.DataFrame({"g": ["a", "b", "a", "b"], "v": [1.23456, 2.5, 3.75, 13270.422265]})


def test_a_load_step_for_a_missing_file_explains_itself_instead_of_failing(df):
    rb = ReportBuilder()
    rb.add_code_cell(action="load", description="Load",
                     code='data = pd.read_csv("not_here.csv")\ndf = data')
    rb.add_code_cell(action="explore", description="Mean",
                     code='result = df.groupby("g")["v"].mean().reset_index()')
    msgs = rb.execute_all(df)
    assert all("OK" in m for m in msgs), msgs
    load, mean = rb.get_cells()
    assert "FileNotFoundError" not in load.output_html
    assert "already holds this dataset" in load.output_html
    assert "<table" in mean.output_html


def test_a_missing_file_elsewhere_is_still_an_error(df):
    rb = ReportBuilder()
    rb.add_code_cell(action="explore", description="x", code='pd.read_csv("not_here.csv")')
    msgs = rb.execute_all(df)
    assert "Error" in msgs[0]
    assert "FileNotFoundError" in rb.get_cells()[0].output_html


def test_tables_drop_the_bare_row_numbers_and_round_for_reading(df):
    rb = ReportBuilder()
    rb.add_code_cell(action="explore", description="t", code="result = df")
    rb.execute_all(df)
    html = rb.get_cells()[0].output_html
    assert "13,270.42" in html and "13270.422265" not in html
    assert "<th>0</th>" not in html and "<th></th>" not in html


def test_a_meaningful_index_is_kept(df):
    rb = ReportBuilder()
    rb.add_code_cell(action="explore", description="t", code='result = df.groupby("g")[["v"]].mean()')
    rb.execute_all(df)
    assert ">a<" in rb.get_cells()[0].output_html


@pytest.mark.parametrize("value,shown", [
    (13270.422265, "13,270.42"), (342, "342"), (0.000123456, "0.0001235"),
    (0.5, "0.5"), (float("nan"), ""), ("text", "text"), (True, "True"),
])
def test_number_format(value, shown):
    assert _fmt_number(value) == shown


def test_a_column_is_formatted_one_way():
    """A column of percentages printed "75" beside "79.32"."""
    html = _table_html(pd.DataFrame({"no": [79.32, 75.0], "r": [0.08404, 0.8065], "p": [0.0, 1e-9]}))
    assert "75.00" in html and "79.32" in html
    assert "0.0840" in html and "0.8065" in html
    assert "&lt; 0.0001" in html  # escaped in the HTML, "< 0.0001" on screen


def test_index_names_become_a_column_not_a_second_header_row():
    ct = pd.crosstab(pd.Series(["n", "s", "n"], name="region"),
                     pd.Series(["no", "yes", "yes"], name="smoker"))
    html = _table_html(ct)
    assert "<th>region</th>" in html and "<th>smoker</th>" not in html
    assert html.count("<tr") == 3  # one header row, two data rows


def _report(df):
    rb = ReportBuilder()
    rb.title = "Costs"
    rb.add_markdown_cell(markdown="## Question 1")
    rb.add_code_cell(action="transform", description="Add a column", code='df["w"] = df["v"] * 2')
    rb.add_code_cell(action="explore", description="Mean v by g",
                     code='result = df.groupby("g")["v"].mean().reset_index()')
    rb.execute_all(df)
    return rb


def test_reader_view_has_headings_and_output_but_no_working_parts(df):
    html = export_report_html(_report(df), show_code=False)
    assert "<h4>Mean v by g</h4>" in html
    assert "Step 1" not in html and 'class="badge"' not in html
    assert "Executed successfully" not in html
    assert "<h4>Add a column</h4>" not in html  # nothing to show a reader


def test_working_view_keeps_steps_badges_and_notes(df):
    html = export_report_html(_report(df), show_code=True)
    assert "Step 1" in html and "Executed successfully" in html


def test_print_layout_lets_cards_break_and_keeps_charts_whole(df):
    html = export_report_html(_report(df), show_code=False)
    assert "@media print" in html and "break-inside: avoid" in html


def test_move_to_a_position_in_one_step():
    rb = ReportBuilder()
    ids = [rb.add_code_cell(description=str(i), code="x = 1").id for i in range(6)]
    rb.move_cell_to(ids[5], 2)
    assert [c.description for c in rb.get_cells()] == ["0", "5", "1", "2", "3", "4"]
    rb.move_cell_to(ids[0], 99)  # clamped to the end
    assert rb.get_cells()[-1].description == "0"
    rb.move_cell_to(ids[0], 0)  # clamped to the start
    assert rb.get_cells()[0].description == "0"
    assert [c.order for c in rb.get_cells()] == [1, 2, 3, 4, 5, 6]
