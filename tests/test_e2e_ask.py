"""Browser tests for the question-shaped panels: Describe > One Variable and
Relate > Two Variables.

The library tests prove the dispatch; these prove a student sees the answer,
that opening a section draws what it promised, and that "treat as" changes
the reading.
"""

from __future__ import annotations

import time

from tests.test_e2e import (
    _assert_no_shiny_errors,
    _click_button,
    _nav_to,
    _select_option,
    _sid,
    _wait_stable,
)
from tests.test_e2e_datasets import _load_bundled

# `app_url` and `page` come from tests/conftest.py.

MOD2 = "two_variables"
MOD1 = "one_variable"


def _open_section_of(page, module: str, section_id: str) -> None:
    """Open one panel's section by its accordion id, not its title: two panels
    share the title "Another picture", and the first match may be in a hidden
    tab pane."""
    button = page.locator(f"#{module}-{section_id} .accordion-button")
    button.first.wait_for(state="visible", timeout=10_000)
    if button.first.get_attribute("aria-expanded") != "true":
        button.first.click()
        time.sleep(3)


def _close_section_of(page, module: str, section_id: str) -> None:
    button = page.locator(f"#{module}-{section_id} .accordion-button")
    button.first.wait_for(state="visible", timeout=10_000)
    if button.first.get_attribute("aria-expanded") == "true":
        button.first.click()
        time.sleep(1.5)


def _headings(page) -> list[str]:
    """Report Builder's code-cell headings, which live in text boxes."""
    return page.eval_on_selector_all(
        "#report_builder-cell_editor input[type=text]", "els => els.map(e => e.value)"
    )


def _answer(page, module: str) -> str:
    return page.locator(_sid(module, "answer")).inner_text()


class TestTwoVariables:

    def test_before_a_run_the_panel_says_what_it_will_do(self, page):
        _load_bundled(page, "tips")
        _nav_to(page, "Relate", "Two Variables")
        _wait_stable(page, 1500)
        text = _answer(page, MOD2)
        assert "How does Y relate to X?" in text
        assert "t-test or ANOVA" in text

    def test_number_by_category_answers_with_groups_then_the_test(self, page):
        _nav_to(page, "Relate", "Two Variables")
        _select_option(page, _sid(MOD2, "y"), "tip")
        _select_option(page, _sid(MOD2, "x"), "day")
        _click_button(page, _sid(MOD2, "run_btn"))
        _wait_stable(page, 4000)

        text = _answer(page, MOD2)
        assert "Mean tip is highest for day" in text, text
        assert page.locator(_sid(MOD2, "answer_plot") + " img").count() == 1

        _open_section_of(page, MOD2, "test_open")
        test_text = page.locator(_sid(MOD2, "test_text")).inner_text()
        assert "ANOVA" in test_text, test_text
        _assert_no_shiny_errors(page)

    def test_opening_the_picture_section_draws_it(self, page):
        _open_section_of(page, MOD2, "picture_open")
        _wait_stable(page, 3000)
        assert page.locator(_sid(MOD2, "picture_plot") + " img").count() == 1
        _assert_no_shiny_errors(page)

    def test_small_integer_x_is_read_as_categories_until_told_otherwise(self, page):
        _select_option(page, _sid(MOD2, "y"), "tip")
        _select_option(page, _sid(MOD2, "x"), "size")
        _select_option(page, _sid(MOD2, "treat_x"), "auto")
        _click_button(page, _sid(MOD2, "run_btn"))
        _wait_stable(page, 4000)
        text = _answer(page, MOD2)
        assert "read as categories" in text, text

        _select_option(page, _sid(MOD2, "treat_x"), "number")
        _click_button(page, _sid(MOD2, "run_btn"))
        _wait_stable(page, 4000)
        text = _answer(page, MOD2)
        assert "r = " in text, text
        assert "as you asked" in text

    def test_colour_by_splits_the_answer_and_adds_it_to_the_report(self, page):
        _select_option(page, _sid(MOD2, "y"), "total_bill")
        _select_option(page, _sid(MOD2, "x"), "day")
        _select_option(page, _sid(MOD2, "treat_x"), "auto")
        _select_option(page, _sid(MOD2, "color_by"), "smoker")
        _click_button(page, _sid(MOD2, "run_btn"))
        _wait_stable(page, 4000)
        text = _answer(page, MOD2)
        assert "split by smoker" in text, text
        assert "day / smoker = " in text, text

        # Add to Report sits beside Show Code on every panel now. With every
        # section closed it sends the answer alone.
        for section in ("picture_open", "test_open", "model_open"):
            _close_section_of(page, MOD2, section)
        page.evaluate(
            "() => document.querySelectorAll('.shiny-notification').forEach(n => n.remove())"
        )
        _click_button(page, _sid(MOD2, "code-add_to_report"))
        _wait_stable(page, 1500)
        note = page.locator(".shiny-notification").first.inner_text()
        assert "to Report Builder" in note, note
        assert "Added 1 cell" in note, note
        _select_option(page, _sid(MOD2, "color_by"), "")

    def test_same_column_twice_is_refused_in_the_panel(self, page):
        _select_option(page, _sid(MOD2, "y"), "tip")
        _select_option(page, _sid(MOD2, "x"), "tip")
        _click_button(page, _sid(MOD2, "run_btn"))
        _wait_stable(page, 2500)
        status = page.locator(_sid(MOD2, "status-panel_status")).inner_text()
        assert "two different columns" in status, status
        # The stale answer went with it.
        assert "How does Y relate to X?" in _answer(page, MOD2)


class TestChartsCanBeDownloaded:
    """Charts go into reports written outside the app; right-click > Save image
    as was the only way out, and most learners did not know it existed."""

    def test_every_chart_on_screen_offers_a_png_download(self, page, tmp_path_factory):
        _load_bundled(page, "tips")
        _nav_to(page, "Relate", "Two Variables")
        _wait_stable(page, 1500)
        _select_option(page, _sid(MOD2, "y"), "tip")
        _select_option(page, _sid(MOD2, "x"), "day")
        _select_option(page, _sid(MOD2, "color_by"), "")
        _click_button(page, _sid(MOD2, "run_btn"))
        _wait_stable(page, 4000)

        button = page.locator(f"#{MOD2}-answer_plot .pa-chart-download")
        assert button.count() == 1
        assert button.is_visible() and button.is_enabled()

        with page.expect_download(timeout=15_000) as download:
            button.click()
        path = tmp_path_factory.mktemp("png") / download.value.suggested_filename
        download.value.save_as(path)
        assert path.suffix == ".png"
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG file"

    def test_a_panel_outside_the_guided_ones_has_it_too(self, page):
        _nav_to(page, "Advanced", "Scatter")
        _wait_stable(page, 1500)
        _select_option(page, _sid("relate", "x"), "total_bill")
        _select_option(page, _sid("relate", "y"), "tip")
        _click_button(page, _sid("relate", "run_btn"))
        _wait_stable(page, 4000)
        assert page.locator("#relate-chart .pa-chart-download").is_visible()

    def test_an_empty_chart_area_shows_no_button(self, page):
        _nav_to(page, "Describe", "One Variable")
        _wait_stable(page, 1500)
        # Nothing has been described yet in this panel on this page load.
        buttons = page.locator(f"#{MOD1}-answer_plot .pa-chart-download")
        assert buttons.count() == 0 or not buttons.first.is_visible()


class TestUploadLoadsOnChoose:
    """"Upload complete" then "No dataset loaded" read as a failed upload."""

    def test_choosing_a_file_loads_it_without_a_second_press(self, page, tmp_path_factory):
        csv = tmp_path_factory.mktemp("upload") / "choose_loads.csv"
        csv.write_text("g,v\na,1\nb,2\nc,3\n", encoding="utf-8")
        _nav_to(page, "Data", "Load")
        _wait_stable(page, 1500)
        page.locator(f"{_sid('load', 'source')} input[type=radio][value='upload']").first.check()
        _wait_stable(page, 1200)
        page.locator(_sid("load", "file_upload")).set_input_files(str(csv))
        # Wait for the load rather than a fixed time: under the full suite's
        # load a fixed 4 s was once too short and read the previous dataset.
        info_box = page.locator(_sid("load", "load_info"))
        deadline = time.time() + 20
        info = info_box.inner_text()
        while "3 rows" not in info and time.time() < deadline:
            page.wait_for_timeout(500)
            info = info_box.inner_text()
        assert "3 rows" in info, info
        status = page.locator(_sid("load", "status-panel_status")).inner_text()
        assert "choose_loads" in status, status
        # Leave the page as the later tests expect it: tips active, bundled
        # picker showing. The upload made the three-row file the active one.
        _load_bundled(page, "tips")


class TestReportFromTheGuidedPanels:
    """Open sections become their own cells; a cell moves in one step."""

    def test_open_sections_add_one_cell_each_and_a_cell_moves_in_one_step(self, page):
        _nav_to(page, "Report", "Report Builder")
        _wait_stable(page, 1000)
        _click_button(page, _sid("report_builder", "clear_report"))
        _wait_stable(page, 1500)

        _nav_to(page, "Relate", "Two Variables")
        _select_option(page, _sid(MOD2, "y"), "tip")
        _select_option(page, _sid(MOD2, "x"), "day")
        _select_option(page, _sid(MOD2, "color_by"), "")
        _click_button(page, _sid(MOD2, "run_btn"))
        _wait_stable(page, 4000)
        for section in ("picture_open", "model_open"):
            _close_section_of(page, MOD2, section)
        _open_section_of(page, MOD2, "test_open")
        page.evaluate(
            "() => document.querySelectorAll('.shiny-notification').forEach(n => n.remove())"
        )
        _click_button(page, _sid(MOD2, "code-add_to_report"))
        _wait_stable(page, 2000)
        note = page.locator(".shiny-notification").first.inner_text()
        assert "Added 2 cells" in note, note

        _nav_to(page, "Report", "Report Builder")
        _wait_stable(page, 2500)
        editor = page.locator(_sid("report_builder", "cell_editor"))
        assert "2 cells" in editor.inner_text()
        assert _headings(page) == ["Relate: tip by day", "Relate: tip by day, test"]

        # Move the second cell to position 1 by typing the position.
        boxes = editor.locator("input[type=number]")
        boxes.nth(1).fill("1")
        boxes.nth(1).dispatch_event("change")
        _wait_stable(page, 2500)
        assert _headings(page) == ["Relate: tip by day, test", "Relate: tip by day"]

        # A heading is the author's to rewrite, and the rewrite sticks.
        first = page.locator(_sid("report_builder", "cell_editor") + " input[type=text]").first
        first.fill("Is the gap between days chance?")
        first.dispatch_event("change")
        _wait_stable(page, 1500)
        boxes = page.locator(_sid("report_builder", "cell_editor") + " input[type=number]")
        boxes.nth(0).fill("2")
        boxes.nth(0).dispatch_event("change")  # forces a redraw from the server's copy
        _wait_stable(page, 2500)
        assert _headings(page) == ["Relate: tip by day", "Is the gap between days chance?"]

        _click_button(page, _sid("report_builder", "run_all"))
        _wait_stable(page, 5000)
        status = page.locator(_sid("report_builder", "status-panel_status")).inner_text()
        assert "2 OK" in status, status
        output = page.locator(_sid("report_builder", "cell_editor")).inner_text()
        assert "mean tip" in output and "coefficient" not in output

        # Show Code off hides the code in the editor, not only in the export.
        assert "import seaborn as sns" in output
        page.locator(_sid("report_builder", "show_code")).uncheck()
        _wait_stable(page, 2000)
        output = page.locator(_sid("report_builder", "cell_editor")).inner_text()
        assert "import seaborn as sns" not in output, "code still shown with Show Code off"
        assert "mean tip" in output, "the output went with the code"
        page.locator(_sid("report_builder", "show_code")).check()
        _wait_stable(page, 1500)
        _assert_no_shiny_errors(page)


class TestOneVariable:

    def test_a_number_gets_a_summary_and_a_histogram(self, page):
        _nav_to(page, "Describe", "One Variable")
        _wait_stable(page, 1500)
        _select_option(page, _sid(MOD1, "col"), "total_bill")
        _click_button(page, _sid(MOD1, "run_btn"))
        _wait_stable(page, 4000)
        text = _answer(page, MOD1)
        assert "total_bill ranges from" in text, text
        assert page.locator(_sid(MOD1, "answer_plot") + " img").count() == 1
        _assert_no_shiny_errors(page)

    def test_a_category_gets_counts_and_a_bar_chart(self, page):
        _select_option(page, _sid(MOD1, "col"), "day")
        _click_button(page, _sid(MOD1, "run_btn"))
        _wait_stable(page, 4000)
        text = _answer(page, MOD1)
        assert "most common is" in text, text
        _open_section_of(page, MOD1, "test_open")
        assert "distribution of day" in page.locator(_sid(MOD1, "test_text")).inner_text()
