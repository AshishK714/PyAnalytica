"""PyAnalytica — Main Shiny application entry point."""

from __future__ import annotations

import logging
from pathlib import Path

from shiny import App, reactive, render, ui

from pyanalytica.core.config import CourseConfig, is_menu_visible, load_config
from pyanalytica.core.extensions import discover_extensions
from pyanalytica.core.session import delete_session, list_sessions, load_session, save_session
from pyanalytica.core.state import WorkbenchState
from pyanalytica.core.theme import apply_theme, get_theme
from pyanalytica.datasets import register_extension_datasets
from pyanalytica.ui.components.dataset_selector import dataset_selector_server, dataset_selector_ui
from pyanalytica.ui.modules.data import (
    mod_combine, mod_export, mod_load, mod_profile, mod_transform, mod_view,
)
from pyanalytica.ui.modules.explore import mod_crosstab, mod_pivot, mod_simulate, mod_summarize
from pyanalytica.ui.modules.visualize import (
    mod_compare, mod_correlate, mod_distribute, mod_relate, mod_timeline,
)
from pyanalytica.ui.modules.analyze import mod_correlation, mod_means, mod_proportions
from pyanalytica.ui.modules.ask import mod_one_variable, mod_two_variables
from pyanalytica.ui.modules.model import (
    mod_classify, mod_cluster, mod_evaluate, mod_predict, mod_reduce, mod_regression,
)
from pyanalytica.ui.modules.homework import mod_homework
from pyanalytica.ui.modules.practice import mod_practice
from pyanalytica.ui.modules.report import mod_notebook, mod_procedure, mod_report_builder
from pyanalytica.ui.modules.ai import mod_assistant

logger = logging.getLogger(__name__)


def create_app(config: CourseConfig | None = None) -> App:
    """Create the PyAnalytica Shiny application."""
    if config is None:
        config = load_config()

    apply_theme(get_theme(config.theme))

    # --- Discover installed extensions ---
    registry = discover_extensions()
    if registry.datasets:
        register_extension_datasets(registry.datasets)

    # Build per-section extension sub-tabs
    _section_ext_tabs: dict[str, list] = {
        "Data": [], "Describe": [], "Relate": [], "Model": [],
        "Learn": [], "Report": [], "Advanced": [],
    }
    # Extensions written against the 0.9 menu still land somewhere sensible.
    _legacy_parents = {"Explore": "Relate", "Visualize": "Describe", "Analyze": "Advanced"}
    _toplevel_ext_panels: list = []
    for mod in registry.modules:
        try:
            panel = ui.nav_panel(mod.label, mod.ui_func(mod.module_id))
            parent = _legacy_parents.get(mod.parent, mod.parent)
            if parent and parent in _section_ext_tabs:
                _section_ext_tabs[parent].append(panel)
            else:
                _toplevel_ext_panels.append(panel)
        except Exception:
            logger.warning("Failed to build UI for extension module %r", mod.module_id, exc_info=True)

    app_ui = ui.page_navbar(
        ui.head_content(
            ui.HTML(
                '<link rel="preconnect" href="https://fonts.googleapis.com">'
                '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
                '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">'
                '<link rel="stylesheet" href="style.css">'
                # A "Download PNG" button on every chart; see the file.
                '<script src="chart_download.js" defer></script>'
            ),
        ),
        # === DATA ===
        ui.nav_panel("Data",
            ui.navset_tab(
                ui.nav_panel("Load", mod_load.load_ui("load")),
                ui.nav_panel("Profile", mod_profile.profile_ui("profile")),
                ui.nav_panel("View", mod_view.view_ui("view")),
                ui.nav_panel("Transform", mod_transform.transform_ui("transform")),
                ui.nav_panel("Combine", mod_combine.combine_ui("combine")),
                ui.nav_panel("Export", mod_export.export_ui("export")),
                *_section_ext_tabs["Data"],
            ),
        ),
        # === DESCRIBE === one thing at a time
        # The menu is organised by the shape of the question, the way JMP's
        # Distribution / Fit Y by X is: the column types pick the method, so
        # a student does not have to know a test's name to reach it. The
        # single-purpose panels that used to be Explore, Visualize and
        # Analyze live on under Advanced.
        ui.nav_panel("Describe",
            ui.navset_tab(
                ui.nav_panel("One Variable", mod_one_variable.one_variable_ui("one_variable")),
                ui.nav_panel("Correlate", mod_correlate.correlate_ui("correlate")),
                ui.nav_panel("Timeline", mod_timeline.timeline_ui("timeline")),
                *_section_ext_tabs["Describe"],
            ),
        ),
        # === RELATE === one thing against another
        ui.nav_panel("Relate",
            ui.navset_tab(
                ui.nav_panel("Two Variables", mod_two_variables.two_variables_ui("two_variables")),
                ui.nav_panel("Group By / Summarize", mod_summarize.summarize_ui("summarize")),
                ui.nav_panel("Pivot", mod_pivot.pivot_ui("pivot")),
                ui.nav_panel("Cross-tab", mod_crosstab.crosstab_ui("crosstab")),
                *_section_ext_tabs["Relate"],
            ),
        ),
        # === MODEL ===
        ui.nav_panel("Model",
            ui.navset_tab(
                ui.nav_panel("Regression", mod_regression.regression_ui("regression")),
                ui.nav_panel("Classify", mod_classify.classify_ui("classify")),
                ui.nav_panel("Evaluate", mod_evaluate.evaluate_ui("evaluate")),
                ui.nav_panel("Predict", mod_predict.predict_ui("predict")),
                ui.nav_panel("Cluster", mod_cluster.cluster_ui("cluster")),
                ui.nav_panel("Reduce", mod_reduce.reduce_ui("reduce")),
                *_section_ext_tabs["Model"],
            ),
        ),
        # === LEARN === exercises on the ideas, not analyses of the loaded data
        ui.nav_panel("Learn",
            ui.navset_tab(
                ui.nav_panel("Simulate", mod_simulate.simulate_ui("simulate")),
                ui.nav_panel("Practice", mod_practice.practice_ui("practice")),
                *_section_ext_tabs["Learn"],
            ),
        ),
        ui.nav_panel("Homework", mod_homework.homework_ui("homework")),
        # === REPORT ===
        ui.nav_panel("Report",
            ui.navset_tab(
                ui.nav_panel("Report Builder", mod_report_builder.report_builder_ui("report_builder")),
                ui.nav_panel("Notebook", mod_notebook.notebook_ui("report")),
                ui.nav_panel("Procedure", mod_procedure.procedure_ui("procedure")),
                *_section_ext_tabs["Report"],
            ),
        ),
        # === ADVANCED === the single-purpose panels, each with every option
        ui.nav_panel("Advanced",
            ui.navset_tab(
                ui.nav_panel("Distribution Plots", mod_distribute.distribute_ui("distribute")),
                ui.nav_panel("Scatter", mod_relate.relate_ui("relate")),
                ui.nav_panel("Group Plots", mod_compare.compare_ui("compare")),
                ui.nav_panel("Means", mod_means.means_ui("means")),
                ui.nav_panel("Proportions", mod_proportions.proportions_ui("proportions")),
                ui.nav_panel("Correlation", mod_correlation.correlation_ui("correlation")),
                *_section_ext_tabs["Advanced"],
            ),
        ),
        # === AI ASSISTANT ===
        ui.nav_panel("AI Assistant", mod_assistant.assistant_ui("assistant")),
        # === EXTENSION TOP-LEVEL PANELS ===
        *_toplevel_ext_panels,
        header=ui.div(
            ui.div(
                dataset_selector_ui("ds"),
                ui.div(
                    ui.input_text("session_name", "", placeholder="Session name", width="150px"),
                    ui.input_action_button("save_session", "Save", class_="btn-sm btn-outline-primary"),
                    ui.input_select("load_session", "Session:", choices=["(none)"], width="150px"),
                    ui.input_action_button("restore_session", "Load", class_="btn-sm btn-outline-primary"),
                    class_="d-flex align-items-center gap-2",
                ),
                class_="d-flex align-items-center gap-4 flex-wrap",
            ),
            class_="container-fluid pa-header-bar",
        ),
        title=ui.span(
            ui.HTML(
                '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
                '<rect x="3" y="12" width="4" height="9" rx="1" fill="white" opacity="0.7"/>'
                '<rect x="10" y="7" width="4" height="14" rx="1" fill="white" opacity="0.85"/>'
                '<rect x="17" y="3" width="4" height="18" rx="1" fill="white"/>'
                '</svg>'
            ),
            "PyAnalytica",
        ),
        id="main_nav",
    )

    def server(input, output, session):
        state = WorkbenchState()
        state._change_signal = reactive.value(0)

        # Restore autosaved session on startup
        if "autosave" in list_sessions():
            try:
                load_session(state, "autosave")
            except Exception:
                pass  # stale or corrupt autosave — start fresh
            else:
                state._notify()

        # Dataset selector
        selected_dataset = dataset_selector_server("ds", state=state)

        @reactive.calc
        def current_df():
            # Re-read when datasets change
            state._change_signal()
            name = selected_dataset()
            if not name or name not in state.datasets:
                return None
            return state.get(name)

        # Data modules
        mod_load.load_server("load", state=state, get_current_df=current_df)
        mod_profile.profile_server("profile", state=state, get_current_df=current_df)
        mod_view.view_server("view", state=state, get_current_df=current_df)
        mod_transform.transform_server("transform", state=state, get_current_df=current_df)
        mod_combine.combine_server("combine", state=state, get_current_df=current_df)
        mod_export.export_server("export", state=state, get_current_df=current_df)

        # Describe and Relate: the question-shaped panels
        mod_one_variable.one_variable_server("one_variable", state=state, get_current_df=current_df)
        mod_two_variables.two_variables_server("two_variables", state=state, get_current_df=current_df)

        # Explore modules
        mod_summarize.summarize_server("summarize", state=state, get_current_df=current_df)
        mod_pivot.pivot_server("pivot", state=state, get_current_df=current_df)
        mod_crosstab.crosstab_server("crosstab", state=state, get_current_df=current_df)
        mod_simulate.simulate_server("simulate", state=state)

        # Visualize modules
        mod_distribute.distribute_server("distribute", state=state, get_current_df=current_df)
        mod_relate.relate_server("relate", state=state, get_current_df=current_df)
        mod_compare.compare_server("compare", state=state, get_current_df=current_df)
        mod_correlate.correlate_server("correlate", state=state, get_current_df=current_df)
        mod_timeline.timeline_server("timeline", state=state, get_current_df=current_df)

        # Analyze modules
        mod_means.means_server("means", state=state, get_current_df=current_df)
        mod_proportions.proportions_server("proportions", state=state, get_current_df=current_df)
        mod_correlation.correlation_server("correlation", state=state, get_current_df=current_df)

        # Model modules
        mod_regression.regression_server("regression", state=state, get_current_df=current_df)
        mod_classify.classify_server("classify", state=state, get_current_df=current_df)
        mod_evaluate.evaluate_server("evaluate", state=state, get_current_df=current_df)
        mod_predict.predict_server("predict", state=state, get_current_df=current_df)
        mod_cluster.cluster_server("cluster", state=state, get_current_df=current_df)
        mod_reduce.reduce_server("reduce", state=state, get_current_df=current_df)

        # Homework module
        mod_practice.practice_server("practice", state=state, get_current_df=current_df)
        mod_homework.homework_server("homework", state=state, get_current_df=current_df)

        # Report modules
        mod_report_builder.report_builder_server("report_builder", state=state, get_current_df=current_df)
        mod_notebook.notebook_server("report", state=state, get_current_df=current_df)
        mod_procedure.procedure_server("procedure", state=state, get_current_df=current_df)

        # AI Assistant module
        mod_assistant.assistant_server("assistant", state=state, get_current_df=current_df)

        # Extension modules
        for ext_mod in registry.modules:
            try:
                ext_mod.server_func(ext_mod.module_id, state=state, get_current_df=current_df)
            except Exception:
                logger.warning(
                    "Failed to initialize extension server %r", ext_mod.module_id, exc_info=True,
                )

        # --- Session persistence ---

        # Autosave on session end instead of every state change
        # (synchronous pickle of large DataFrames blocks the event loop)
        _ = session.on_ended(lambda: save_session(state, "autosave") if state.datasets else None)

        def _refresh_session_choices():
            names = list_sessions()
            choices = [n for n in names if n != "autosave"] or ["(none)"]
            ui.update_select("load_session", choices=choices)

        @reactive.effect
        @reactive.event(input.save_session)
        def _save_session():
            name = input.session_name().strip()
            if not name:
                ui.notification_show("Enter a session name first.", type="warning")
                return
            save_session(state, name)
            _refresh_session_choices()
            ui.notification_show(f"Session '{name}' saved.", type="message")

        @reactive.effect
        @reactive.event(input.restore_session)
        def _restore_session():
            name = input.load_session()
            if not name or name == "(none)":
                ui.notification_show("Select a session to load.", type="warning")
                return
            try:
                loaded = load_session(state, name)
            except ValueError as e:
                ui.notification_show(str(e), type="error")
                return
            state._notify()
            ui.notification_show(f"Session '{name}' restored ({len(loaded)} datasets).", type="message")

        # Populate session dropdown on startup
        _refresh_session_choices()

    return App(app_ui, server, static_assets=Path(__file__).parent / "www")


app = create_app()


def _port_is_free(host: str, port: int) -> bool:
    """Return True if *port* can be bound on *host* right now."""
    import socket

    # Deliberately NOT setting SO_REUSEADDR: on Windows that flag lets a
    # socket bind a port another socket already holds, so the probe would
    # report a busy port as free. uvicorn sets it, which is exactly the case
    # this function exists to detect.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _resolve_port(host: str, requested: int | None, default: int = 8000) -> int:
    """Choose a port to serve on.

    An explicitly requested port is honoured or the caller is told it is taken
    -- silently moving somebody off the port they asked for is worse than
    failing. When no port was requested and the default is busy (usually the
    app already running in another window), pick a free one instead of dying
    with "address already in use", which is not a useful thing to say to
    someone who has never used a terminal.
    """
    import socket

    if requested is not None:
        if not _port_is_free(host, requested):
            raise SystemExit(
                f"Port {requested} on {host} is already in use. "
                f"Close whatever is using it, or pass a different --port."
            )
        return requested

    if _port_is_free(host, default):
        return default

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _parse_args(argv: list[str] | None = None):
    """Parse command-line arguments for the ``pyanalytica`` command."""
    import argparse

    from pyanalytica import __version__

    parser = argparse.ArgumentParser(
        prog="pyanalytica",
        description="Start the PyAnalytica analytics workbench in your browser.",
    )
    parser.add_argument(
        "--port", type=int, default=None,
        help="Port to serve on (default: 8000, or the next free port if busy).",
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Address to bind (default: 127.0.0.1, reachable only from this computer).",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Do not open a browser window automatically.",
    )
    parser.add_argument("--version", action="version", version=f"pyanalytica {__version__}")
    return parser.parse_args(argv)


def _quiet_library_warnings() -> None:
    """Suppress deprecation notices from libraries we do not control.

    Insurance, not a fix for anything students currently see. Verified: with
    Python's default filters, every common operation -- histogram, boxplot,
    scatter, heatmap, summarize, pivot, crosstab, t-test, correlation --
    produces nothing on stderr. MatplotlibDeprecationWarning subclasses
    DeprecationWarning, which Python hides outside __main__, so the seaborn
    notices visible under pytest never reach a student's terminal.

    What a student did see was ShinyDeprecationWarning, which subclasses
    RuntimeWarning *and* which shiny registers an "always" filter for, so it
    displays regardless. That was fixed at source in 0.6.2 by using the
    renamed decorator; this filter would not have caught it.

    Kept because a library may start forcing its own category the way shiny
    does, and because a student running with -W always or a dev-mode
    interpreter would otherwise get a wall of text. Only the launcher applies
    it: warnings still appear under pytest, still appear when importing the
    package, and PYANALYTICA_WARNINGS=1 restores them here.
    """
    import os
    import warnings

    if os.environ.get("PYANALYTICA_WARNINGS"):
        return

    for category in (DeprecationWarning, PendingDeprecationWarning, FutureWarning):
        warnings.filterwarnings("ignore", category=category)


def main(argv: list[str] | None = None):
    """CLI entry point."""
    import shiny

    _quiet_library_warnings()
    args = _parse_args(argv)
    port = _resolve_port(args.host, args.port)
    url = f"http://{args.host}:{port}"

    # flush=True: stdout is block-buffered when piped, and this banner is the
    # only place a student is told which address to open. It must not sit in a
    # buffer behind uvicorn's own logging.
    if args.port is None and port != 8000:
        print(f"Port 8000 was busy, using {port} instead.", flush=True)
    print(f"PyAnalytica is starting at {url}", flush=True)
    print("Open that address in your browser if it does not open by itself.", flush=True)
    print("Press Ctrl+C in this window to stop.", flush=True)

    shiny.run_app(
        "pyanalytica.ui.app:app",
        host=args.host,
        port=port,
        launch_browser=not args.no_browser,
    )


if __name__ == "__main__":
    main()
