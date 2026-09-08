"""A refused filter must say so and leave the table standing.

The library refuses a filter that cannot mean anything, and that is unit-tested.
What only the app can show is what happens next. `filtered_df()` is a
reactive.calc that the table, the row count and the download all read, so a
filter accepted into the list and *then* found impossible took every one of
those outputs down at once -- the panel emptied, and the reason appeared
nowhere. The filter is checked as it is added instead, and this is the test that
the checking happens there rather than one layer too late.
"""

from __future__ import annotations

import time

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


def _add_filter(page: Page, column: str, operator: str, value: str) -> None:
    _select_option(page, _sid("view", "filter_col"), column)
    _wait_stable(page, 800)
    _select_option(page, _sid("view", "filter_op"), operator)
    _wait_stable(page, 500)
    box = page.locator(_sid("view", "filter_val"))
    box.fill(value)
    _wait_stable(page, 500)
    _click_button(page, _sid("view", "add_filter"))
    _wait_stable(page, 2500)


def _table_text(page: Page) -> str:
    grid = page.locator(_sid("view", "view_table"))
    expect(grid).to_be_visible(timeout=15_000)
    return grid.inner_text()


class TestARefusedFilterDoesNotBreakThePanel:

    def test_t01_load_titanic(self, page: Page):
        _nav_to(page, "Data", "Load")
        _wait_stable(page, 1500)
        page.wait_for_selector(_sid("load", "bundled_name"), state="attached", timeout=10_000)
        _select_option(page, _sid("load", "bundled_name"), "titanic")
        _wait_stable(page)
        _click_button(page, _sid("load", "load_btn"))
        _wait_stable(page, 4000)
        _nav_to(page, "Data", "View")
        _wait_stable(page, 2500)
        assert _table_text(page).strip()

    def test_t02_a_working_filter_still_works(self, page: Page):
        _add_filter(page, "Age", ">", "60")
        info = page.locator(_sid("view", "filter_info")).inner_text()
        assert info.strip(), "the row count says nothing"
        assert _table_text(page).strip()

    def test_t03_text_against_a_numeric_column_is_refused(self, page: Page):
        _click_button(page, _sid("view", "clear_filters"))
        _wait_stable(page, 1500)
        _add_filter(page, "Age", "==", "Southampton")

        notice = page.locator(".shiny-notification")
        assert notice.count(), "the filter was accepted with no message"
        text = " ".join(notice.all_inner_texts())
        assert "holds numbers" in text, f"unhelpful message: {text!r}"

    def test_t04_the_table_survives_the_refusal(self, page: Page):
        """The old failure took out the table, the count and the download."""
        assert _table_text(page).strip(), "the table went blank after a refused filter"
        page.locator(_sid("view", "filter_info")).wait_for(state="visible", timeout=10_000)
        assert page.locator(_sid("view", "filter_info")).inner_text().strip()

    def test_t05_ordering_a_text_column_by_a_number_is_refused(self, page: Page):
        """This one used to return every row and look completely ordinary."""
        _click_button(page, _sid("view", "clear_filters"))
        _wait_stable(page, 1500)
        _add_filter(page, "Sex", ">", "60")

        notice = page.locator(".shiny-notification")
        assert notice.count(), "a filter matching every row was accepted silently"
        assert "alphabetically" in " ".join(notice.all_inner_texts())
        assert _table_text(page).strip()
