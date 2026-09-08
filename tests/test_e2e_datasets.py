"""Browser tests that vary the *data*, not just the module.

Why this file exists
--------------------

The main suite drives every module once, on `tips`, with a hand-picked pair of
columns. A human tester following the same worksheet on `titanic` and on his
own CSVs found faults in the first hour that the suite had passed over for
months. Reviewing what he hit, the pattern was never "this module is broken" —
it was "this module is broken *for this kind of column*":

* Pivoting by a numeric column produces integer column labels, and the data
  grid failed on those with "'DataFrame' object has no attribute 'dtype'".
  Pivoting tips by `sex` works; by `size` it did not. The suite tested `sex`.
* A 0/1 integer column classifies as numeric, so `Survived` never appeared in
  Cross-tab's variable list. Nothing errored — the option simply was absent.
* Correlate with a single column selected produced no chart and no message.

So these tests parameterise over column *shapes*: numeric labels, binary
integers, high-cardinality text, all-missing, constant. One module, several
kinds of data, rather than several modules on one kind of data.

They are slower than the main suite and deliberately narrow.
"""

from __future__ import annotations

import pytest

from tests.test_e2e import (  # reuse the harness
    _assert_choices_include,
    _assert_no_error_text,
    _assert_no_shiny_errors,
    _assert_output_has_content,
    _click_button,
    _nav_to,
    _open_section,
    _select_multiple,
    _select_option,
    _sid,
    _wait_stable,
)

# `app_url` and `page` come from tests/conftest.py, so this module gets its own
# app and browser rather than sharing test_e2e's.


def _load_bundled(page, name: str) -> None:
    """Load a bundled dataset and make it active.

    The source picker is a radio group, and _select_option cannot set one --
    its JS fallback assigns .value to a <div> and silently does nothing. So
    click the radio directly, and do it unconditionally: an earlier test that
    switched to file upload leaves the picker there, and #load-bundled_name
    does not exist in that mode. That ordering broke all five Practice tests
    in CI while they passed in isolation.
    """
    _nav_to(page, "Data", "Load")
    _wait_stable(page, 1500)
    bundled = page.locator(f"{_sid('load', 'source')} input[type=radio][value='bundled']")
    if bundled.count():
        bundled.first.check()
    _wait_stable(page, 1200)
    _select_option(page, _sid("load", "bundled_name"), name)
    _wait_stable(page, 1000)
    _click_button(page, _sid("load", "load_btn"))
    _wait_stable(page, 3000)


class TestPivotColumnLabelTypes:
    """The crash a human hit in his first twenty minutes."""

    @pytest.mark.parametrize("columns_var,label", [
        ("sex", "string labels"),
        ("size", "integer labels"),
        ("", "no column variable"),
    ])
    def test_pivot_renders_for_any_column_type(self, page, columns_var, label):
        _load_bundled(page, "tips")
        _nav_to(page, "Explore", "Pivot")
        _wait_stable(page, 2000)

        _select_option(page, _sid("pivot", "index"), "day")
        _select_option(page, _sid("pivot", "columns"), columns_var)
        _select_option(page, _sid("pivot", "values"), "total_bill")
        _select_option(page, _sid("pivot", "aggfunc"), "mean")
        _click_button(page, _sid("pivot", "run_btn"))
        _wait_stable(page, 4000)

        # Not "does an element exist" — does a table actually render, and is
        # the region free of exception text.
        _assert_output_has_content(page, _sid("pivot", "pivot_table"), kind="table")
        _assert_no_shiny_errors(page)


class TestBinaryIntegerColumns:
    """A 0/1 integer column is categorical to a student and numeric to us."""

    def test_crosstab_offers_a_binary_outcome(self, page):
        _load_bundled(page, "titanic")
        _nav_to(page, "Explore", "Cross-tab")
        _wait_stable(page, 2500)
        _assert_choices_include(page, _sid("crosstab", "col_var"), ["Survived"])

    def test_crosstab_runs_on_a_binary_outcome(self, page):
        _load_bundled(page, "titanic")
        _nav_to(page, "Explore", "Cross-tab")
        _wait_stable(page, 2500)
        _select_option(page, _sid("crosstab", "row_var"), "Sex")
        _select_option(page, _sid("crosstab", "col_var"), "Survived")
        _click_button(page, _sid("crosstab", "run_btn"))
        _wait_stable(page, 3000)
        _assert_output_has_content(page, _sid("crosstab", "crosstab_table"), kind="table")


class TestDegenerateSelections:
    """Selections a student makes by accident must say something."""

    def test_correlate_with_one_column_explains_itself(self, page):
        _load_bundled(page, "titanic")
        _nav_to(page, "Visualize", "Correlate")
        _wait_stable(page, 2500)
        _select_multiple(page, _sid("correlate", "cols"), ["Age"])
        _click_button(page, _sid("correlate", "run_btn"))
        _wait_stable(page, 3500)

        # Either a chart or an explanation, and the explanation lives in its
        # own output beside the plot. Silence is the bug -- the chart element
        # existed and showed nothing, with no reason given anywhere.
        guidance = page.locator(_sid("correlate", "guidance")).inner_text().strip()
        chart_images = page.locator(f"{_sid('correlate', 'chart')} img").count()

        assert guidance or chart_images, (
            "selecting one column produced no chart and no explanation"
        )
        if guidance:
            assert "two" in guidance.lower(), (
                f"the explanation should say how many columns are needed: {guidance!r}"
            )

    def test_correlate_with_several_columns_draws(self, page):
        _load_bundled(page, "titanic")
        _nav_to(page, "Visualize", "Correlate")
        _wait_stable(page, 2500)
        _select_multiple(page, _sid("correlate", "cols"), ["Age", "Fare", "Pclass"])
        _click_button(page, _sid("correlate", "run_btn"))
        _wait_stable(page, 4000)
        _assert_output_has_content(page, _sid("correlate", "chart"), kind="image")


class TestDatasetSwitching:
    """Loading a dataset should take you to it; refreshing should not move you."""

    def test_loading_a_dataset_makes_it_active(self, page):
        _load_bundled(page, "tips")
        assert page.locator(_sid("ds", "dataset")).input_value() == "tips"

        _load_bundled(page, "titanic")
        active = page.locator(_sid("ds", "dataset")).input_value()
        assert active == "titanic", (
            f"loading titanic left {active!r} active — a tester reported having "
            f"to hunt for the dropdown after loading"
        )

    def test_switching_back_sticks(self, page):
        _load_bundled(page, "tips")
        _load_bundled(page, "titanic")
        _select_option(page, _sid("ds", "dataset"), "tips")
        _wait_stable(page, 1500)

        # Visiting other tabs refreshes their dropdowns, which used to reset
        # the active dataset to whichever name sorts first.
        for tab in ("Profile", "View", "Transform"):
            _nav_to(page, "Data", tab)
            _wait_stable(page, 1200)

        assert page.locator(_sid("ds", "dataset")).input_value() == "tips"


class TestErrorTextIsNotOutput:
    """An exception shown as text is not a Shiny error, and used to pass."""

    def test_profile_on_a_wide_mix_of_types(self, page):
        _load_bundled(page, "titanic")
        _nav_to(page, "Data", "Profile")
        _wait_stable(page, 3000)
        _assert_no_error_text(page, "body")
        _assert_no_shiny_errors(page)

    def test_every_visualize_tab_is_free_of_error_text(self, page):
        _load_bundled(page, "titanic")
        for tab in ("Distribute", "Relate", "Compare", "Correlate", "Timeline"):
            _nav_to(page, "Visualize", tab)
            _wait_stable(page, 1500)
            _assert_no_error_text(page, "body")


class TestDateParsingOnUpload:
    """A CSV date column must become a date, so Timeline has an axis to use."""

    def test_uploaded_dates_are_recognised_and_timeline_works(self, page):
        import os

        csv = os.path.abspath("examples/tester_files/sales.csv")
        _nav_to(page, "Data", "Load")
        _wait_stable(page, 1500)

        # Switch the source to file upload. Note this is a radio group, not a
        # select -- _select_option's fallback sets .value on a <div> and does
        # nothing, which is why this clicks the radio directly.
        radio = page.locator(f"{_sid('load', 'source')} input[type=radio][value='upload']")
        if radio.count():
            radio.first.check()
            _wait_stable(page, 1200)
            # The id is on the <input> itself, not a wrapper. Note also that
            # every module's file input exists in the DOM at once, so a bare
            # input[type=file] selector picks a hidden one from another tab.
            page.locator(_sid("load", "file_upload")).set_input_files(csv)
            _wait_stable(page, 2000)
            _click_button(page, _sid("load", "load_btn"))
            _wait_stable(page, 4000)

            _nav_to(page, "Visualize", "Timeline")
            _wait_stable(page, 2500)
            options = [
                o.strip()
                for o in page.locator(f"{_sid('timeline', 'date_col')} option").all_inner_texts()
            ]
            assert "date" in options, (
                f"Timeline was offered no date column after uploading a CSV "
                f"with dates. Offered: {options}"
            )


class TestPracticeDrills:
    """Practice had never been driven in a browser, only unit-tested.

    Doing so found two faults at once: every question's feedback was registered
    under the same output id, so checking an answer showed nothing; and the
    "load the tips dataset" hint never cleared once tips was loaded.
    """

    def test_a_correct_answer_says_so(self, page):
        _load_bundled(page, "tips")
        _nav_to(page, "Practice")
        _wait_stable(page, 2500)

        page.locator(_sid("practice", "ans_rows")).fill("244")
        _click_button(page, _sid("practice", "check_rows"))
        _wait_stable(page, 2000)

        feedback = page.locator(_sid("practice", "fb_rows")).inner_text()
        assert feedback.strip(), "checking an answer produced no feedback at all"
        assert "correct" in feedback.lower()

    def test_a_wrong_answer_says_so_and_offers_the_hint(self, page):
        _load_bundled(page, "tips")
        _nav_to(page, "Practice")
        _wait_stable(page, 2500)

        # 25.29 was the answer under the simulated tips data; against the
        # real data it is wrong, which is what this test needs.
        page.locator(_sid("practice", "ans_mean_bill")).fill("25.29")
        _click_button(page, _sid("practice", "check_mean_bill"))
        _wait_stable(page, 2000)

        feedback = page.locator(_sid("practice", "fb_mean_bill")).inner_text().lower()
        assert "not quite" in feedback
        assert "profile" in feedback  # the hint, so a wrong answer is a route forward

    def test_each_question_has_its_own_feedback(self, page):
        """All six were writing to one output, so only one could ever show."""
        _load_bundled(page, "tips")
        _nav_to(page, "Practice")
        _wait_stable(page, 2500)

        page.locator(_sid("practice", "ans_rows")).fill("244")
        _click_button(page, _sid("practice", "check_rows"))
        _wait_stable(page, 1500)

        assert page.locator(_sid("practice", "fb_rows")).inner_text().strip()
        assert not page.locator(_sid("practice", "fb_max_bill")).inner_text().strip()

    def test_the_dataset_hint_clears_once_loaded(self, page):
        _load_bundled(page, "tips")
        _nav_to(page, "Practice")
        _wait_stable(page, 2500)
        hint = page.locator(_sid("practice", "dataset_hint")).inner_text().lower()
        assert "using the tips dataset" in hint, (
            f"the hint still tells the student to load a dataset they have: {hint!r}"
        )

    def test_score_counts_attempts_and_resets(self, page):
        _load_bundled(page, "tips")
        _nav_to(page, "Practice")
        _wait_stable(page, 2500)

        page.locator(_sid("practice", "ans_rows")).fill("244")
        _click_button(page, _sid("practice", "check_rows"))
        _wait_stable(page, 1500)
        assert "1 of 6 correct" in page.locator(_sid("practice", "score_panel")).inner_text()

        _click_button(page, _sid("practice", "reset"))
        _wait_stable(page, 1500)
        assert not page.locator(_sid("practice", "score_panel")).inner_text().strip()


class TestModelSaving:
    """Running a model must leave something for Evaluate and Predict to use.

    Both modules only saved when the "Save Model As" box had been typed into,
    and it is empty by default — so running a regression saved nothing, said
    nothing, and Evaluate stayed permanently empty. Reported by the instructor,
    not by a test, because nothing covered this path.
    """

    def _run_regression(self, page, name: str = "") -> None:
        _nav_to(page, "Model", "Regression")
        _wait_stable(page, 2500)
        _select_option(page, _sid("regression", "target"), "Fare")
        _select_multiple(page, _sid("regression", "features"), ["Age", "Pclass"])
        if name:
            page.locator(_sid("regression", "model_name")).fill(name)
        _click_button(page, _sid("regression", "run_btn"))
        _wait_stable(page, 5000)

    def test_regression_saves_without_being_named(self, page):
        _load_bundled(page, "titanic")
        self._run_regression(page)

        _nav_to(page, "Model", "Evaluate")
        _wait_stable(page, 2500)
        options = [
            o.strip()
            for o in page.locator(f"{_sid('evaluate', 'model_name')} option").all_inner_texts()
            if o.strip()
        ]
        assert options, "running a regression left Evaluate with no model to choose"
        assert any("Fare" in o for o in options), (
            f"the saved model should be named after its target; got {options}"
        )

    def test_a_typed_name_is_respected(self, page):
        _load_bundled(page, "titanic")
        self._run_regression(page, name="my_regression")

        _nav_to(page, "Model", "Evaluate")
        _wait_stable(page, 2500)
        options = [
            o.strip()
            for o in page.locator(f"{_sid('evaluate', 'model_name')} option").all_inner_texts()
        ]
        assert "my_regression" in options

    def test_classify_saves_too(self, page):
        _load_bundled(page, "titanic")
        _nav_to(page, "Model", "Classify")
        _wait_stable(page, 2500)
        _select_option(page, _sid("classify", "target"), "Survived")
        _select_multiple(page, _sid("classify", "features"), ["Age", "Fare"])
        _click_button(page, _sid("classify", "run_btn"))
        _wait_stable(page, 6000)

        _nav_to(page, "Model", "Evaluate")
        _wait_stable(page, 2500)
        options = [
            o.strip()
            for o in page.locator(f"{_sid('evaluate', 'model_name')} option").all_inner_texts()
            if o.strip()
        ]
        assert any("Survived" in o for o in options), (
            f"running a classifier left Evaluate with nothing usable; got {options}"
        )


class TestClusterAndReduceExplainThemselves:
    """Reported as "Cluster and Reduce are not working".

    Both needed two or more features and enforced it with req(), which aborts
    the run without a word. Picking one variable and pressing Run produced
    nothing at all: no chart, no message, no error in the console. The button
    looked broken. The multi-select makes this the *likely* first experience,
    not an edge case -- clicking a second variable deselects the first unless
    you hold Ctrl, and nothing on screen said so.

    The happy-path tests passed throughout, because they always selected two.
    """

    def _guidance(self, page, mod: str) -> str:
        return page.locator(_sid(mod, "guidance")).inner_text().strip()

    def test_cluster_with_one_feature_says_why(self, page):
        _load_bundled(page, "titanic")
        _nav_to(page, "Model", "Cluster")
        _wait_stable(page, 2500)
        _select_multiple(page, _sid("cluster", "features"), ["Age"])
        _click_button(page, _sid("cluster", "run_btn"))
        _wait_stable(page, 3500)

        text = self._guidance(page, "cluster")
        assert text, "one feature produced no clusters and no explanation"
        assert "two" in text.lower(), f"the message should say how many are needed; got {text!r}"
        assert "ctrl" in text.lower() or "cmd" in text.lower(), (
            "a plain multi-select needs Ctrl/Cmd to pick more than one, and the "
            f"message is the only place a student learns that; got {text!r}"
        )

    def test_reduce_with_one_feature_says_why(self, page):
        _load_bundled(page, "titanic")
        _nav_to(page, "Model", "Reduce")
        _wait_stable(page, 2500)
        _select_multiple(page, _sid("reduce", "features"), ["Age"])
        _click_button(page, _sid("reduce", "run_btn"))
        _wait_stable(page, 3500)

        text = self._guidance(page, "reduce")
        assert text and "two" in text.lower(), (
            f"one feature produced no PCA and no usable explanation; got {text!r}"
        )

    def test_cluster_still_runs_on_two_features(self, page):
        _load_bundled(page, "titanic")
        _nav_to(page, "Model", "Cluster")
        _wait_stable(page, 2500)
        _select_multiple(page, _sid("cluster", "features"), ["Age", "Fare"])
        _click_button(page, _sid("cluster", "run_btn"))
        _wait_stable(page, 6000)

        assert not self._guidance(page, "cluster"), "guidance should clear once the run is valid"
        _assert_output_has_content(page, _sid("cluster", "profiles"), kind="table")
        _open_section(page, "Cluster scatter plot")
        assert page.locator(f"{_sid('cluster', 'scatter_plot')} img").count()
        _assert_no_shiny_errors(page)

    def test_reduce_still_runs_on_several_features(self, page):
        _load_bundled(page, "titanic")
        _nav_to(page, "Model", "Reduce")
        _wait_stable(page, 2500)
        _select_multiple(page, _sid("reduce", "features"), ["Age", "Fare", "Pclass", "SibSp"])
        _click_button(page, _sid("reduce", "run_btn"))
        _wait_stable(page, 6000)

        assert not self._guidance(page, "reduce")
        _open_section(page, "Component loadings")
        _assert_output_has_content(page, _sid("reduce", "loadings"), kind="table")
        _open_section(page, "How many components?")
        assert page.locator(f"{_sid('reduce', 'scree_plot')} img").count(), "no scree plot"
        _assert_no_shiny_errors(page)

    def test_a_refused_run_clears_the_previous_result(self, page):
        """The nastier half of the bug.

        Run a valid PCA, deselect everything, press Run: the old charts stayed
        on screen. A student reads that as the answer to what they just asked,
        which makes it a wrong-number bug rather than a cosmetic one.
        """
        _load_bundled(page, "titanic")
        _nav_to(page, "Model", "Reduce")
        _wait_stable(page, 2500)
        _select_multiple(page, _sid("reduce", "features"), ["Age", "Fare", "Pclass"])
        _click_button(page, _sid("reduce", "run_btn"))
        _wait_stable(page, 6000)
        # Opened once and left open, so the second half of this test can tell a
        # cleared result from a closed section.
        _open_section(page, "How many components?")
        assert page.locator(f"{_sid('reduce', 'scree_plot')} img").count()

        page.evaluate(
            "() => {const s=document.querySelector('#reduce-features');"
            "[...s.options].forEach(o=>o.selected=false);"
            "s.dispatchEvent(new Event('change',{bubbles:true}));}"
        )
        _click_button(page, _sid("reduce", "run_btn"))
        _wait_stable(page, 3500)

        assert not page.locator(f"{_sid('reduce', 'scree_plot')} img").count(), (
            "the previous PCA stayed on screen after a refused run"
        )
        assert self._guidance(page, "reduce"), "nothing explained why the run was refused"


class TestFirstClickOnAModelTab:
    """Open Model > Regression and press Run without changing anything.

    Target and Features are populated from the same column list, so the first
    column starts selected in both. Pressing Run used to hand the student a raw
    pandas message -- "Expected unique column names, got: 'Survived' 2 times" --
    which explains nothing about what they did wrong.
    """

    def _first_click(self, page, sub: str, mod: str) -> str:
        _load_bundled(page, "titanic")
        _nav_to(page, "Model", sub)
        _wait_stable(page, 2500)
        _click_button(page, _sid(mod, "run_btn"))
        _wait_stable(page, 6000)
        notes = page.locator(".shiny-notification")
        return " ".join(notes.all_inner_texts()) if notes.count() else ""

    def test_regression_never_shows_the_raw_pandas_message(self, page):
        said = self._first_click(page, "Regression", "regression")
        assert "Expected unique column names" not in said, (
            f"pandas internals reached the student: {said!r}"
        )

    def test_classify_never_shows_the_raw_pandas_message(self, page):
        said = self._first_click(page, "Classify", "classify")
        assert "Expected unique column names" not in said, (
            f"pandas internals reached the student: {said!r}"
        )

    def test_a_target_chosen_as_its_own_feature_is_explained(self, page):
        _load_bundled(page, "titanic")
        _nav_to(page, "Model", "Regression")
        _wait_stable(page, 2500)
        _select_option(page, _sid("regression", "target"), "Fare")
        _select_multiple(page, _sid("regression", "features"), ["Fare"])
        _click_button(page, _sid("regression", "run_btn"))
        _wait_stable(page, 4000)

        said = " ".join(page.locator(".shiny-notification").all_inner_texts()).lower()
        assert said, "using the target as its only feature produced no message"
        assert "itself" in said or "different feature" in said, (
            f"the message should say why this cannot work; got {said!r}"
        )
