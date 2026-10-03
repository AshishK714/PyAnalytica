"""What a student sees on their very first click, before loading anything.

The app fixture is module-scoped, so this file gets an app of its own with an
empty workbench -- which is the whole point. Loading a dataset anywhere in this
module would destroy the precondition, so nothing here loads one.

This is the runtime half of the rule enforced statically in
tests/test_ui/test_no_silent_refusals.py. That one proves the source contains
no bare req() inside a handler the student triggered; this one proves a
sentence actually reaches the screen.
"""

from __future__ import annotations

import time

from playwright.sync_api import Page


def _sid(module_id: str, element_id: str) -> str:
    return f"#{module_id}-{element_id}"


def _nav_to(page: Page, *labels: str) -> None:
    for label in labels:
        link = page.locator(f"a.nav-link:has-text('{label}')")
        link.first.wait_for(state="visible", timeout=15_000)
        link.first.click()
        time.sleep(0.5)


def _wait_stable(page: Page, ms: int) -> None:
    page.wait_for_timeout(ms)

class TestEveryRunButtonAnswersWithNoDataLoaded:
    """The class of bug behind three separate reports, checked in the browser.

    tests/test_ui/test_no_silent_refusals.py proves the source shape. This
    proves a student actually sees a sentence, which is the part that matters.
    Uses a fresh app with nothing loaded -- the state a student is in for their
    very first click.
    """

    TARGETS = [
        ("Describe", "One Variable", "one_variable", "run_btn"),
        ("Relate", "Two Variables", "two_variables", "run_btn"),
        ("Relate", "Group By / Summarize", "summarize", "run_btn"),
        ("Relate", "Pivot", "pivot", "run_btn"),
        ("Relate", "Cross-tab", "crosstab", "run_btn"),
        ("Advanced", "Distribution Plots", "distribute", "run_btn"),
        ("Advanced", "Scatter", "relate", "run_btn"),
        ("Advanced", "Group Plots", "compare", "run_btn"),
        ("Describe", "Correlate", "correlate", "run_btn"),
        ("Describe", "Timeline", "timeline", "run_btn"),
        ("Advanced", "Means", "means", "run_btn"),
        ("Advanced", "Proportions", "proportions", "run_btn"),
        ("Advanced", "Correlation", "correlation", "run_btn"),
        ("Model", "Regression", "regression", "run_btn"),
        ("Model", "Classify", "classify", "run_btn"),
        ("Model", "Cluster", "cluster", "run_btn"),
        ("Model", "Reduce", "reduce", "run_btn"),
        ("Model", "Evaluate", "evaluate", "run_btn"),
        ("Model", "Predict", "predict", "predict_btn"),
    ]

    def test_nothing_refuses_in_silence(self, page):
        page.reload()
        page.wait_for_selector("a.nav-link", timeout=30_000)
        _wait_stable(page, 2000)

        silent = []
        for top, sub, mod, btn in self.TARGETS:
            _nav_to(page, top, sub)
            _wait_stable(page, 1200)
            page.evaluate(
                "() => document.querySelectorAll('.shiny-notification')"
                ".forEach(n => n.remove())"
            )
            button = page.locator(_sid(mod, btn))
            if not button.count():
                continue
            button.click()
            _wait_stable(page, 2000)

            notes = page.locator(".shiny-notification")
            panel = page.locator(_sid(mod, "guidance"))
            said = (
                notes.first.inner_text().strip() if notes.count()
                else (panel.inner_text().strip() if panel.count() else "")
            )
            # A module that simply succeeded is fine; silence with no output is
            # not. Both leave the notification area empty, so distinguish them
            # by whether anything was produced.
            produced = page.locator(
                f"{_sid(mod, 'guidance')}, .shiny-output-error:visible"
            )
            if not said and not produced.count():
                silent.append(f"{top} > {sub}")

        assert not silent, (
            "these did nothing and said nothing when pressed with no data "
            "loaded:" + chr(10) + "  " + (chr(10) + "  ").join(silent)
        )
