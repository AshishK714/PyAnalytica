"""Describe > One Variable -- what does this column look like?

A number gets a summary and a histogram; a category gets counts and a bar
chart. A second picture and a test wait behind disclosure sections.
"""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.ask import TREAT_CHOICES, describe_one
from pyanalytica.core import round_df
from pyanalytica.core.state import WorkbenchState
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.decimals_control import decimals_server, decimals_ui
from pyanalytica.ui.components.disclosure import PLOT_HEIGHT, is_open, supporting
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.selects import update_choices
from pyanalytica.ui.components.status import status_server, status_ui


def _guide():
    return ui.div(
        ui.h5("What does one column look like?"),
        ui.p(
            "Choose a column. A number gets a summary table and a histogram; a "
            "category gets counts and a bar chart. A second picture and a test "
            "wait below until you open them.",
            class_="mb-2",
        ),
        ui.p(
            'A 0/1 column or a small whole-number scale is read as categories. '
            '"Treat as" overrides that reading.',
            class_="text-muted small",
        ),
        class_="pa-guide",
    )


@module.ui
def one_variable_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("col", "Column", choices=[]),
            ui.input_select("treat", "Treat it as", choices=TREAT_CHOICES),
            ui.input_action_button("run_btn", "Describe", class_="btn-primary w-100 mt-2"),
            width=300,
        ),
        status_ui("status"),
        ui.output_ui("answer"),
        decimals_ui("dec"),
        ui.output_data_frame("answer_table"),
        ui.output_plot("answer_plot", height="440px"),
        download_result_ui("dl"),
        supporting(
            # Named for what it holds once there is an answer: "Another
            # picture" did not say a bar chart of means was inside.
            ui.output_text("picture_title", inline=True),
            ui.output_plot("picture_plot", height=PLOT_HEIGHT),
            ui.output_ui("picture_text"),
            id="picture_open",
        ),
        supporting(
            "Test",
            ui.output_ui("test_text"),
            ui.output_data_frame("test_table"),
            id="test_open",
        ),
        code_panel_ui("code"),
    )


@module.server
def one_variable_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    result = reactive.value(None)
    recorded_run = reactive.value(0)
    get_dec = decimals_server("dec")
    status = status_server("status")

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            update_choices(input, "col", list(df.columns))

    @reactive.effect
    # Re-run when the picture section opens: its figure is only drawn then.
    @reactive.event(input.run_btn, input["picture_open"])
    def _run():
        if input.run_btn() == 0:
            return
        df = get_current_df()
        if not require(df is not None, NO_DATASET):
            return
        col = input.col()
        if not require(col, "Choose the column you want to describe."):
            result.set(None)
            status.check("Choose the column you want to describe.")
            return
        try:
            r = describe_one(
                df, col, treat=input.treat(),
                second_picture=is_open(input, "picture_open"),
            )
        except Exception as e:
            result.set(None)
            status.failed(str(e))
            return
        result.set(r)
        status.clear()
        last_code.set(r.code.code)
        if recorded_run() != input.run_btn():
            recorded_run.set(input.run_btn())
            state.codegen.record(r.code, action="ask", description=r.description)

    @render.ui
    def answer():
        r = result()
        if r is None:
            return _guide()
        return ui.div(
            ui.h5(r.question),
            ui.p(r.answer.sentence, class_="mb-1"),
            ui.tags.small(r.reading, class_="text-muted"),
            class_="alert alert-info",
        )

    @render.data_frame
    def answer_table():
        r = result()
        req(r is not None and r.answer.table is not None)
        return render.DataGrid(round_df(r.answer.table, get_dec()))

    @render.plot
    def answer_plot():
        r = result()
        req(r is not None and r.answer.figure is not None)
        return r.answer.figure

    @render.text
    def picture_title():
        r = result()
        if r is None or r.picture is None:
            return "Another picture"
        return r.picture.title

    @render.plot
    def picture_plot():
        r = result()
        req(r is not None and r.picture is not None and r.picture.figure is not None)
        return r.picture.figure

    @render.ui
    def picture_text():
        r = result()
        req(r is not None and r.picture is not None)
        return ui.p(r.picture.sentence, class_="text-muted small mt-2")

    @render.ui
    def test_text():
        r = result()
        req(r is not None and r.test is not None)
        t = r.test
        return ui.div(
            ui.p(t.sentence),
            *[ui.p(line, class_="mb-1 small") for line in t.notes],
            ui.tags.ul(*[ui.tags.li(step, class_="small") for step in r.next_steps], class_="mb-0"),
            class_="mt-2 p-2 bg-light rounded",
        )

    @render.data_frame
    def test_table():
        r = result()
        req(r is not None and r.test is not None and r.test.table is not None)
        return render.DataGrid(round_df(r.test.table, get_dec()))

    download_result_server(
        "dl", get_df=lambda: result().answer.table if result() else None,
        filename=lambda: result().description if result() else "describe",
        decimals=get_dec,
    )
    def _report_cells():
        r = result()
        if r is None:
            return []
        opened = {k for k in ("picture", "test") if is_open(input, f"{k}_open")}
        return [(label, snippet.code) for label, snippet in r.report_cells(opened)]

    code_panel_server(
        "code", get_code=last_code, state=state, action="ask",
        description=lambda: result().description if result() else "Describe",
        get_cells=_report_cells,
    )
