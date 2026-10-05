"""Data > Profile module — data quality overview."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.core import round_df
from pyanalytica.core.state import WorkbenchState
from pyanalytica.data.profile import profile_dataframe
from pyanalytica.ui.components.decimals_control import decimals_server, decimals_ui


@module.ui
def profile_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.p(
                "This profiles the active dataset, the one chosen in Data > Load. "
                "It follows whichever dataset is active; press Refresh if it looks "
                "out of date after a change."
            ),
            ui.input_action_button("refresh", "Refresh Profile", class_="btn-outline-primary w-100"),
            width=300,
        ),
        ui.navset_tab(
            ui.nav_panel("Overview", ui.output_ui("overview")),
            ui.nav_panel("Quality", ui.output_ui("quality")),
            ui.nav_panel("Columns", decimals_ui("dec"), ui.output_data_frame("column_details")),
        ),
    )


@module.server
def profile_server(input, output, session, state: WorkbenchState, get_current_df):
    get_dec = decimals_server("dec")

    @reactive.calc
    def profile():
        input.refresh()
        df = get_current_df()
        req(df is not None)
        return profile_dataframe(df)

    @render.ui
    def overview():
        p = profile()
        return ui.TagList(
            ui.h5("Dataset Overview"),
            ui.tags.table(
                ui.tags.tr(ui.tags.td("Rows"), ui.tags.td(str(p.shape[0]))),
                ui.tags.tr(ui.tags.td("Columns"), ui.tags.td(str(p.shape[1]))),
                ui.tags.tr(ui.tags.td("Memory"), ui.tags.td(p.memory_usage)),
                class_="table table-sm",
            ),
            ui.h5("Column Types"),
            ui.tags.table(
                *[ui.tags.tr(
                    ui.tags.td(cp.name),
                    ui.tags.td(cp.dtype),
                    ui.tags.td(cp.column_type.value),
                    ui.tags.td(f"{p.shape[0] - cp.non_null_count:,}"),
                    ui.tags.td(f"{cp.non_null_pct}%"),
                    ui.tags.td(str(cp.unique_count)),
                ) for cp in p.column_profiles],
                ui.tags.thead(ui.tags.tr(
                    ui.tags.th("Column"), ui.tags.th("Dtype"), ui.tags.th("Type"),
                    ui.tags.th("Missing"), ui.tags.th("Non-null"), ui.tags.th("Unique"),
                )),
                class_="table table-sm table-striped",
            ),
        )

    @render.ui
    def quality():
        p = profile()
        flags = p.quality_flags
        items = []

        if flags.missing_columns:
            items.append(ui.h5("Missing Values"))
            # A count as well as a share: "3,088 of 5,000" is what a write-up
            # needs when it says how many rows an analysis dropped.
            missing_n = {cp.name: p.shape[0] - cp.non_null_count for cp in p.column_profiles}
            rows = [ui.tags.tr(ui.tags.td(col), ui.tags.td(f"{missing_n.get(col, 0):,}"),
                               ui.tags.td(f"{pct}%"))
                    for col, pct in flags.missing_columns]
            items.append(ui.tags.table(
                ui.tags.thead(ui.tags.tr(ui.tags.th("Column"), ui.tags.th("Missing"),
                                         ui.tags.th("% Missing"))),
                *rows, class_="table table-sm",
            ))

        items.append(ui.p(f"Duplicate rows: {flags.duplicate_rows}"))

        if flags.constant_columns:
            items.append(ui.p(f"Constant columns: {', '.join(flags.constant_columns)}"))
        if flags.potential_ids:
            items.append(ui.p(f"Potential ID columns: {', '.join(flags.potential_ids)}"))
        if flags.type_mismatches:
            items.append(ui.p(f"Possible type mismatches: {', '.join(flags.type_mismatches)}"))

        return ui.TagList(*items) if items else ui.p("No quality issues detected.")

    @render.data_frame
    def column_details():
        p = profile()
        import pandas as pd
        data = []
        for cp in p.column_profiles:
            row = {
                "Column": cp.name, "Type": cp.column_type.value,
                "Missing": p.shape[0] - cp.non_null_count,
                "Non-null %": cp.non_null_pct, "Unique": cp.unique_count,
                "Mean": cp.mean, "Median": cp.median,
                "Std": cp.std, "Min": cp.min_val, "Max": cp.max_val,
            }
            data.append(row)
        return render.DataGrid(round_df(pd.DataFrame(data), get_dec()), height="500px")
