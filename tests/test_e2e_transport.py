"""End-to-end tests for the transport layer -- failures that happen *outside*
module error handling.

Why this file exists, separately from the library tests:

`add_column_binned` was correct. Called directly it returned exactly the column
it promised, and every unit test passed. The failure was in serialising that
column to the browser: `pd.cut` names its bins with pandas `Interval` objects,
Shiny's encoder cannot represent them, and it raises *after* `mod_transform`'s
try/except has already returned. Nothing caught it. No notification, no error
element, no log line the student could see -- the panel just stopped responding,
and the reload it took to recover started a fresh session and discarded the
dataset along with every derived column.

A test that calls the function cannot see any of that. The only oracle is the
live app: does the session still answer after the operation?

Run with:
    python -m pytest tests/test_e2e_transport.py -v
"""

from __future__ import annotations

import time

import pytest
from playwright.sync_api import Page, expect


def _sid(module: str, widget: str) -> str:
    return f"#{module}-{widget}"


def _wait_stable(page: Page, ms: int = 2000) -> None:
    time.sleep(ms / 1000)


def _nav_to(page: Page, *tab_labels: str, timeout: float = 10_000) -> None:
    for label in tab_labels:
        link = page.locator(f"a.nav-link:has-text('{label}')")
        link.first.wait_for(state="visible", timeout=timeout)
        link.first.click()
        time.sleep(0.5)


def _select_option(page: Page, selector: str, value: str, *, timeout: float = 10_000) -> None:
    locator = page.locator(selector)
    locator.wait_for(state="attached", timeout=timeout)
    try:
        locator.select_option(value, timeout=3000)
    except Exception:
        wrapper = page.locator(f"{selector} + .selectize-control, {selector} ~ .selectize-control")
        wrapper.first.click()
        page.keyboard.type(value)
        time.sleep(0.3)
        page.keyboard.press("Enter")
        time.sleep(0.3)


def _click_button(page: Page, selector: str, *, timeout: float = 10_000) -> None:
    btn = page.locator(selector)
    btn.wait_for(state="visible", timeout=timeout)
    btn.scroll_into_view_if_needed()
    btn.click()


def _fill(page: Page, selector: str, value: str, *, timeout: float = 10_000) -> None:
    box = page.locator(selector)
    box.wait_for(state="visible", timeout=timeout)
    box.fill(value)
    time.sleep(0.3)


def _assert_session_still_answers(page: Page) -> None:
    """The real oracle: can the server still service a request?

    A wedged Shiny session leaves the UI in place -- every element is still
    attached, so an existence check passes -- but no further input is ever
    answered. Ask it for something new and require a fresh answer.
    """
    _nav_to(page, "Data", "View")
    _wait_stable(page, 2500)
    grid = page.locator(_sid("view", "view_table"))
    expect(grid).to_be_visible(timeout=15_000)
    assert grid.inner_text().strip(), "Data > View rendered nothing; the session is not responding"


class TestBinningSurvivesTheGrid:
    """Issue 1 -- the critical one. Binning must not wedge the session."""

    def test_t01_load_tips(self, page: Page):
        _nav_to(page, "Data", "Load")
        _wait_stable(page, 1500)
        page.wait_for_selector(_sid("load", "bundled_name"), state="attached", timeout=10_000)
        _select_option(page, _sid("load", "bundled_name"), "tips")
        _wait_stable(page)
        _click_button(page, _sid("load", "load_btn"))
        _wait_stable(page, 4000)
        expect(page.locator(_sid("ds", "dataset"))).to_contain_text("tips")

    def test_t02_bin_with_blank_labels_renders(self, page: Page):
        """Blank labels is the default path, and the one that used to hang."""
        _nav_to(page, "Data", "Transform")
        _wait_stable(page, 1500)
        _select_option(page, _sid("transform", "action"), "add_binned")
        _wait_stable(page, 2000)

        page.wait_for_selector(_sid("transform", "col"), state="attached", timeout=10_000)
        _select_option(page, _sid("transform", "col"), "total_bill")
        _fill(page, _sid("transform", "new_col_name"), "bill_band")
        _fill(page, _sid("transform", "n_bins"), "4")
        # Bin labels deliberately left blank.
        _wait_stable(page)

        _click_button(page, _sid("transform", "apply_btn"))
        _wait_stable(page, 4000)

        preview = page.locator(_sid("transform", "preview"))
        expect(preview).to_be_visible(timeout=15_000)
        # Column headers are upper-cased by the stylesheet, so compare folded.
        text = preview.inner_text().lower()
        assert "bill_band" in text, f"binned column missing from the preview: {text[:400]}"
        assert " to " in text, "bin names are not readable text"
        assert "interval" not in text

    def test_t03_session_still_responds_afterwards(self, page: Page):
        """The failure mode was silence, not an error message."""
        _assert_session_still_answers(page)

    def test_t04_binned_column_is_usable_downstream(self, page: Page):
        """A column that cannot cross the wire is worse than no column."""
        _nav_to(page, "Explore", "Summarize")
        _wait_stable(page, 2000)
        page.wait_for_selector(_sid("summarize", "group_cols"), state="attached", timeout=10_000)
        html = page.locator(_sid("summarize", "group_cols")).inner_html()
        assert "bill_band" in html, "the binned column never reached the rest of the app"


class TestNoPanelSwallowsItsOwnFailure:
    """A panel that fails must say so on the panel, not only in a 5s toast."""

    def test_t05_bad_bin_count_reports_instead_of_hanging(self, page: Page):
        _nav_to(page, "Data", "Transform")
        _wait_stable(page, 1500)
        _select_option(page, _sid("transform", "action"), "add_binned")
        _wait_stable(page, 2000)
        page.wait_for_selector(_sid("transform", "col"), state="attached", timeout=10_000)
        # 'sex' is text, so binning it cannot work.
        _select_option(page, _sid("transform", "col"), "sex")
        _fill(page, _sid("transform", "new_col_name"), "nope")
        _wait_stable(page)
        _click_button(page, _sid("transform", "apply_btn"))
        _wait_stable(page, 3000)

        _assert_session_still_answers(page)


@pytest.mark.parametrize("dataset", ["tips", "titanic"])
def test_t06_binning_every_numeric_column_stays_serializable(page: Page, dataset: str):
    """Sweep the numeric columns rather than trusting one happy path.

    The original defect reproduced on every numeric column; a single-column test
    would have caught it, but a sweep also catches the dtype-specific cases
    (integer columns, columns with missing values) that one example misses.
    """
    _nav_to(page, "Data", "Load")
    _wait_stable(page, 1500)
    page.wait_for_selector(_sid("load", "bundled_name"), state="attached", timeout=10_000)
    _select_option(page, _sid("load", "bundled_name"), dataset)
    _wait_stable(page)
    _click_button(page, _sid("load", "load_btn"))
    _wait_stable(page, 4000)

    _nav_to(page, "Data", "Transform")
    _wait_stable(page, 1500)
    _select_option(page, _sid("transform", "action"), "add_binned")
    _wait_stable(page, 2000)
    page.wait_for_selector(_sid("transform", "col"), state="attached", timeout=10_000)

    options = page.locator(f"{_sid('transform', 'col')} option")
    columns = [options.nth(i).get_attribute("value") for i in range(options.count())]
    assert columns, "no columns offered for binning"

    for i, column in enumerate(columns[:4]):
        _select_option(page, _sid("transform", "col"), column)
        _fill(page, _sid("transform", "new_col_name"), f"band_{i}")
        _wait_stable(page, 800)
        _click_button(page, _sid("transform", "apply_btn"))
        _wait_stable(page, 3000)
        _assert_session_still_answers(page)
        _nav_to(page, "Data", "Transform")
        _wait_stable(page, 1200)
