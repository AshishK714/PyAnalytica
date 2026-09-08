"""The answer is visible; everything else is offered -- see docs/DISCLOSURE.md.

Only the app can show this. The tiers are a layout claim -- what a student meets
first, what costs a click, what is not drawn until asked for -- and none of it
is visible from the module source. Regression is the worked example; the other
nine heavy panels follow the same shape.
"""

from __future__ import annotations

import time

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
        time.sleep(0.5)


def _select_option(page: Page, selector: str, value: str) -> None:
    loc = page.locator(selector)
    loc.wait_for(state="attached", timeout=15_000)
    loc.select_option(value, timeout=5000)
    time.sleep(0.5)


def _fit_a_model(page: Page) -> None:
    _nav_to(page, "Data", "Load")
    _wait_stable(page)
    page.wait_for_selector(_sid("load", "bundled_name"), state="attached", timeout=15_000)
    _select_option(page, _sid("load", "bundled_name"), "titanic")
    page.locator(_sid("load", "load_btn")).click()
    _wait_stable(page, 4000)

    _nav_to(page, "Model", "Regression")
    _wait_stable(page, 2000)
    page.wait_for_selector(
        f"{_sid('regression', 'target')} option:not([value=''])",
        state="attached", timeout=15_000,
    )
    _select_option(page, _sid("regression", "target"), "Age")
    page.evaluate(
        """(sel) => {
            const el = document.querySelector(sel);
            Array.from(el.options).forEach(o => o.selected = ['Fare','Pclass'].includes(o.value));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        }""",
        _sid("regression", "features"),
    )
    time.sleep(1)
    page.locator(_sid("regression", "run_btn")).click()
    _wait_stable(page, 6000)


class TestRegressionTiers:

    def test_t01_the_answer_is_visible_without_a_click(self, page: Page):
        _fit_a_model(page)
        expect(page.locator(_sid("regression", "model_summary"))).to_be_visible()
        expect(page.locator(_sid("regression", "coef_table"))).to_be_visible()
        assert "R" in page.locator(_sid("regression", "model_summary")).inner_text()

    def test_t02_the_diagnostics_are_offered_by_name(self, page: Page):
        """Closed is not the same as hidden: the student has to see it exists."""
        body = page.locator("body").inner_text()
        assert "Diagnostic plots" in body
        assert "Multicollinearity" in body

    def test_t03_the_diagnostic_plots_are_not_drawn_while_closed(self, page: Page):
        """The saving, and the reason the answer has the screen to itself."""
        for widget in ("resid_plot", "qq_plot"):
            plot = page.locator(f"{_sid('regression', widget)} img")
            assert plot.count() == 0, f"{widget} was drawn while its section was closed"

    def test_t04_opening_the_section_draws_them(self, page: Page):
        """The other half: a disclosure that reveals an empty box is worse than none."""
        page.locator(".accordion-button:has-text('Diagnostic plots')").first.click()
        _wait_stable(page, 4000)
        for widget in ("resid_plot", "qq_plot"):
            plot = page.locator(f"{_sid('regression', widget)} img")
            expect(plot).to_be_visible(timeout=20_000)

    def test_t05_a_disclosed_plot_gets_room(self, page: Page):
        """350px was shorter than the figure drawn into it, which clipped titles."""
        box = page.locator(f"{_sid('regression', 'resid_plot')} img").bounding_box()
        assert box is not None
        assert box["height"] >= 450, f"disclosed plot is only {box['height']:.0f}px tall"

    def test_t06_the_supporting_section_opens_too(self, page: Page):
        page.locator(".accordion-button:has-text('Multicollinearity')").first.click()
        _wait_stable(page, 2500)
        expect(page.locator(_sid("regression", "vif_table"))).to_be_visible(timeout=15_000)


class TestHeadingsBelongToTheirSection:

    def test_a_heading_never_stands_over_content_that_is_not_there(self, page: Page):
        """A static heading sits in the layout whether or not its content
        rendered -- which is how a failed evaluation showed "Confusion Matrix"
        over an empty page."""
        _nav_to(page, "Model", "Regression")
        _wait_stable(page, 1500)
        page.reload(wait_until="networkidle")
        time.sleep(4)
        _nav_to(page, "Model", "Regression")
        _wait_stable(page, 2000)

        body = page.locator("body").inner_text()
        # Before anything is fitted there is no VIF table, so nothing should
        # announce one outside a section the student chose to open.
        assert "VIF (Multicollinearity)" not in body


class TestClosedSectionsCostNothingToCompute:
    """Hiding an output stops it being drawn, not built.

    Cluster is the case that matters: the elbow plot fits k-means at every k in
    2..10 and scores each with silhouette, which is O(n^2). That is 697ms of a
    730ms run on 891 rows, and on the 53,940-row diamonds it does not finish --
    all to draw a plot that starts closed. The panel now tells the library not
    to build what nobody is looking at, and opening the section re-runs it.

    The risk this guards is the obvious one: a section that, once opened, shows
    nothing because the work was skipped and never redone.
    """

    def test_t07_cluster_runs_with_both_sections_closed(self, page: Page):
        _nav_to(page, "Data", "Load")
        _wait_stable(page)
        page.wait_for_selector(_sid("load", "bundled_name"), state="attached", timeout=15_000)
        _select_option(page, _sid("load", "bundled_name"), "titanic")
        page.locator(_sid("load", "load_btn")).click()
        _wait_stable(page, 4000)

        _nav_to(page, "Model", "Cluster")
        _wait_stable(page, 2000)
        page.wait_for_selector(
            f"{_sid('cluster', 'features')} option:not([value=''])",
            state="attached", timeout=15_000,
        )
        page.evaluate(
            """(sel) => {
                const el = document.querySelector(sel);
                Array.from(el.options).forEach(o => o.selected = ['Age','Fare'].includes(o.value));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }""",
            _sid("cluster", "features"),
        )
        _wait_stable(page, 1000)
        page.locator(_sid("cluster", "run_btn")).click()
        _wait_stable(page, 6000)

        expect(page.locator(_sid("cluster", "cluster_summary"))).to_be_visible()
        assert page.locator(_sid("cluster", "profiles")).inner_text().strip()
        # Neither figure was built, so neither is on the page.
        assert page.locator(f"{_sid('cluster', 'elbow_plot')} img").count() == 0
        assert page.locator(f"{_sid('cluster', 'scatter_plot')} img").count() == 0

    def test_t08_opening_the_elbow_builds_it(self, page: Page):
        """The half that would break if the flag were only a rendering hint."""
        page.locator(".accordion-button:has-text('Choosing k')").first.click()
        _wait_stable(page, 8000)
        expect(page.locator(f"{_sid('cluster', 'elbow_plot')} img")).to_be_visible(
            timeout=30_000
        )

    def test_t09_the_answer_is_the_same_either_way(self, page: Page):
        """Re-running with the plots must not change the clustering."""
        before = page.locator(_sid("cluster", "profiles")).inner_text()
        page.locator(".accordion-button:has-text('Choosing k')").first.click()
        _wait_stable(page, 5000)
        after = page.locator(_sid("cluster", "profiles")).inner_text()
        assert before == after, "the cluster profiles changed when a plot was toggled"
