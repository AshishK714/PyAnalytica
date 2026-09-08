"""
Comprehensive Playwright end-to-end test suite for the PyAnalytica Shiny app.

Run with:
    PYTHONPATH=src python -m pytest tests/test_e2e.py -v

Requirements:
    pip install pytest playwright pytest-playwright
    playwright install chromium
"""

from __future__ import annotations

import ast
import os
import random
import shutil
import socket
import subprocess
import tempfile
import sys
import time
from typing import Generator

import pytest
from playwright.sync_api import Page, expect


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Shiny module-namespaced selector helpers
#
# In Shiny for Python, a module with namespace "load" and widget id "source"
# produces an HTML element with id="load-source".  These helpers build
# the correct CSS selectors.
# ---------------------------------------------------------------------------

def _sid(module: str, widget: str) -> str:
    """Build a '#module-widget' CSS selector for a Shiny module element."""
    return f"#{module}-{widget}"


def _select_option(page: Page, selector: str, value: str, *, timeout: float = 10_000) -> None:
    """
    Set a Shiny select-input to *value*.

    Shiny uses selectize.js for some inputs and plain <select> for others.
    We try the simple select_option first and fall back to typing into
    a selectize wrapper if that fails.
    """
    locator = page.locator(selector)
    locator.wait_for(state="attached", timeout=timeout)
    try:
        locator.select_option(value, timeout=3000)
    except Exception:
        # Selectize: click the control, type value, press Enter
        wrapper = page.locator(f"{selector} + .selectize-control, {selector} ~ .selectize-control")
        if wrapper.count() > 0:
            wrapper.locator(".selectize-input").click()
            page.keyboard.type(value, delay=50)
            page.keyboard.press("Enter")
        else:
            # Last resort: try JavaScript
            page.evaluate(
                f"""(v) => {{
                    const el = document.querySelector('{selector}');
                    if (el) {{ el.value = v; el.dispatchEvent(new Event('change')); }}
                }}""",
                value,
            )


def _select_multiple(page: Page, selector: str, values: list[str], *, timeout: float = 10_000) -> None:
    """
    Set a Shiny selectize-multiple input to the given list of values.

    Works for both selectize.js and plain <select multiple> elements.
    """
    locator = page.locator(selector)
    locator.wait_for(state="attached", timeout=timeout)

    # Try plain multi-select first
    try:
        locator.select_option(values, timeout=3000)
        return
    except Exception:
        pass

    # Selectize: click and type each value
    wrapper = page.locator(f"{selector} + .selectize-control, {selector} ~ .selectize-control")
    if wrapper.count() > 0:
        selectize_input = wrapper.locator(".selectize-input")
        for val in values:
            selectize_input.click()
            page.keyboard.type(val, delay=30)
            time.sleep(0.3)
            page.keyboard.press("Enter")
            time.sleep(0.3)
    else:
        # JavaScript fallback for multi-select
        page.evaluate(
            f"""(vals) => {{
                const el = document.querySelector('{selector}');
                if (el) {{
                    Array.from(el.options).forEach(o => o.selected = vals.includes(o.value));
                    el.dispatchEvent(new Event('change'));
                }}
            }}""",
            values,
        )


def _click_button(page: Page, selector: str, *, timeout: float = 10_000) -> None:
    """Click a Shiny action button and give the server a moment to respond."""
    btn = page.locator(selector)
    btn.wait_for(state="visible", timeout=timeout)
    btn.scroll_into_view_if_needed()
    btn.click()


def _open_section(page: Page, title: str, *, timeout: float = 10_000) -> None:
    """Open a disclosure section by its title.

    Content inside a closed section is attached but never drawn, so an
    assertion about it has to open the section first or it passes vacuously.
    """
    button = page.locator(f".accordion-button:has-text('{title}')")
    button.first.wait_for(state="visible", timeout=timeout)
    if button.first.get_attribute("aria-expanded") != "true":
        button.first.click()
        time.sleep(2.5)


def _nav_to(page: Page, *tab_labels: str, timeout: float = 10_000) -> None:
    """
    Navigate through Shiny's navbar and sub-tabs by visible label text.

    Usage:
        _nav_to(page, "Data", "Load")        # top-nav "Data", sub-tab "Load"
        _nav_to(page, "Explore", "Pivot")     # top-nav "Explore", sub-tab "Pivot"
    """
    for label in tab_labels:
        link = page.locator(f"a.nav-link:has-text('{label}')")
        # There may be duplicates (navbar + sub-tab); click the first visible one
        link.first.wait_for(state="visible", timeout=timeout)
        link.first.click()
        time.sleep(0.5)


def _assert_no_shiny_errors(page: Page) -> None:
    """Assert that no Shiny output-error elements are visible on the page."""
    errors = page.locator(".shiny-output-error:visible")
    count = errors.count()
    if count > 0:
        texts = [errors.nth(i).inner_text() for i in range(count)]
        pytest.fail(f"Found {count} Shiny output error(s): {texts}")


# ---------------------------------------------------------------------------
# Output oracles
#
# The suite used to check that an element existed. A human tester found three
# things that pass that bar and are still broken:
#
#   * An exception rendered as ordinary text inside the output, because the
#     module caught it and returned a string. `.shiny-output-error` never
#     appears, so _assert_no_shiny_errors sees nothing wrong.
#   * An output element that exists and is empty -- Correlate with a single
#     column selected produced no chart, no message, nothing.
#   * A chart or table that renders for one column type and crashes for
#     another. Pivoting tips by `sex` works; by `size` it did not.
#
# These three helpers close those gaps.
# ---------------------------------------------------------------------------

# Text that means an exception reached the screen, whatever it is wrapped in.
_ERROR_TEXT = (
    "traceback", "has no attribute", "keyerror", "valueerror", "typeerror",
    "indexerror", "attributeerror", "not in index", "object is not",
    "unexpected keyword", "does not support", "cannot be", "nonetype",
)


def _assert_no_error_text(page: Page, selector: str) -> None:
    """Fail if an output region is displaying what looks like an exception.

    Modules that catch their own exceptions and return the message as text
    produce no .shiny-output-error, so the older check passes while the
    student is looking at a stack-trace fragment.
    """
    region = page.locator(selector)
    if region.count() == 0:
        return
    text = region.first.inner_text().strip().lower()
    for marker in _ERROR_TEXT:
        if marker in text:
            pytest.fail(
                f"{selector} is showing an error message rather than output: "
                f"{' '.join(region.first.inner_text().split())[:160]}"
            )


def _assert_output_has_content(page: Page, selector: str, *, kind: str = "any") -> None:
    """Fail unless the output actually shows something.

    *kind* is "table", "image", or "any". An element that exists but renders
    nothing is the failure mode `to_be_attached()` cannot see.
    """
    region = page.locator(selector)
    expect(region).to_be_attached()
    _assert_no_error_text(page, selector)

    tables = region.locator("table, .shiny-data-grid")
    images = region.locator("img")
    text = region.first.inner_text().strip() if region.first.is_visible() else ""

    if kind == "table":
        if tables.count() == 0:
            pytest.fail(f"{selector}: expected a table, found none (text: {text[:120]!r})")
        return
    if kind == "image":
        if images.count() == 0:
            pytest.fail(f"{selector}: expected a chart, found none (text: {text[:120]!r})")
        box = images.first.bounding_box()
        if box and (box["width"] < 50 or box["height"] < 50):
            pytest.fail(f"{selector}: chart rendered at {box['width']}x{box['height']}")
        return

    if tables.count() == 0 and images.count() == 0 and not text:
        pytest.fail(f"{selector}: element exists but shows nothing at all")


def _assert_choices_include(page: Page, selector: str, expected: list[str]) -> None:
    """Fail if a dropdown is missing options a student would look for.

    Cross-tab offered no way to pick `Survived`, because a 0/1 integer column
    classifies as numeric and the categorical filter drops it. Nothing errored;
    the option simply was not there.
    """
    options = [o.strip() for o in page.locator(f"{selector} option").all_inner_texts()]
    missing = [want for want in expected if want not in options]
    if missing:
        pytest.fail(
            f"{selector} is missing option(s) {missing}. Offered: {options[:12]}"
        )


def _wait_stable(page: Page, ms: int = 2000) -> None:
    """Wait for Shiny reactivity to settle."""
    time.sleep(ms / 1000)


# ---------------------------------------------------------------------------
# "Show Code" panel helpers
#
# Every analytics module mounts the shared component as code_panel_ui("code"),
# which nests a Shiny module inside a Shiny module.  Namespaces join with "-",
# so the toggle button for module "distribute" has id
# "distribute-code-toggle_code" and the output "distribute-code-code_display".
# ---------------------------------------------------------------------------

def _nested_sid(module: str, child: str, widget: str) -> str:
    """Build a selector for a widget inside a module nested in another module.

    Shiny joins namespaces with "-", so a widget "decimals" in child module
    "dec" mounted inside module "view" has id "view-dec-decimals".  Nesting
    _sid() inside itself produces "#view-#dec-decimals", which matches nothing.
    """
    return f"#{module}-{child}-{widget}"


def _code_sid(module: str, widget: str) -> str:
    """Build a selector for a widget inside a module's nested code panel."""
    return _nested_sid(module, "code", widget)


def _open_code_panel(page: Page, module: str, *, timeout: float = 10_000) -> None:
    """Expand the Show Code panel for *module* if it is currently collapsed.

    The panel keeps its open/closed state for the life of the session, and the
    page fixture is module-scoped, so this must be idempotent.
    """
    toggle = page.locator(_code_sid(module, "toggle_code"))
    toggle.wait_for(state="visible", timeout=timeout)
    toggle.scroll_into_view_if_needed()
    if "Show Code" in toggle.inner_text():
        toggle.click()
        _wait_stable(page, 1200)


def _read_code(page: Page, module: str, *, timeout: float = 10_000) -> str:
    """Open the code panel for *module* and return the emitted snippet text."""
    _open_code_panel(page, module)
    block = page.locator(f"{_code_sid(module, 'code_display')} pre code")
    block.wait_for(state="visible", timeout=timeout)
    return block.inner_text()


def _assert_code(page: Page, module: str, *fragments: str) -> str:
    """Assert the module emitted a usable code snippet, and return it.

    Two tiers of check:
      1. Universal -- the panel produced something other than the placeholder,
         and that something parses as valid Python.  A snippet a student cannot
         paste into a notebook is a bug regardless of its contents.
      2. Specific -- each fragment in *fragments* appears in the snippet, which
         pins the emitted code to the operation the user actually asked for.
    """
    code = _read_code(page, module)

    assert code.strip(), f"[{module}] Show Code panel is empty"
    assert "No code generated yet." not in code, (
        f"[{module}] Show Code still shows the placeholder -- the action ran "
        f"but recorded no snippet"
    )

    try:
        ast.parse(code)
    except SyntaxError as exc:
        pytest.fail(
            f"[{module}] emitted code is not valid Python ({exc.msg} at line "
            f"{exc.lineno}):" + chr(10) + code
        )

    missing = [f for f in fragments if f not in code]
    if missing:
        pytest.fail(
            f"[{module}] emitted code is missing expected fragment(s) "
            f"{missing}:" + chr(10) + code
        )
    return code


# ---------------------------------------------------------------------------
# Navigation discovery
# ---------------------------------------------------------------------------

def _discover_nav(page: Page) -> "dict[str, list[str]]":
    """Read the app's navigation structure from the live DOM.

    Returns {top_level_label: [sub_tab_labels]}; a top-level panel with no
    sub-tabs (e.g. "Homework") maps to an empty list.  Discovering this rather
    than hand-listing it means a tab added to app.py is swept automatically.
    """
    tops = [
        t.strip()
        for t in page.locator(
            "ul.navbar-nav > li.nav-item > a.nav-link"
        ).all_inner_texts()
        if t.strip()
    ]

    structure: "dict[str, list[str]]" = {}
    for top in tops:
        _nav_to(page, top)
        _wait_stable(page, 1200)
        subs = [
            t.strip()
            for t in page.locator(
                "ul.nav-tabs:visible > li.nav-item > a.nav-link"
            ).all_inner_texts()
            if t.strip()
        ]
        structure[top] = subs
    return structure


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# ============================================================================
# Test functions — ordered by naming convention (t01_, t02_, ...) so that
# pytest collects them in the intended execution sequence.
# ============================================================================


# ---------------------------------------------------------------------------
# INFRASTRUCTURE
# ---------------------------------------------------------------------------

class TestInfrastructure:
    """Tests that verify the app boots correctly and the header controls exist."""

    def test_t01_app_returns_200(self, app_url: str):
        """GET / returns HTTP 200."""
        import urllib.request
        resp = urllib.request.urlopen(app_url, timeout=10)
        assert resp.status == 200

    def test_t02_header_has_dataset_selector(self, page: Page):
        """The dataset selector dropdown is present in the header."""
        sel = page.locator(_sid("ds", "dataset"))
        expect(sel).to_be_attached()

    def test_t03_decimals_selector_on_view_tab(self, page: Page):
        """The decimals dropdown is present on the Data > View tab (not global header)."""
        _nav_to(page, "Data", "View")
        _wait_stable(page, 2000)
        sel = page.locator(_nested_sid("view", "dec", "decimals"))
        expect(sel).to_be_attached()

    def test_t04_initial_dropdown_shows_none(self, page: Page):
        """Before loading data the dataset selector shows '(none)'."""
        sel = page.locator(_sid("ds", "dataset"))
        selected = sel.input_value()
        assert selected == "(none)", f"Expected '(none)', got '{selected}'"


# ---------------------------------------------------------------------------
# DATA > LOAD
# ---------------------------------------------------------------------------

class TestDataLoad:
    """Tests for the Data > Load module."""

    def test_t05_load_tips(self, page: Page):
        """Load the bundled 'tips' dataset."""
        _nav_to(page, "Data", "Load")
        _wait_stable(page, 1500)

        # Source should default to 'bundled'
        source = page.locator(_sid("load", "source"))
        expect(source).to_be_attached()

        # Wait for the bundled_name select to render (it is dynamic UI)
        page.wait_for_selector(_sid("load", "bundled_name"), state="attached", timeout=10_000)
        _select_option(page, _sid("load", "bundled_name"), "tips")
        _wait_stable(page)

        _click_button(page, _sid("load", "load_btn"))
        _wait_stable(page, 4000)

        # Notification should have appeared (Shiny notifications are transient;
        # check the dataset selector updated instead)
        ds_sel = page.locator(_sid("ds", "dataset"))
        expect(ds_sel).to_contain_text("tips")
        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code. A bundled
        # dataset ships inside the package, so pd.read_csv("tips.csv") would
        # be a line that fails wherever the student runs it; the snippet loads
        # it properly and names the frame df, which is what every later step
        # refers to.
        _assert_code(page, "load", "load_dataset", "df = ")
    def test_t06_load_diamonds(self, page: Page):
        """Load the bundled 'diamonds' dataset so two datasets are available."""
        _nav_to(page, "Data", "Load")
        _wait_stable(page)

        page.wait_for_selector(_sid("load", "bundled_name"), state="attached", timeout=10_000)
        _select_option(page, _sid("load", "bundled_name"), "diamonds")
        _wait_stable(page)

        _click_button(page, _sid("load", "load_btn"))
        _wait_stable(page, 5000)

        # Dataset selector should now list both
        ds_sel = page.locator(_sid("ds", "dataset"))
        html = ds_sel.inner_html()
        assert "tips" in html, "tips should still be in the selector"
        assert "diamonds" in html, "diamonds should be in the selector"
        _assert_no_shiny_errors(page)

    def test_t07_switch_back_to_tips(self, page: Page):
        """Switch the active dataset back to tips for remaining tests.

        Every later test selects tips columns, so a silent failure here used to
        surface 26 tests downstream as a wall of unrelated timeouts.  Assert it.
        """
        _select_option(page, _sid("ds", "dataset"), "tips")
        _wait_stable(page, 2000)

        active = page.locator(_sid("ds", "dataset")).input_value()
        assert active == "tips", (
            f"Failed to switch the active dataset to tips (got '{active}'). "
            f"Every downstream test depends on this."
        )

    def test_t08_preview_table_visible(self, page: Page):
        """After loading a dataset, the preview table on Load tab shows data."""
        _nav_to(page, "Data", "Load")
        _wait_stable(page, 2000)
        # The DataGrid renders inside a container with the output id
        table = page.locator(_sid("load", "preview_table"))
        expect(table).to_be_attached()
        # It should have some rows rendered
        page.wait_for_selector(f"{_sid('load', 'preview_table')} table, {_sid('load', 'preview_table')} .shiny-data-grid", timeout=10_000)
        _assert_no_shiny_errors(page)


# ---------------------------------------------------------------------------
# DATA > PROFILE
# ---------------------------------------------------------------------------

class TestDataProfile:
    """Tests for the Data > Profile module."""

    def test_t09_profile_overview_renders(self, page: Page):
        """Navigate to Profile tab and verify overview section renders."""
        _nav_to(page, "Data", "Profile")
        _wait_stable(page, 3000)

        overview = page.locator(_sid("profile", "overview"))
        expect(overview).to_be_attached()
        # Should show shape info (rows/columns)
        page.wait_for_selector(f"{_sid('profile', 'overview')} table", timeout=15_000)
        overview_text = overview.inner_text()
        assert "Rows" in overview_text or "rows" in overview_text.lower(), \
            f"Overview should contain 'Rows', got: {overview_text[:300]}"
        _assert_no_shiny_errors(page)

    def test_t10_profile_columns_tab(self, page: Page):
        """Navigate to the Columns sub-tab within Profile."""
        # Click the "Columns" sub-tab within the Profile panel
        columns_tab = page.locator("a.nav-link:has-text('Columns')")
        if columns_tab.count() > 0:
            columns_tab.last.click()
            _wait_stable(page, 3000)
        column_details = page.locator(_sid("profile", "column_details"))
        expect(column_details).to_be_attached()
        _assert_no_shiny_errors(page)


# ---------------------------------------------------------------------------
# DATA > VIEW
# ---------------------------------------------------------------------------

class TestDataView:
    """Tests for the Data > View module."""

    def test_t11_view_table_renders(self, page: Page):
        """Navigate to the View tab and verify the data table renders."""
        _nav_to(page, "Data", "View")
        _wait_stable(page, 3000)

        table = page.locator(_sid("view", "view_table"))
        expect(table).to_be_attached()
        _assert_no_shiny_errors(page)

    def test_t12_view_filter_info(self, page: Page):
        """Filter info text is present."""
        info = page.locator(_sid("view", "filter_info"))
        expect(info).to_be_attached()
        text = info.inner_text()
        assert "rows" in text.lower() or "Showing" in text, f"Expected row info, got: {text}"
        _assert_no_shiny_errors(page)


# ---------------------------------------------------------------------------
# DATA > TRANSFORM
# ---------------------------------------------------------------------------

class TestDataTransform:
    """Tests for the Data > Transform module."""

    def test_t13_transform_actions_available(self, page: Page):
        """Navigate to Transform tab and verify all actions are in the dropdown."""
        _nav_to(page, "Data", "Transform")
        _wait_stable(page, 2000)

        action_select = page.locator(_sid("transform", "action"))
        expect(action_select).to_be_attached()

        html = action_select.inner_html()
        expected_actions = [
            "fill_missing", "drop_missing", "drop_columns",
            "convert_dtype", "drop_duplicates", "add_log",
            "add_zscore", "add_rank", "str_lower", "str_upper", "str_strip",
        ]
        for action in expected_actions:
            assert action in html, f"Action '{action}' not found in transform dropdown"
        _assert_no_shiny_errors(page)

    def test_t14_drop_columns_shows_multiselect(self, page: Page):
        """Selecting 'Drop Column(s)' action reveals a multi-select input."""
        _select_option(page, _sid("transform", "action"), "drop_columns")
        _wait_stable(page, 2000)

        # The dynamic UI should now show a selectize input for columns to drop
        drop_cols = page.locator(_sid("transform", "drop_cols"))
        expect(drop_cols).to_be_attached(timeout=10_000)
        _assert_no_shiny_errors(page)

    def test_t15_add_log_column(self, page: Page):
        """Apply an 'Add Log Column' transform and verify preview updates."""
        _select_option(page, _sid("transform", "action"), "add_log")
        _wait_stable(page, 2000)

        # Wait for dynamic controls to render
        page.wait_for_selector(_sid("transform", "col"), state="attached", timeout=10_000)
        _select_option(page, _sid("transform", "col"), "total_bill")
        _wait_stable(page)

        _click_button(page, _sid("transform", "apply_btn"))
        _wait_stable(page, 3000)

        # Verify the preview table is still showing
        preview = page.locator(_sid("transform", "preview"))
        expect(preview).to_be_attached()
        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "transform", "np.log")


# ---------------------------------------------------------------------------
# DATA > COMBINE
# ---------------------------------------------------------------------------

class TestDataCombine:
    """Tests for the Data > Combine module."""
    def test_t16_combine_tab_loads(self, page: Page):
        """Navigate to Combine tab and verify both dataset selectors exist."""
        _nav_to(page, "Data", "Combine")
        _wait_stable(page, 2000)

        left = page.locator(_sid("combine", "left"))
        right = page.locator(_sid("combine", "right"))
        expect(left).to_be_attached()
        expect(right).to_be_attached()

        # Both datasets should be in the selectors
        left_html = left.inner_html()
        right_html = right.inner_html()
        assert "tips" in left_html, "tips should be available as left dataset"
        assert "diamonds" in right_html or "tips" in right_html, "datasets should be in right selector"
        _assert_no_shiny_errors(page)


# ---------------------------------------------------------------------------
# DATA > EXPORT
# ---------------------------------------------------------------------------

class TestDataExport:
    """Tests for the Data > Export module."""

    def test_t17_export_tab_has_download_button(self, page: Page):
        """Navigate to Export tab and verify the download button exists."""
        _nav_to(page, "Data", "Export")
        _wait_stable(page, 2000)

        download_btn = page.locator(_sid("export", "download_btn"))
        expect(download_btn).to_be_attached()

        # Export info should show dataset info
        info = page.locator(_sid("export", "export_info"))
        expect(info).to_be_attached()
        _assert_no_shiny_errors(page)

    def test_t18_export_preview_shows_data(self, page: Page):
        """The export preview table is visible with data."""
        preview = page.locator(_sid("export", "export_preview"))
        expect(preview).to_be_attached()
        _assert_no_shiny_errors(page)


# ---------------------------------------------------------------------------
# EXPLORE > SUMMARIZE
# ---------------------------------------------------------------------------

class TestExploreSummarize:
    """Tests for the Explore > Summarize module."""

    def test_t19_summarize_select_and_run(self, page: Page):
        """Select group and value columns, run summarize, verify result table."""
        _nav_to(page, "Explore", "Summarize")
        _wait_stable(page, 2000)

        # Wait for column selectors to populate
        page.wait_for_selector(
            f"{_sid('summarize', 'group_cols')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        _select_multiple(page, _sid("summarize", "group_cols"), ["day"])
        _wait_stable(page)
        _select_multiple(page, _sid("summarize", "value_cols"), ["total_bill"])
        _wait_stable(page)

        _click_button(page, _sid("summarize", "run_btn"))
        _wait_stable(page, 4000)

        table = page.locator(_sid("summarize", "summary_table"))
        expect(table).to_be_attached()
        # Wait for actual data to render
        page.wait_for_selector(
            f"{_sid('summarize', 'summary_table')} table, {_sid('summarize', 'summary_table')} .shiny-data-grid",
            timeout=15_000,
        )
        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "summarize", "groupby")


# ---------------------------------------------------------------------------
# EXPLORE > PIVOT
# ---------------------------------------------------------------------------

class TestExplorePivot:
    """Tests for the Explore > Pivot module."""
    def test_t20_pivot_select_and_run(self, page: Page):
        """Select row, column, value variables, create pivot, verify table."""
        _nav_to(page, "Explore", "Pivot")
        _wait_stable(page, 2000)

        page.wait_for_selector(
            f"{_sid('pivot', 'index')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        _select_option(page, _sid("pivot", "index"), "day")
        _wait_stable(page)
        _select_option(page, _sid("pivot", "columns"), "time")
        _wait_stable(page)
        _select_option(page, _sid("pivot", "values"), "total_bill")
        _wait_stable(page)

        _click_button(page, _sid("pivot", "run_btn"))
        _wait_stable(page, 4000)

        table = page.locator(_sid("pivot", "pivot_table"))
        expect(table).to_be_attached()
        page.wait_for_selector(
            f"{_sid('pivot', 'pivot_table')} table, {_sid('pivot', 'pivot_table')} .shiny-data-grid",
            timeout=15_000,
        )
        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "pivot")


# ---------------------------------------------------------------------------
# EXPLORE > CROSS-TAB
# ---------------------------------------------------------------------------

class TestExploreCrosstab:
    """Tests for the Explore > Cross-tab module."""
    def test_t21_crosstab_chi_square(self, page: Page):
        """Select variables, run cross-tab, verify chi-square result + table."""
        _nav_to(page, "Explore", "Cross-tab")
        _wait_stable(page, 2000)

        page.wait_for_selector(
            f"{_sid('crosstab', 'row_var')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        _select_option(page, _sid("crosstab", "row_var"), "sex")
        _wait_stable(page)
        _select_option(page, _sid("crosstab", "col_var"), "smoker")
        _wait_stable(page)

        _click_button(page, _sid("crosstab", "run_btn"))
        _wait_stable(page, 4000)

        # Chi-square result should appear
        chi2 = page.locator(_sid("crosstab", "chi2_result"))
        expect(chi2).to_be_attached()
        page.wait_for_selector(f"{_sid('crosstab', 'chi2_result')} .alert", timeout=15_000)
        chi2_text = chi2.inner_text()
        assert "Chi-Square" in chi2_text or "chi" in chi2_text.lower(), \
            f"Expected chi-square mention, got: {chi2_text[:200]}"

        # Cross-tab table should appear
        table = page.locator(_sid("crosstab", "crosstab_table"))
        expect(table).to_be_attached()
        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "crosstab", "pd.crosstab")


# ---------------------------------------------------------------------------
# VISUALIZE > DISTRIBUTE
# ---------------------------------------------------------------------------

class TestVisualizeDistribute:
    """Tests for the Visualize > Distribute module."""
    def test_t22_histogram(self, page: Page):
        """Select a column, run, verify chart appears."""
        _nav_to(page, "Visualize", "Distribute")
        _wait_stable(page, 2000)

        page.wait_for_selector(
            f"{_sid('distribute', 'col')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        _select_option(page, _sid("distribute", "col"), "total_bill")
        _wait_stable(page)
        _select_option(page, _sid("distribute", "chart_type"), "histogram")
        _wait_stable(page)

        _click_button(page, _sid("distribute", "run_btn"))
        _wait_stable(page, 5000)

        # Chart should render as an <img> (Shiny render.plot outputs an image)
        chart = page.locator(_sid("distribute", "chart"))
        expect(chart).to_be_attached()
        # Wait for an img element inside the chart output
        page.wait_for_selector(
            f"{_sid('distribute', 'chart')} img",
            state="visible", timeout=15_000,
        )
        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "distribute", "sns.histplot")


# ---------------------------------------------------------------------------
# VISUALIZE > RELATE
# ---------------------------------------------------------------------------

class TestVisualizeRelate:
    """Tests for the Visualize > Relate module."""
    def test_t23_scatter_plot(self, page: Page):
        """Select x and y, run, verify scatter plot appears."""
        _nav_to(page, "Visualize", "Relate")
        _wait_stable(page, 2000)

        page.wait_for_selector(
            f"{_sid('relate', 'x')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        _select_option(page, _sid("relate", "x"), "total_bill")
        _wait_stable(page)
        _select_option(page, _sid("relate", "y"), "tip")
        _wait_stable(page)

        _click_button(page, _sid("relate", "run_btn"))
        _wait_stable(page, 5000)

        chart = page.locator(_sid("relate", "chart"))
        expect(chart).to_be_attached()
        page.wait_for_selector(
            f"{_sid('relate', 'chart')} img",
            state="visible", timeout=15_000,
        )
        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "relate", "sns.scatterplot")


# ---------------------------------------------------------------------------
# VISUALIZE > COMPARE
# ---------------------------------------------------------------------------

class TestVisualizeCompare:
    """Tests for the Visualize > Compare module."""
    def test_t24_grouped_boxplot(self, page: Page):
        """Select category and numeric, run, verify grouped plot appears."""
        _nav_to(page, "Visualize", "Compare")
        _wait_stable(page, 2000)

        page.wait_for_selector(
            f"{_sid('compare', 'x_cat')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        _select_option(page, _sid("compare", "x_cat"), "day")
        _wait_stable(page)
        _select_option(page, _sid("compare", "y_num"), "total_bill")
        _wait_stable(page)

        _click_button(page, _sid("compare", "run_btn"))
        _wait_stable(page, 5000)

        chart = page.locator(_sid("compare", "chart"))
        expect(chart).to_be_attached()
        page.wait_for_selector(
            f"{_sid('compare', 'chart')} img",
            state="visible", timeout=15_000,
        )
        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "compare")


# ---------------------------------------------------------------------------
# VISUALIZE > CORRELATE
# ---------------------------------------------------------------------------

class TestVisualizeCorrelate:
    """Tests for the Visualize > Correlate module."""
    def test_t25_correlation_matrix(self, page: Page):
        """Select numeric columns, run, verify correlation matrix appears."""
        _nav_to(page, "Visualize", "Correlate")
        _wait_stable(page, 2000)

        page.wait_for_selector(
            f"{_sid('correlate', 'cols')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        _select_multiple(page, _sid("correlate", "cols"), ["total_bill", "tip", "size"])
        _wait_stable(page)

        _click_button(page, _sid("correlate", "run_btn"))
        _wait_stable(page, 5000)

        chart = page.locator(_sid("correlate", "chart"))
        expect(chart).to_be_attached()
        page.wait_for_selector(
            f"{_sid('correlate', 'chart')} img",
            state="visible", timeout=15_000,
        )
        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "correlate", "sns.heatmap")


# ---------------------------------------------------------------------------
# ANALYZE > MEANS
# ---------------------------------------------------------------------------

class TestAnalyzeMeans:
    """Tests for the Analyze > Means module."""
    def test_t26_two_sample_ttest(self, page: Page):
        """Run a two-sample t-test and verify result, group stats, no errors."""
        _nav_to(page, "Analyze", "Means")
        _wait_stable(page, 2000)

        page.wait_for_selector(
            f"{_sid('means', 'value_col')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        # Select two-sample test
        _select_option(page, _sid("means", "test_type"), "two_sample")
        _wait_stable(page, 2000)

        _select_option(page, _sid("means", "value_col"), "total_bill")
        _wait_stable(page, 1500)

        # Wait for group_col to appear (dynamic UI)
        page.wait_for_selector(_sid("means", "group_col"), state="attached", timeout=10_000)
        _select_option(page, _sid("means", "group_col"), "sex")
        _wait_stable(page)

        _click_button(page, _sid("means", "run_btn"))
        _wait_stable(page, 5000)

        # Check test result alert appears
        test_result = page.locator(_sid("means", "test_result"))
        expect(test_result).to_be_attached()
        page.wait_for_selector(f"{_sid('means', 'test_result')} .alert", timeout=15_000)
        result_text = test_result.inner_text()
        assert "t-test" in result_text.lower() or "t test" in result_text.lower() or \
               "statistic" in result_text.lower() or "p-value" in result_text.lower(), \
            f"Expected test name or statistic in result, got: {result_text[:300]}"

        # Check group stats table renders
        group_stats = page.locator(_sid("means", "group_stats"))
        expect(group_stats).to_be_attached()

        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "means", "ttest_ind")
    def test_t27_one_way_anova(self, page: Page):
        """Run a one-way ANOVA and verify result renders."""
        _select_option(page, _sid("means", "test_type"), "anova")
        _wait_stable(page, 2000)

        _select_option(page, _sid("means", "value_col"), "total_bill")
        _wait_stable(page, 1500)

        page.wait_for_selector(_sid("means", "group_col"), state="attached", timeout=10_000)
        _select_option(page, _sid("means", "group_col"), "day")
        _wait_stable(page)

        _click_button(page, _sid("means", "run_btn"))
        _wait_stable(page, 5000)

        test_result = page.locator(_sid("means", "test_result"))
        expect(test_result).to_be_attached()
        page.wait_for_selector(f"{_sid('means', 'test_result')} .alert", timeout=15_000)
        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "means", "f_oneway")


# ---------------------------------------------------------------------------
# ANALYZE > PROPORTIONS
# ---------------------------------------------------------------------------

class TestAnalyzeProportions:
    """Tests for the Analyze > Proportions module."""
    def test_t28_chi_square_test(self, page: Page):
        """Run proportions test and verify result + observed/expected tables."""
        _nav_to(page, "Analyze", "Proportions")
        _wait_stable(page, 2000)

        # row_var/col_var only exist for the independence test; the module
        # defaults to one_prop, which renders op_var instead.  Without this the
        # test waited for a control that never renders and never ran a chi-square.
        _select_option(page, _sid("proportions", "test_type"), "independence")
        _wait_stable(page, 2000)

        page.wait_for_selector(
            f"{_sid('proportions', 'row_var')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        _select_option(page, _sid("proportions", "row_var"), "sex")
        _wait_stable(page)
        _select_option(page, _sid("proportions", "col_var"), "smoker")
        _wait_stable(page)

        _click_button(page, _sid("proportions", "run_btn"))
        _wait_stable(page, 5000)

        # Test result
        test_result = page.locator(_sid("proportions", "test_result"))
        expect(test_result).to_be_attached()
        page.wait_for_selector(f"{_sid('proportions', 'test_result')} .alert", timeout=15_000)

        # Observed table
        observed = page.locator(_sid("proportions", "observed"))
        expect(observed).to_be_attached()

        # Expected table
        expected = page.locator(_sid("proportions", "expected"))
        expect(expected).to_be_attached()

        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "proportions", "crosstab")


# ---------------------------------------------------------------------------
# ANALYZE > CORRELATION
# ---------------------------------------------------------------------------

class TestAnalyzeCorrelation:
    """Tests for the Analyze > Correlation module."""
    def test_t29_correlation_test(self, page: Page):
        """Run correlation test and verify result with r, p, CI."""
        _nav_to(page, "Analyze", "Correlation")
        _wait_stable(page, 2000)

        page.wait_for_selector(
            f"{_sid('correlation', 'x')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        _select_option(page, _sid("correlation", "x"), "total_bill")
        _wait_stable(page)
        _select_option(page, _sid("correlation", "y"), "tip")
        _wait_stable(page)

        _click_button(page, _sid("correlation", "run_btn"))
        _wait_stable(page, 5000)

        test_result = page.locator(_sid("correlation", "test_result"))
        expect(test_result).to_be_attached()
        page.wait_for_selector(f"{_sid('correlation', 'test_result')} .alert", timeout=15_000)

        result_text = test_result.inner_text()
        assert "correlation" in result_text.lower() or "r =" in result_text.lower(), \
            f"Expected correlation info in result, got: {result_text[:300]}"
        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "correlation", "stats.")


# ---------------------------------------------------------------------------
# MODEL > REGRESSION
# ---------------------------------------------------------------------------

class TestModelRegression:
    """Tests for the Model > Regression module."""
    def test_t30_linear_regression(self, page: Page):
        """Run linear regression and verify coefficients + VIF tables."""
        _nav_to(page, "Model", "Regression")
        _wait_stable(page, 2000)

        page.wait_for_selector(
            f"{_sid('regression', 'target')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        _select_option(page, _sid("regression", "target"), "tip")
        _wait_stable(page)
        _select_multiple(page, _sid("regression", "features"), ["total_bill", "size"])
        _wait_stable(page)

        _click_button(page, _sid("regression", "run_btn"))
        _wait_stable(page, 6000)

        # Model summary
        summary = page.locator(_sid("regression", "model_summary"))
        expect(summary).to_be_attached()
        page.wait_for_selector(f"{_sid('regression', 'model_summary')} .alert", timeout=15_000)
        summary_text = summary.inner_text()
        assert "R" in summary_text or "regression" in summary_text.lower(), \
            f"Expected regression summary, got: {summary_text[:300]}"

        # Coefficients table
        coef = page.locator(_sid("regression", "coef_table"))
        expect(coef).to_be_attached()

        # VIF table
        vif = page.locator(_sid("regression", "vif_table"))
        expect(vif).to_be_attached()

        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "regression", "LinearRegression")


# ---------------------------------------------------------------------------
# MODEL > CLASSIFY
# ---------------------------------------------------------------------------

class TestModelClassify:
    """Tests for the Model > Classify module."""
    def test_t31_logistic_regression(self, page: Page):
        """Run logistic regression and verify accuracy is displayed."""
        _nav_to(page, "Model", "Classify")
        _wait_stable(page, 2000)

        page.wait_for_selector(
            f"{_sid('classify', 'target')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        # For tips, use 'sex' as target (categorical binary) and numeric features
        _select_option(page, _sid("classify", "target"), "sex")
        _wait_stable(page)
        _select_multiple(page, _sid("classify", "features"), ["total_bill", "tip", "size"])
        _wait_stable(page)

        _click_button(page, _sid("classify", "run_btn"))
        _wait_stable(page, 8000)

        # Model summary should show accuracy
        summary = page.locator(_sid("classify", "model_summary"))
        expect(summary).to_be_attached()
        page.wait_for_selector(f"{_sid('classify', 'model_summary')} .alert", timeout=20_000)
        summary_text = summary.inner_text()
        assert "accuracy" in summary_text.lower() or "Logistic" in summary_text or "Train" in summary_text, \
            f"Expected accuracy info, got: {summary_text[:300]}"

        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "classify", "LogisticRegression")


# ---------------------------------------------------------------------------
# MODEL > CLUSTER
# ---------------------------------------------------------------------------

class TestModelCluster:
    """Tests for the Model > Cluster module."""
    def test_t32_kmeans_cluster(self, page: Page):
        """Run K-means clustering and verify cluster plot/summary appears."""
        _nav_to(page, "Model", "Cluster")
        _wait_stable(page, 2000)

        page.wait_for_selector(
            f"{_sid('cluster', 'features')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        _select_multiple(page, _sid("cluster", "features"), ["total_bill", "tip"])
        _wait_stable(page)

        _click_button(page, _sid("cluster", "run_btn"))
        _wait_stable(page, 8000)

        # Cluster summary
        summary = page.locator(_sid("cluster", "cluster_summary"))
        expect(summary).to_be_attached()
        page.wait_for_selector(f"{_sid('cluster', 'cluster_summary')} .alert", timeout=20_000)

        # The scatter plot is tier 2 now: attached while closed, so requiring
        # the image means opening the section first.
        _open_section(page, "Cluster scatter plot")
        scatter = page.locator(f"{_sid('cluster', 'scatter_plot')} img")
        expect(scatter).to_be_visible(timeout=20_000)

        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "cluster", "KMeans")


# ---------------------------------------------------------------------------
# MODEL > REDUCE
# ---------------------------------------------------------------------------

class TestModelReduce:
    """Tests for the Model > Reduce (PCA) module."""
    def test_t33_pca_analysis(self, page: Page):
        """Run PCA and verify scree/biplot and summary appear."""
        _nav_to(page, "Model", "Reduce")
        _wait_stable(page, 2000)

        page.wait_for_selector(
            f"{_sid('reduce', 'features')} option:not([value=''])",
            state="attached", timeout=10_000,
        )

        _select_multiple(page, _sid("reduce", "features"), ["total_bill", "tip", "size"])
        _wait_stable(page)

        _click_button(page, _sid("reduce", "run_btn"))
        _wait_stable(page, 8000)

        # PCA summary
        summary = page.locator(_sid("reduce", "pca_summary"))
        expect(summary).to_be_attached()
        page.wait_for_selector(f"{_sid('reduce', 'pca_summary')} .alert", timeout=20_000)
        summary_text = summary.inner_text()
        assert "PCA" in summary_text or "variance" in summary_text.lower(), \
            f"Expected PCA summary, got: {summary_text[:300]}"

        # Scree plot
        _open_section(page, "How many components?")
        scree = page.locator(f"{_sid('reduce', 'scree_plot')} img")
        expect(scree).to_be_visible(timeout=20_000)

        _assert_no_shiny_errors(page)

        # Second oracle: the operation must also emit runnable code.
        _assert_code(page, "reduce", "PCA")


# ---------------------------------------------------------------------------
# CROSS-CUTTING: DECIMALS CHANGE
# ---------------------------------------------------------------------------

class TestCrossCutting:
    """Cross-cutting tests: decimals selector, global error checks."""
    def test_t34_change_decimals(self, page: Page):
        """Change the decimals dropdown on View tab from 4 to 2 and verify page still works."""
        _nav_to(page, "Data", "View")
        _wait_stable(page, 2000)

        # Decimals is now per-module, inside the View tab
        dec_id = _nested_sid("view", "dec", "decimals")
        _select_option(page, dec_id, "2")
        _wait_stable(page, 2000)

        # Table should still render
        table = page.locator(_sid("view", "view_table"))
        expect(table).to_be_attached()
        _assert_no_shiny_errors(page)

        # Restore to 4
        _select_option(page, dec_id, "4")
        _wait_stable(page, 1000)

    def test_t35_all_tabs_open_without_errors(self, page: Page):
        """Sweep every navbar tab and sub-tab discovered from the live DOM.

        This replaces the five hand-listed loops it grew out of.  Those lists
        drifted: Simulate and Predict shipped without ever being added, so both
        modules were silently exempt from the smoke sweep.  EXPECTED_TABS below
        is a floor, not a whitelist -- it fails if a known tab disappears, while
        a newly added tab is swept with no test change at all.
        """
        expected_tabs = {
            "Data": {"Load", "Profile", "View", "Transform", "Combine", "Export"},
            "Explore": {"Group By / Summarize", "Pivot", "Cross-tab", "Simulate"},
            "Visualize": {"Distribute", "Relate", "Compare", "Correlate", "Timeline"},
            "Analyze": {"Means", "Proportions", "Correlation"},
            "Model": {"Regression", "Classify", "Evaluate", "Predict", "Cluster", "Reduce"},
            "Report": {"Report Builder", "Notebook", "Procedure"},
        }

        discovered = _discover_nav(page)

        for top, expected_subs in expected_tabs.items():
            assert top in discovered, (
                f"Top-level tab '{top}' not found. Discovered: {sorted(discovered)}"
            )
            missing = expected_subs - set(discovered[top])
            assert not missing, (
                f"'{top}' is missing sub-tab(s) {sorted(missing)}. "
                f"Found: {sorted(discovered[top])}"
            )

        swept = []
        for top, subs in discovered.items():
            for sub in subs or [None]:
                _nav_to(page, top, sub) if sub else _nav_to(page, top)
                _wait_stable(page, 1500)
                _assert_no_shiny_errors(page)
                swept.append(f"{top} > {sub}" if sub else top)

        assert len(swept) >= 25, f"Expected to sweep >=25 tabs, swept {len(swept)}: {swept}"

    def test_t40_dataset_selector_persists(self, page: Page):
        """The active dataset remains 'tips' after navigating across all tabs."""
        ds_sel = page.locator(_sid("ds", "dataset"))
        val = ds_sel.input_value()
        assert val == "tips", f"Expected 'tips' selected, got '{val}'"
