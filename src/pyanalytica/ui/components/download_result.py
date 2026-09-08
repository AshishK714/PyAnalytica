"""Reusable download-result component for any module with a result DataFrame."""

from __future__ import annotations

from typing import Callable

from shiny import module, render, req, ui

from pyanalytica.data.export import to_csv_bytes
from pyanalytica.ui.components.downloads import render_download


@module.ui
def download_result_ui(label: str = "Download CSV"):
    return ui.download_button("dl_btn", label, class_="btn-sm btn-outline-secondary mt-2")


@module.server
def download_result_server(
    input,
    output,
    session,
    get_df: Callable,
    filename: str | Callable[[], str] = "result",
):
    """*filename* may be a callable, for a panel whose download changes with
    what it is showing -- Evaluate saves a confusion matrix or a table of
    regression error depending on the model, and naming both after the first
    would mislabel half of them."""

    @render_download(
        filename=lambda: f"{filename() if callable(filename) else filename}.csv"
    )
    def dl_btn():
        df = get_df()
        req(df is not None)
        yield to_csv_bytes(df)
