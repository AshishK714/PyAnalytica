"""What Add to Report sends from the guided panels.

A student-style run of a nine-question assignment found that the report
showed the model's coefficients where the student had seen a table of group
means: the panel sent all its code as one cell, every rung set ``result``,
and a report cell shows only the last. These tests run the cells the way
Report Builder does and check each one shows its own table.
"""

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from pyanalytica.ask import describe_one, relate_two
from pyanalytica.core.report_builder import ReportBuilder


@pytest.fixture
def df():
    rng = np.random.default_rng(11)
    n = 240
    smoker = rng.choice(["yes", "no", "no", "no"], n)
    region = rng.choice(["ne", "nw", "se", "sw"], n)
    age = rng.integers(18, 65, n)
    charges = 250 * age + np.where(smoker == "yes", 20000, 0) + rng.normal(0, 2000, n)
    return pd.DataFrame({"age": age, "smoker": smoker, "region": region, "charges": charges})


def _run_cells(cells, df):
    rb = ReportBuilder()
    for label, snippet in cells:
        rb.add_code_cell(action="ask", description=label, code=snippet.code, imports=snippet.imports)
    msgs = rb.execute_all(df)
    assert all("OK" in m for m in msgs), msgs
    return rb.get_cells()


def test_only_the_answer_goes_when_no_section_is_open(df):
    r = relate_two(df, "charges", "region")
    cells = r.report_cells(set())
    assert len(cells) == 1
    assert cells[0][0] == r.description


def test_each_open_section_is_its_own_cell(df):
    r = relate_two(df, "charges", "region")
    cells = r.report_cells({"picture", "test", "model"})
    assert [c[0] for c in cells] == [
        r.description,
        f"{r.description}, bar chart of means",
        f"{r.description}, test",
        f"{r.description}, model",
    ]


def test_the_answer_cell_shows_the_group_table_not_the_coefficients(df):
    r = relate_two(df, "charges", "smoker")
    out = _run_cells(r.report_cells({"model"}), df)
    answer_html, model_html = out[0].output_html, out[1].output_html
    assert "mean charges" in answer_html
    assert "coefficient" not in answer_html
    assert "coefficient" in model_html


def test_a_colour_split_reaches_the_report(df):
    plain = _run_cells(relate_two(df, "charges", "region").report_cells(set()), df)[0].output_html
    split = _run_cells(
        relate_two(df, "charges", "region", color_by="smoker").report_cells(set()), df
    )[0].output_html
    assert plain != split
    assert "<th>smoker</th>" in split


def test_within_group_r_table_reaches_the_report(df):
    r = relate_two(df, "charges", "age", color_by="smoker")
    cells = r.report_cells(set())
    ns = {"df": df.copy(), "pd": pd, "np": np}
    exec(cells[0][1].code.split("\n\n")[0], ns)  # the table part of the answer
    assert ns["result"].columns.tolist() == r.answer.table.columns.tolist()
    assert ns["result"]["smoker"].tolist() == r.answer.table["smoker"].tolist()
    html = _run_cells(cells, df)[0].output_html
    assert "Pearson r" in html and ">all<" in html


def test_one_variable_sends_the_answer_and_open_sections(df):
    r = describe_one(df, "charges")
    assert len(r.report_cells(set())) == 1
    assert len(r.report_cells({"picture", "test"})) == 3
    _run_cells(r.report_cells({"picture", "test"}), df)


def test_category_model_rung_without_code_is_skipped(df):
    r = relate_two(df, "smoker", "region")
    cells = r.report_cells({"model"})
    assert len(cells) == 1  # the model rung is a pointer with no code


# --- the same screen lists groups in one order -----------------------------

def test_table_boxplot_and_bars_share_one_group_order(df):
    r = relate_two(df, "charges", "region", second_picture=True)
    table_order = r.answer.table["region"].tolist()
    box_order = [t.get_text() for t in r.answer.figure.axes[0].get_xticklabels()]
    bar_order = [t.get_text() for t in r.picture.figure.axes[0].get_xticklabels()]
    assert table_order == box_order == bar_order == sorted(table_order)


def test_binary_outcome_sentence_describes_the_rarer_level(df):
    r = relate_two(df, "smoker", "region")
    assert "smoker = yes" in r.answer.sentence


def test_colour_split_points_to_pivot_for_rows_by_columns(df):
    r = relate_two(df, "charges", "region", color_by="smoker")
    assert any("Relate > Pivot" in n for n in r.answer.notes)
