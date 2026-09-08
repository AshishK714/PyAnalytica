"""Data > Combine module — merge, append, reshape."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.core.state import Operation, WorkbenchState
from pyanalytica.data.combine import detect_overlapping_columns, merge_dataframes
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.status import status_server, status_ui
from pyanalytica.ui.components.selects import (
    update_choices,
    update_multi_choices,
)

from datetime import datetime


@module.ui
def combine_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.h5("Merge Two Datasets"),
            ui.input_select("left", "Left Dataset", choices=[]),
            ui.input_select("right", "Right Dataset", choices=[]),
            ui.input_select("join_key", "Join Key", choices=[]),
            ui.input_select("how", "Join Type",
                choices=["inner", "left", "right", "outer"]),
            ui.input_text("result_name", "Result Name", value="merged"),
            ui.output_ui("overlap_panel"),
            ui.input_action_button("merge_btn", "Merge", class_="btn-primary w-100 mt-2"),
            width=300,
        ),
        # Above the output: a failure belongs where the result would be.
        status_ui("status"),
        ui.output_text("merge_info"),
        ui.output_data_frame("merge_preview"),
        code_panel_ui("code"),
    )


@module.server
def combine_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    status = status_server("status")

    @reactive.effect
    def _update_datasets():
        # Read change signal to re-fire when datasets are added/removed
        if state._change_signal is not None:
            state._change_signal()
        names = state.dataset_names()
        update_choices(input, "left", names)
        update_choices(input, "right", names)

    @reactive.effect
    def _update_keys():
        left_name = input.left()
        right_name = input.right()
        if left_name and right_name and left_name in state.datasets and right_name in state.datasets:
            left_cols = set(state.get(left_name).columns)
            right_cols = set(state.get(right_name).columns)
            common = sorted(left_cols & right_cols)
            update_choices(input, "join_key", common)

    @reactive.calc
    def _overlap_info():
        left_name = input.left()
        right_name = input.right()
        key = input.join_key()
        if (
            not left_name or not right_name or not key
            or left_name not in state.datasets
            or right_name not in state.datasets
        ):
            return []
        return detect_overlapping_columns(
            state.get(left_name), state.get(right_name), on=key,
        )

    @render.ui
    def overlap_panel():
        infos = _overlap_info()
        if not infos:
            return None

        items = []
        items.append(ui.tags.hr())
        items.append(ui.tags.strong("Overlapping columns detected"))
        for info in infos:
            default = "left" if info.pct_same == 100.0 else "both"
            label = (
                f"{info.column}: {info.n_same}/{info.total_comparable} match "
                f"({info.pct_same}%)"
            )
            note = ""
            if info.pct_same == 100.0:
                note = " (identical - recommended: keep left)"
            items.append(
                ui.input_radio_buttons(
                    f"keep_{info.column}",
                    ui.span(label, ui.tags.small(note, style="color:#888")),
                    choices={"left": "Keep left", "right": "Keep right", "both": "Keep both"},
                    selected=default,
                    inline=True,
                )
            )
        items.append(ui.tags.hr())
        items.append(ui.tags.small("Suffixes for 'Keep both' columns:", style="color:#666"))
        items.append(
            ui.layout_columns(
                ui.input_text("suffix_left", "Left suffix", value="_left"),
                ui.input_text("suffix_right", "Right suffix", value="_right"),
                col_widths=[6, 6],
            )
        )
        return ui.div(*items)

    @reactive.effect
    @reactive.event(input.merge_btn)
    def _merge():
        left_name = input.left()
        right_name = input.right()
        key = input.join_key()
        how = input.how()
        result_name = input.result_name() or "merged"
        if not require(
            left_name and right_name and key,
            "Choose both datasets and the column to join them on.",
        ):
            return

        # Collect keep choices from overlap radio buttons
        infos = _overlap_info()
        keep: dict[str, str] = {}
        for info in infos:
            val = input[f"keep_{info.column}"]()
            if val:
                keep[info.column] = val

        # Collect suffix preferences
        has_both = any(v == "both" for v in keep.values())
        suffixes = ("_x", "_y")
        if infos and has_both:
            sl = input.suffix_left() or "_left"
            sr = input.suffix_right() or "_right"
            suffixes = (sl, sr)

        try:
            result = merge_dataframes(
                state.get(left_name), state.get(right_name),
                on=key, how=how,
                left_name=left_name, right_name=right_name,
                keep=keep,
                suffixes=suffixes,
            )
            state.load(result_name, result.merged)
            state.codegen.record(result.code)
            last_code.set(result.code.code)

            msg = (
                f"Merged: {result.result_rows} rows | "
                f"Left unmatched: {result.left_unmatched} | "
                f"Right unmatched: {result.right_unmatched}"
            )
            status.done(msg)
        except Exception as e:
            status.failed(str(e))

    @render.text
    def merge_info():
        return "Select two datasets and a common key column to merge."

    @render.data_frame
    def merge_preview():
        df = get_current_df()
        req(df is not None)
        return render.DataGrid(df.head(100), height="400px")

    code_panel_server("code", get_code=last_code)
