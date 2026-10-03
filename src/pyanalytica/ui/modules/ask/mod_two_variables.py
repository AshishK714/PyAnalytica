"""Relate > Two Variables -- how does Y relate to X?

The student picks Y and X; the column types pick the analysis (see
``pyanalytica.ask.two``). The answer rung is always on screen: one sentence,
one table, one chart. The other rungs -- a second picture, the test, the
model -- sit behind disclosure sections and are built only when opened.
"""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.ask import TREAT_CHOICES, relate_two
from pyanalytica.core import round_df
from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_groupable_columns
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.decimals_control import decimals_server, decimals_ui
from pyanalytica.ui.components.disclosure import PLOT_HEIGHT, is_open, supporting
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.selects import update_choices
from pyanalytica.ui.components.status import status_server, status_ui

#: What the panel will do, shown before the first run so the choice of
#: analysis is never a surprise.
_GUIDE = [
    ("number", "category", "group means, boxplots", "t-test or ANOVA", "regression on group dummies"),
    ("number", "number", "r and the fitted line, scatter", "correlation test", "the fitted line"),
    ("category", "category", "row percentages, grouped bars", "chi-square", "pointer to Model > Classify"),
    ("category", "number", "read as number by category, roles swapped", "t-test or ANOVA", "pointer to Model > Classify"),
]


def _guide():
    rows = [
        ui.tags.tr(*[ui.tags.td(cell) for cell in row]) for row in _GUIDE
    ]
    return ui.div(
        ui.h5("How does Y relate to X?"),
        ui.p(
            "Choose Y (the outcome) and X (the grouping or predictor). The two "
            "column types pick the analysis; the answer appears here with its "
            "chart, and the test and model wait below until you open them.",
            class_="mb-2",
        ),
        ui.tags.table(
            ui.tags.thead(ui.tags.tr(*[ui.tags.th(h) for h in ("Y", "X", "Describe", "Test", "Model")])),
            ui.tags.tbody(*rows),
            class_="table table-sm small",
        ),
        ui.p(
            'A 0/1 column or a small whole-number scale is read as categories. '
            '"Treat as" overrides that reading. "Colour by" adds a third, '
            'categorical column: the same comparison split by it, to see '
            'whether the answer holds within groups.',
            class_="text-muted small",
        ),
        class_="pa-guide",
    )


@module.ui
def two_variables_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("y", "Y (the outcome)", choices=[]),
            ui.input_select("x", "X (the grouping or predictor)", choices=[]),
            ui.input_select("color_by", "Colour by (optional context)", choices=[""]),
            ui.input_select("treat_y", "Treat Y as", choices=TREAT_CHOICES),
            ui.input_select("treat_x", "Treat X as", choices=TREAT_CHOICES),
            ui.input_action_button("run_btn", "Answer", class_="btn-primary w-100 mt-2"),
            width=300,
        ),
        # Above the answer, because when a run fails this is what replaces it.
        status_ui("status"),
        ui.output_ui("answer"),
        decimals_ui("dec"),
        ui.output_data_frame("answer_table"),
        ui.output_plot("answer_plot", height="440px"),
        download_result_ui("dl"),
        supporting(
            "Another picture",
            ui.output_plot("picture_plot", height=PLOT_HEIGHT),
            ui.output_ui("picture_text"),
            id="picture_open",
        ),
        supporting(
            "Test: could this be chance?",
            ui.output_ui("test_text"),
            ui.output_data_frame("test_table"),
            id="test_open",
        ),
        supporting(
            "Model: the same answer as an equation",
            ui.output_ui("model_text"),
            ui.output_data_frame("model_table"),
            id="model_open",
        ),
        code_panel_ui("code"),
    )


@module.server
def two_variables_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    result = reactive.value(None)
    recorded_run = reactive.value(0)
    get_dec = decimals_server("dec")
    status = status_server("status")

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            cols = list(df.columns)
            update_choices(input, "y", cols)
            # Default X to a different column than Y, so the first press of
            # Answer does not refuse with "Y and X are the same column".
            update_choices(input, "x", cols, prefer=cols[1] if len(cols) > 1 else None)
            update_choices(input, "color_by", [""] + get_groupable_columns(df), allow_none=True)

    @reactive.effect
    # Opening a section has to re-run this: the second picture is only drawn
    # when its section is open, so a section opened after the run would stay
    # empty with the event limited to the button.
    @reactive.event(input.run_btn, input["picture_open"])
    def _run():
        if input.run_btn() == 0:
            return
        df = get_current_df()
        if not require(df is not None, NO_DATASET):
            return
        y, x = input.y(), input.x()
        if not require(y and x, "Choose both a Y and an X column to relate."):
            result.set(None)
            status.check("Choose both a Y and an X column to relate.")
            return
        try:
            r = relate_two(
                df, y, x, treat_y=input.treat_y(), treat_x=input.treat_x(),
                color_by=input.color_by() or None,
                second_picture=is_open(input, "picture_open"),
            )
        except Exception as e:
            # Clear the answer as well: a stale one beside the inputs that
            # failed reads as a fresh answer to a question nobody asked.
            result.set(None)
            status.failed(str(e))
            return
        result.set(r)
        status.clear()
        last_code.set(r.code.code)
        # Record once per press, not again when a section is opened.
        if recorded_run() != input.run_btn():
            recorded_run.set(input.run_btn())
            state.codegen.record(r.code, action="ask", description=f"Relate: {r.description}")

    @render.ui
    def answer():
        r = result()
        if r is None:
            return _guide()
        return ui.div(
            ui.h5(r.question),
            ui.p(r.answer.sentence, class_="mb-1"),
            *[ui.p(note, class_="small mb-1") for note in r.answer.notes],
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
            class_="mt-2 p-2 bg-light rounded",
        )

    @render.data_frame
    def test_table():
        r = result()
        req(r is not None and r.test is not None and r.test.table is not None)
        return render.DataGrid(round_df(r.test.table, get_dec()))

    @render.ui
    def model_text():
        r = result()
        req(r is not None and r.model is not None)
        return ui.div(
            ui.p(r.model.sentence),
            ui.tags.ul(*[ui.tags.li(step, class_="small") for step in r.next_steps], class_="mb-0"),
            class_="mt-2 p-2 bg-light rounded",
        )

    @render.data_frame
    def model_table():
        r = result()
        req(r is not None and r.model is not None and r.model.table is not None)
        return render.DataGrid(round_df(r.model.table, get_dec()))

    download_result_server(
        "dl", get_df=lambda: result().answer.table if result() else None, filename="relate",
    )
    code_panel_server(
        "code", get_code=last_code, state=state, action="ask",
        description=lambda: f"Relate: {result().description}" if result() else "Relate",
    )
