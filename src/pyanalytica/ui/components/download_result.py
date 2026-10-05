"""Reusable download-result component for any module with a result DataFrame."""

from __future__ import annotations

import re
from typing import Callable

from shiny import module, render, req, ui

from pyanalytica.core import round_df
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
    decimals: Callable[[], int] | None = None,
):
    """*filename* may be a callable, for a panel whose download changes with
    what it is showing -- Evaluate saves a confusion matrix or a table of
    regression error depending on the model, and naming both after the first
    would mislabel half of them. It is made safe for a file name here.

    *decimals* is the panel's decimals control, for a results table: the
    file then holds the numbers the screen showed. Without it every digit
    went out (8434.268297856202 beside 8434.27 on screen), and a learner
    pasting into a report rounded each table by hand. Data downloads (a
    filtered dataset, predictions) leave it out and keep full precision.
    """

    def _name() -> str:
        raw = filename() if callable(filename) else filename
        return file_slug(raw)

    @render_download(filename=lambda: f"{_name()}.csv")
    def dl_btn():
        df = get_df()
        req(df is not None)
        if decimals is None:
            yield to_csv_bytes(df)
        else:
            places = int(decimals())
            yield to_csv_bytes(round_df(df, places), decimals=places)


def file_slug(text: str | None, fallback: str = "result") -> str:
    """A description as a file name: "charges by region, split by smoker"
    becomes "charges_by_region_split_by_smoker". Every download from one
    panel used to share one name, so a learner ended up with relate (1).csv
    to relate (12).csv and no way to tell them apart."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", str(text or "")).strip("_")[:80]
    return slug or fallback
