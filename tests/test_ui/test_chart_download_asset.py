"""The chart download script ships with the package and the page loads it."""

from pathlib import Path

WWW = Path(__file__).resolve().parents[2] / "src" / "pyanalytica" / "ui" / "www"


def test_the_script_exists_and_targets_every_plot_output():
    js = (WWW / "chart_download.js").read_text(encoding="utf-8")
    assert ".shiny-plot-output" in js
    assert "Download PNG" in js
    # It must save the picture on screen, not ask the server to redraw it.
    assert "img.src" in js


def test_the_app_includes_the_script_tag():
    source = (WWW.parent / "app.py").read_text(encoding="utf-8")
    assert '<script src="chart_download.js" defer></script>' in source


def test_the_button_is_styled_and_hidden_when_printing():
    css = (WWW / "style.css").read_text(encoding="utf-8")
    assert ".pa-chart-download" in css
    assert "@media print" in css
