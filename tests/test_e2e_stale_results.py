"""A failed run must not leave the previous answer on screen -- issues 7 and 11.

The reported sequence: run a two-sample t-test that works, change the grouping
variable to one with twelve levels, run again. The toast said "Expected 2
groups, got 12" and disappeared after five seconds, while the panel went on
showing the *previous* test's result beside the inputs that had just failed.

Only the app can show this. The message and the stale result are both renders,
and the interesting moment is the one after the toast has gone -- which is why
this test waits it out before looking.
"""

from __future__ import annotations

import time

from playwright.sync_api import Page, expect


def _sid(module: str, widget: str) -> str:
    return f"#{module}-{widget}"


def _status(module: str) -> str:
    """The status area is a nested module, so its id carries both namespaces."""
    return f"#{module}-status-panel_status"


def _wait_stable(page: Page, ms: int = 1500) -> None:
    time.sleep(ms / 1000)


def _nav_to(page: Page, *labels: str, timeout: float = 10_000) -> None:
    for label in labels:
        link = page.locator(f"a.nav-link:has-text('{label}')")
        link.first.wait_for(state="visible", timeout=timeout)
        link.first.click()
        time.sleep(0.5)


def _select(page: Page, selector: str, value: str) -> None:
    loc = page.locator(selector)
    loc.wait_for(state="attached", timeout=15_000)
    loc.select_option(value, timeout=5000)
    time.sleep(0.6)


def _result_text(page: Page) -> str:
    return page.locator(_sid("means", "test_result")).inner_text()


class TestAFailedRunClearsTheResult:

    def test_t01_a_test_that_works(self, page: Page):
        _nav_to(page, "Data", "Load")
        _wait_stable(page)
        page.wait_for_selector(_sid("load", "bundled_name"), state="attached", timeout=15_000)
        _select(page, _sid("load", "bundled_name"), "titanic")
        page.locator(_sid("load", "load_btn")).click()
        _wait_stable(page, 4000)

        _nav_to(page, "Analyze", "Means")
        _wait_stable(page, 2000)
        _select(page, _sid("means", "test_type"), "two_sample")
        _wait_stable(page, 1200)
        page.wait_for_selector(
            f"{_sid('means', 'value_col')} option:not([value=''])",
            state="attached", timeout=15_000,
        )
        _select(page, _sid("means", "value_col"), "Age")
        _select(page, _sid("means", "group_col"), "Sex")
        page.locator(_sid("means", "run_btn")).click()
        _wait_stable(page, 4000)

        text = _result_text(page)
        assert "Age" in text or "t(" in text, f"the first test did not run: {text!r}"

    def test_t02_a_failing_run_does_not_leave_the_old_answer(self, page: Page):
        """Twelve levels is not two, so the t-test cannot run."""
        before = _result_text(page)
        assert before.strip()

        _select(page, _sid("means", "group_col"), "Embarked")
        page.locator(_sid("means", "run_btn")).click()
        _wait_stable(page, 4000)

        after = _result_text(page)
        assert after.strip() != before.strip(), (
            "the previous test's result is still on screen beside inputs that "
            f"failed: {after[:160]!r}"
        )

    def test_t03_and_says_why_where_the_result_was(self, page: Page):
        status = page.locator(_status("means"))
        expect(status).to_be_visible(timeout=15_000)
        text = status.inner_text()
        assert "groups" in text.lower(), f"the panel does not say what went wrong: {text!r}"

    def test_t04_the_message_outlives_the_toast(self, page: Page):
        """A five-second toast cannot be re-read, and cannot be screenshotted
        for an assignment."""
        time.sleep(11)
        page.locator(".shiny-notification").first.wait_for(
            state="detached", timeout=20_000
        )
        status = page.locator(_status("means"))
        expect(status).to_be_visible()
        assert "groups" in status.inner_text().lower()

    def test_t05_a_later_success_clears_the_message(self, page: Page):
        _select(page, _sid("means", "group_col"), "Sex")
        page.locator(_sid("means", "run_btn")).click()
        _wait_stable(page, 4000)

        assert not page.locator(f"{_status('means')} .alert-danger").count(), (
            "the failure message survived a successful run"
        )
        assert _result_text(page).strip()
