"""Every Transform action, driven in the app -- sweep cases A20-A29.

Transform is the panel with the most actions and the most ways to reach them:
the sidebar rebuilds itself for each one, so the controls a given action needs
are created by a dynamic output rather than sitting in the page. That is
exactly the arrangement where a library test proves nothing -- `add_column_binned`
was correct in isolation while the app it lives in stopped responding whenever
anyone used it.

So this walks the Action dropdown from top to bottom, exercises each entry with
values that should work, and after every one asks the server for something new.
A wedged Shiny session keeps its UI on screen; the only way to tell is to ask.
"""

from __future__ import annotations

import time

import pytest
from playwright.sync_api import Page, expect


def _sid(module: str, widget: str) -> str:
    return f"#{module}-{widget}"


def _wait_stable(page: Page, ms: int = 1500) -> None:
    time.sleep(ms / 1000)


def _nav_to(page: Page, *tab_labels: str, timeout: float = 10_000) -> None:
    for label in tab_labels:
        link = page.locator(f"a.nav-link:has-text('{label}')")
        link.first.wait_for(state="visible", timeout=timeout)
        link.first.click()
        time.sleep(0.4)


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


def _fill_if_present(page: Page, selector: str, value: str) -> bool:
    box = page.locator(selector)
    if not box.count():
        return False
    box.first.fill(value)
    time.sleep(0.2)
    return True


def _session_answers(page: Page) -> None:
    """A wedged session leaves every element attached and answers nothing."""
    _nav_to(page, "Data", "View")
    _wait_stable(page, 2000)
    grid = page.locator(_sid("view", "view_table"))
    expect(grid).to_be_visible(timeout=15_000)
    assert grid.inner_text().strip(), "the session stopped answering"
    _nav_to(page, "Data", "Transform")
    _wait_stable(page, 1200)


#: Action value -> the fields it needs, beyond Column. Values chosen to work
#: against the tips dataset.
ACTION_INPUTS: dict[str, dict[str, str]] = {
    "fill_missing": {},
    "drop_missing": {},
    "rename_column": {"new_col_name": "renamed_col"},
    "drop_columns": {},
    "convert_dtype": {},
    "drop_duplicates": {},
    "dummy_encode": {},
    "ordinal_encode": {},
    "add_arithmetic": {"new_col_name": "arith", "expr": "total_bill * 2"},
    "add_conditional": {"new_col_name": "cond", "condition": "total_bill > 20",
                        "true_val": "1", "false_val": "0"},
    "add_binned": {"new_col_name": "banded", "n_bins": "4"},
    "add_log": {"new_col_name": "logged"},
    "add_zscore": {"new_col_name": "zscored"},
    "add_rank": {"new_col_name": "ranked"},
    "str_lower": {},
    "str_upper": {},
    "str_strip": {},
    "str_replace": {"find_text": "Male", "replace_text": "M"},
    "str_extract": {"new_col_name": "extracted", "pattern": r"^(\w+)"},
}

#: Actions that need a text column rather than a numeric one.
TEXT_ACTIONS = {"str_lower", "str_upper", "str_strip", "str_replace", "str_extract",
                "dummy_encode", "ordinal_encode"}


def _load_tips(page: Page) -> None:
    """Start every case from the same frame.

    Apply commits to the workbench and there is no undo, so one case renaming a
    column or dropping one leaves the next case selecting a column that no
    longer exists. That is a property of the tool worth knowing -- the testing
    plan calls it out as the thing that dictates test *ordering* -- and here it
    means reloading rather than sharing one dataset across twenty actions.
    """
    _nav_to(page, "Data", "Load")
    _wait_stable(page)
    page.wait_for_selector(_sid("load", "bundled_name"), state="attached", timeout=10_000)
    _select_option(page, _sid("load", "bundled_name"), "tips")
    _wait_stable(page)
    _click_button(page, _sid("load", "load_btn"))
    _wait_stable(page, 3000)


@pytest.fixture
def loaded(page: Page):
    _load_tips(page)
    return page


def test_the_action_list_matches_what_this_file_exercises(loaded, page: Page):
    """Fail loudly when an action is added and nothing here covers it."""
    _nav_to(page, "Data", "Transform")
    _wait_stable(page, 1500)
    options = page.locator(f"{_sid('transform', 'action')} option")
    offered = {options.nth(i).get_attribute("value") for i in range(options.count())}
    missing = offered - set(ACTION_INPUTS)
    assert not missing, f"Transform offers actions this sweep does not exercise: {missing}"


@pytest.mark.parametrize("action", list(ACTION_INPUTS))
def test_each_transform_action_runs_and_leaves_the_session_answering(
    loaded, page: Page, action: str
):
    _nav_to(page, "Data", "Transform")
    _wait_stable(page, 1200)
    _select_option(page, _sid("transform", "action"), action)
    _wait_stable(page, 1800)

    column = "sex" if action in TEXT_ACTIONS else "total_bill"
    if page.locator(_sid("transform", "col")).count():
        _select_option(page, _sid("transform", "col"), column)
        _wait_stable(page, 600)

    for field, value in ACTION_INPUTS[action].items():
        _fill_if_present(page, _sid("transform", field), value)
    _wait_stable(page, 600)

    _click_button(page, _sid("transform", "apply_btn"))
    _wait_stable(page, 3000)

    preview = page.locator(_sid("transform", "preview"))
    expect(preview).to_be_visible(timeout=15_000)
    shown = preview.inner_text()
    assert shown.strip(), f"{action} left the preview empty"

    errors = page.locator(".shiny-output-error:visible")
    assert not errors.count(), (
        f"{action} rendered a Shiny error: {errors.first.inner_text()[:200]}"
    )

    # "It rendered" is not an oracle here, and this file learned that the hard
    # way: with String: Extract broken, the action failed into a five-second
    # toast, the *previous* preview stayed on screen, and the assertions above
    # all passed. Require evidence the transform actually happened.
    expected = ACTION_INPUTS[action].get("new_col_name")
    if expected:
        assert expected.lower() in shown.lower(), (
            f"{action} reported no error but produced no {expected!r} column. "
            f"Check for a notification: a failure that only toasts looks "
            f"exactly like this. Preview: {shown[:200]}"
        )

    _session_answers(page)


def test_string_extract_produces_a_column_not_a_traceback(loaded, page: Page):
    """A27: the pattern in the sweep plan has a capture group, as most do."""
    _nav_to(page, "Data", "Transform")
    _wait_stable(page, 1200)
    _select_option(page, _sid("transform", "action"), "str_extract")
    _wait_stable(page, 1800)
    _select_option(page, _sid("transform", "col"), "day")
    _fill_if_present(page, _sid("transform", "new_col_name"), "day_start")
    _fill_if_present(page, _sid("transform", "pattern"), r"^(\w)")
    _wait_stable(page, 600)
    _click_button(page, _sid("transform", "apply_btn"))
    _wait_stable(page, 3000)

    text = page.locator(_sid("transform", "preview")).inner_text().lower()
    assert "day_start" in text, f"extract produced no column: {text[:300]}"
    assert "dataframe with multiple columns" not in text
    _session_answers(page)
