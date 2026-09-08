"""Model > Reduce module — PCA."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_numeric_columns
from pyanalytica.model.reduce import pca_analysis
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.disclosure import PLOT_HEIGHT, diagnostics, supporting
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


@module.ui
def reduce_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("features", "Features", choices=[], multiple=True),
            ui.input_action_button("run_btn", "Run PCA", class_="btn-primary w-100 mt-2"),
            width=300,
        ),
        # Tier 1 -- how much variance the components explain.
        ui.output_ui("guidance"),
        ui.output_ui("pca_summary"),
        download_result_ui("dl"),
        # Tier 2 -- what the components are made of, and how many to keep.
        supporting(
            "Component loadings",
            ui.output_data_frame("loadings"),
        ),
        supporting(
            "How many components? (scree plot)",
            ui.output_plot("scree_plot", height=PLOT_HEIGHT),
        ),
        # Tier 3.
        diagnostics(
            "Biplot",
            ui.output_plot("biplot", height=PLOT_HEIGHT),
        ),
        ui.p("PCA reveals structure in your data. It's exploratory — not predictive.", class_="text-muted small mt-2"),
        code_panel_ui("code"),
    )


@module.server
def reduce_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    result = reactive.value(None)

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            update_multi_choices(input, "features", get_numeric_columns(df))

    @reactive.effect
    @reactive.event(input.run_btn)
    def _run():
        df = get_current_df()
        if not require(df is not None, NO_DATASET):
            return
        features = list(input.features())
        # See mod_cluster: req() here aborted the run without a word, so
        # picking one feature -- or none -- looked like a broken button.
        # Clearing the result matters especially here, because deselecting
        # everything and pressing Run used to leave the previous PCA on
        # screen, which reads as a fresh answer to a question nobody asked.
        if len(features) < 2:
            result.set(None)
            return
        try:
            r = pca_analysis(df, features)
            result.set(r)
            state.codegen.record(r.code, action="model", description="PCA")
            last_code.set(r.code.code)
        except Exception as e:
            ui.notification_show(f"Error: {e}", type="error")

    @render.ui
    def guidance():
        df = get_current_df()
        if df is None:
            return ui.div(
                ui.tags.strong("No dataset loaded. "),
                "Open Data > Load and choose a dataset first.",
                class_="alert alert-info",
            )

        chosen = list(input.features())
        if len(chosen) >= 2:
            return ui.TagList()

        available = len(get_numeric_columns(df))
        if available < 2:
            return ui.div(
                ui.tags.strong("Cannot run PCA: "),
                f"this dataset has {available} numeric column"
                f"{'' if available == 1 else 's'}. PCA summarises several "
                f"columns at once, so it needs at least two.",
                class_="alert alert-warning",
            )

        return ui.div(
            ui.tags.strong("Choose at least two features. "),
            "PCA looks for patterns shared across columns, so a single column "
            "has nothing to share a pattern with. Hold Ctrl (Cmd on a Mac) to "
            "select more than one.",
            class_="alert alert-info",
        )

    @render.ui
    def pca_summary():
        r = result()
        req(r is not None)
        return ui.div(
            ui.h5("PCA Results"),
            ui.p(f"Recommended components: {r.recommended_n} (>80% variance explained)"),
            ui.p(f"Total variance explained: {r.cumulative_variance[-1]*100:.1f}%"),
            class_="alert alert-info",
        )

    @render.plot
    def scree_plot():
        r = result()
        req(r is not None and r.scree_plot is not None)
        return r.scree_plot

    @render.plot
    def biplot():
        r = result()
        req(r is not None and r.biplot is not None)
        return r.biplot

    @render.data_frame
    def loadings():
        r = result()
        req(r is not None)
        return render.DataGrid(r.loadings.reset_index().rename(columns={"index": "Variable"}))

    download_result_server(
        "dl",
        get_df=lambda: result().loadings.reset_index(),
        filename="pca_loadings",
    )
    code_panel_server("code", get_code=last_code)
