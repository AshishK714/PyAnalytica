"""Model > Cluster module — K-means, hierarchical."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.types import get_numeric_columns
from pyanalytica.model.cluster import hierarchical_cluster, kmeans_cluster
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.disclosure import (
    PLOT_HEIGHT,
    diagnostics,
    is_open,
    supporting,
)
from pyanalytica.ui.components.download_result import download_result_server, download_result_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.status import status_server, status_ui
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)


@module.ui
def cluster_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("method", "Method",
                choices={"kmeans": "K-Means", "hierarchical": "Hierarchical"}),
            ui.input_select("features", "Features", choices=[], multiple=True),
            ui.input_slider("n_clusters", "Number of Clusters", 2, 15, 3),
            ui.input_action_button("run_btn", "Run Clustering", class_="btn-primary w-100 mt-2"),
            width=300,
        ),
        # Tier 1 -- the clusters and what is in them.
        # Above the result: when a run fails this is what replaces it.
        status_ui("status"),
        ui.output_ui("guidance"),
        ui.output_ui("cluster_summary"),
        ui.output_ui("profiles_heading"),
        ui.output_data_frame("profiles"),
        download_result_ui("dl"),
        # Tier 2 -- where they sit.
        supporting(
            "Cluster scatter plot",
            ui.output_plot("scatter_plot", height=PLOT_HEIGHT),
            id="scatter_open",
        ),
        # Tier 3 -- how many clusters to use is a different question from what
        # the clusters are.
        diagnostics(
            "Choosing k (elbow plot)",
            ui.output_plot("elbow_plot", height=PLOT_HEIGHT),
            id="elbow_open",
        ),
        code_panel_ui("code"),
    )


@module.server
def cluster_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    result = reactive.value(None)
    status = status_server("status")

    @reactive.effect
    def _update_cols():
        df = get_current_df()
        if df is not None:
            update_multi_choices(input, "features", get_numeric_columns(df))

    def _wants_plots() -> bool:
        """Either section being open is enough: both come from one sweep."""
        return is_open(input, "elbow_open") or is_open(input, "scatter_open")

    @reactive.effect
    # Opening a diagnostics section has to re-run this: the fit is what
    # builds the figures, and with the event limited to the button, a
    # section opened after the fit stayed empty.
    @reactive.event(input.run_btn, input["elbow_open"], input["scatter_open"])
    def _run():
        df = get_current_df()
        if not require(df is not None, NO_DATASET):
            return
        features = list(input.features())
        # Was req(len(features) >= 2), which aborts the run silently. A student
        # who picked one variable and pressed Run saw nothing happen and no
        # reason why -- reported as "Cluster does not work". Clear any earlier
        # result too, so a refused run cannot leave the previous run's charts
        # on screen looking like the answer to what was just asked.
        if len(features) < 2:
            result.set(None)
            return
        try:
            if input.method() == "kmeans":
                # The elbow plot's sweep -- a k-means fit and an O(n^2)
                # silhouette score at every k in 2..10 -- is 95% of this
                # panel's runtime and exists only to draw it. 697ms
                # against 32ms on 891 rows; on diamonds it does not
                # finish. The answer is identical either way.
                r = kmeans_cluster(
                    df, features, chosen_k=input.n_clusters(),
                    diagnostics=_wants_plots(),
                )
            else:
                r = hierarchical_cluster(df, features, n_clusters=input.n_clusters())
            result.set(r)
            state.codegen.record(r.code, action="model", description="Cluster analysis")
            last_code.set(r.code.code)
        except Exception as e:
            result.set(None)
            status.failed(str(e))

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
                ui.tags.strong("Cannot cluster: "),
                f"this dataset has {available} numeric column"
                f"{'' if available == 1 else 's'}. Clustering groups rows by "
                f"how close they are across several measurements, so it needs "
                f"at least two.",
                class_="alert alert-warning",
            )

        return ui.div(
            ui.tags.strong("Choose at least two features. "),
            "Clustering groups rows by how close they are to each other, and "
            "closeness needs more than one measurement to be meaningful. "
            "Hold Ctrl (Cmd on a Mac) to select more than one.",
            class_="alert alert-info",
        )

    @render.ui
    def cluster_summary():
        r = result()
        req(r is not None)
        return ui.div(
            ui.h5(f"Clustering: {r.n_clusters} clusters"),
            ui.p("Note: Clusters are analytical conveniences, not fixed types in reality.", class_="text-muted small"),
            class_="alert alert-info",
        )

    @render.plot
    def elbow_plot():
        r = result()
        req(r is not None and r.elbow_plot is not None)
        return r.elbow_plot

    @render.plot
    def scatter_plot():
        r = result()
        req(r is not None and r.scatter_plot is not None)
        return r.scatter_plot

    @render.ui
    def profiles_heading():
        # Rendered with the table, not above it: a static heading announces a
        # table that may not be there.
        req(result() is not None)
        return ui.h5("Cluster Profiles")

    @render.data_frame
    def profiles():
        r = result()
        req(r is not None)
        return render.DataGrid(r.cluster_profiles.reset_index())

    download_result_server(
        "dl",
        get_df=lambda: result().cluster_profiles.reset_index(),
        filename="cluster_profiles",
    )
    code_panel_server("code", get_code=last_code)
