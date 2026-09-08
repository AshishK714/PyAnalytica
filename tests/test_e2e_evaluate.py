"""Model > Evaluate in the browser -- the panel the sweep never reached.

The Classification Threshold slider was rendered and its value never read, so
moving it from 0.5 to 0.9 left the confusion matrix and every metric identical.
`tests/test_ui/test_no_dead_controls.py` catches that statically now, but only
the app can show the other half: the slider is created by a dynamic output that
appears *after* a binary model has been evaluated, so whether it is wired at all
depends on Shiny's render order rather than on the code reading cleanly.

Model > Evaluate had no browser coverage of any kind before this file.
"""

from __future__ import annotations

import re
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


def _select_multiple(page: Page, selector: str, values: list[str]) -> None:
    page.evaluate(
        """([sel, vals]) => {
            const el = document.querySelector(sel);
            if (!el) return;
            Array.from(el.options).forEach(o => o.selected = vals.includes(o.value));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        }""",
        [selector, values],
    )
    time.sleep(0.6)


def _click_button(page: Page, selector: str, *, timeout: float = 10_000) -> None:
    btn = page.locator(selector)
    btn.wait_for(state="visible", timeout=timeout)
    btn.scroll_into_view_if_needed()
    btn.click()


def _set_slider(page: Page, selector: str, value: float) -> None:
    """Move an ionRangeSlider, which ignores a plain .value assignment."""
    page.evaluate(
        """([sel, val]) => {
            const el = document.querySelector(sel);
            const inst = window.jQuery && window.jQuery(el).data('ionRangeSlider');
            if (inst) { inst.update({from: val}); }
            else { el.value = val; }
            window.jQuery(el).trigger('change');
        }""",
        [selector, value],
    )
    time.sleep(0.8)


def _metrics(page: Page) -> str:
    block = page.locator(f"{_sid('evaluate', 'metrics_summary')} .alert")
    block.wait_for(state="visible", timeout=20_000)
    return block.inner_text()


def _numbers(text: str) -> list[float]:
    return [float(v) for v in re.findall(r"\d\.\d{4}", text)]


class TestEvaluateThreshold:

    def test_t01_fit_a_binary_model(self, page: Page):
        _nav_to(page, "Data", "Load")
        _wait_stable(page, 1500)
        page.wait_for_selector(_sid("load", "bundled_name"), state="attached", timeout=10_000)
        _select_option(page, _sid("load", "bundled_name"), "titanic")
        _wait_stable(page)
        _click_button(page, _sid("load", "load_btn"))
        _wait_stable(page, 4000)

        _nav_to(page, "Model", "Classify")
        _wait_stable(page, 2000)
        page.wait_for_selector(
            f"{_sid('classify', 'target')} option:not([value=''])",
            state="attached", timeout=10_000,
        )
        _select_option(page, _sid("classify", "target"), "Survived")
        _wait_stable(page)
        _select_multiple(page, _sid("classify", "features"), ["Pclass", "Age", "Fare"])
        _wait_stable(page)
        _click_button(page, _sid("classify", "run_btn"))
        _wait_stable(page, 8000)

        summary = page.locator(_sid("classify", "model_summary"))
        expect(summary).to_be_attached()
        assert "ccuracy" in summary.inner_text()

    def test_t02_evaluate_reports_metrics(self, page: Page):
        _nav_to(page, "Model", "Evaluate")
        _wait_stable(page, 2000)
        _click_button(page, _sid("evaluate", "run_btn"))
        _wait_stable(page, 5000)

        text = _metrics(page)
        assert "Accuracy" in text and "Recall" in text
        assert len(_numbers(text)) >= 4

    def test_t03_the_metrics_say_which_threshold_produced_them(self, page: Page):
        text = _metrics(page)
        assert "0.50" in text, f"the threshold in force is not stated: {text!r}"

    def test_t04_the_metrics_say_what_the_baseline_is(self, page: Page):
        """88.9% accuracy means nothing next to a 88.7% majority class."""
        text = _metrics(page)
        assert "most common class" in text, (
            f"accuracy is reported with nothing to compare it against: {text!r}"
        )

    def test_t05_moving_the_threshold_changes_the_answer(self, page: Page):
        before = _metrics(page)

        slider = page.locator(_sid("evaluate", "threshold"))
        expect(slider).to_be_attached(timeout=10_000)
        _set_slider(page, _sid("evaluate", "threshold"), 0.9)
        _click_button(page, _sid("evaluate", "run_btn"))
        _wait_stable(page, 5000)

        after = _metrics(page)
        assert after != before, (
            "moving the Classification Threshold from 0.5 to 0.9 left every "
            f"metric identical: {after!r}"
        )
        assert "0.90" in after

    def test_t06_a_higher_threshold_trades_recall_for_precision(self, page: Page):
        """The direction is the lesson, so assert it rather than just 'changed'."""
        _set_slider(page, _sid("evaluate", "threshold"), 0.5)
        _click_button(page, _sid("evaluate", "run_btn"))
        _wait_stable(page, 5000)
        at_half = _metrics(page)

        _set_slider(page, _sid("evaluate", "threshold"), 0.9)
        _click_button(page, _sid("evaluate", "run_btn"))
        _wait_stable(page, 5000)
        at_nine = _metrics(page)

        def recall(text: str) -> float:
            return float(re.search(r"Recall: (\d\.\d{4})", text).group(1))

        assert recall(at_nine) < recall(at_half), (
            f"raising the threshold should call fewer positives and lower recall; "
            f"got {recall(at_half)} at 0.5 and {recall(at_nine)} at 0.9"
        )

    def test_t12_no_regression_sections_are_offered_for_a_classifier(self, page: Page):
        """And none of the classifier's for a regression, checked in t11's class.

        A section that opens onto nothing is the same fault as a heading over an
        empty table, one click further in.
        """
        # The classifier fitted in t01 is still the selection here; it is saved
        # under a generated name, so take whatever is chosen rather than
        # guessing one.
        _nav_to(page, "Model", "Evaluate")
        _wait_stable(page, 2000)
        _click_button(page, _sid("evaluate", "run_btn"))
        _wait_stable(page, 6000)

        body = page.locator("body").inner_text()
        assert "ROC curve" in body
        assert "Predicted vs actual" not in body
        assert "Residuals" not in body


class TestEvaluatingARegression:
    """Model > Evaluate used to hand a regression to sklearn's classification
    metrics, which answered "continuous is not supported" -- a message naming a
    scikit-learn target type, under a "Confusion Matrix" heading, with the
    metrics area blank.

    Refusing those models would have been the smaller fix and the wrong one:
    checking a regression against held-out rows is a reasonable thing to want,
    and this is where a student looks for it.
    """

    def test_t07_fit_a_regression(self, page: Page):
        _nav_to(page, "Model", "Regression")
        _wait_stable(page, 2000)
        page.wait_for_selector(
            f"{_sid('regression', 'target')} option:not([value=''])",
            state="attached", timeout=15_000,
        )
        _select_option(page, _sid("regression", "target"), "Age")
        _select_multiple(page, _sid("regression", "features"), ["Fare", "Pclass"])
        page.locator(_sid("regression", "test_size")).evaluate(
            """el => { const i = window.jQuery(el).data('ionRangeSlider');
                       if (i) i.update({from: 0.3}); window.jQuery(el).trigger('change'); }"""
        )
        _wait_stable(page, 1000)
        page.locator(_sid("regression", "model_name")).fill("age_model")
        _wait_stable(page)
        _click_button(page, _sid("regression", "run_btn"))
        _wait_stable(page, 7000)

    def test_t08_evaluating_it_reports_regression_measures(self, page: Page):
        _nav_to(page, "Model", "Evaluate")
        _wait_stable(page, 2500)
        _select_option(page, _sid("evaluate", "model_name"), "age_model")
        _click_button(page, _sid("evaluate", "run_btn"))
        _wait_stable(page, 6000)

        text = _metrics(page)
        assert "R" in text and "rows" in text, f"no regression summary: {text!r}"
        assert "continuous is not supported" not in page.locator("body").inner_text()

    def test_t09_the_measures_are_the_ones_that_mean_something(self, page: Page):
        table = page.locator(_sid("evaluate", "results_table"))
        expect(table).to_be_visible(timeout=20_000)
        body = table.inner_text().upper()
        for measure in ("RMSE", "MAE", "ROWS"):
            assert measure in body, f"{measure} missing from {body[:200]!r}"

    def test_t10_no_confusion_matrix_is_offered_for_a_regression(self, page: Page):
        """The heading is dynamic now, so it does not stand over nothing."""
        assert "Confusion Matrix" not in page.locator("body").inner_text()

    def test_t11_the_regression_plots_are_offered_not_forced(self, page: Page):
        body = page.locator("body").inner_text()
        assert "Predicted vs actual" in body
        assert page.locator(f"{_sid('evaluate', 'pred_vs_actual')} img").count() == 0

        page.locator(".accordion-button:has-text('Predicted vs actual')").first.click()
        _wait_stable(page, 4000)
        expect(page.locator(f"{_sid('evaluate', 'pred_vs_actual')} img")).to_be_visible(
            timeout=20_000
        )
