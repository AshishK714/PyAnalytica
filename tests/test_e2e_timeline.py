"""Timeline must not offer a date axis it cannot draw -- issue 2, in the app.

The sweep's repro is a CSV whose only time-like column is a month name with no
year anywhere in the file. The panel offered that column, `pd.to_datetime` dated
every row to year 1, and the result was a confident line chart titled
"subscribed_pct over Time" with an x-axis reading 0001-03, 0001-04, 0001-05.

The library now refuses such an axis, and that is unit-tested. What only the
browser can show is the other half: that the *dropdown* no longer offers the
column, so the student is never walked up to the trap in the first place.

`tests/test_e2e_datasets.py::TestDateParsingOnUpload` is the positive
counterpart -- a CSV with real dates must still get an axis. Both matter: a fix
that refuses everything would pass this file and fail that one.
"""

from __future__ import annotations

import time

from playwright.sync_api import Page


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


def _click_button(page: Page, selector: str, *, timeout: float = 10_000) -> None:
    btn = page.locator(selector)
    btn.wait_for(state="visible", timeout=timeout)
    btn.scroll_into_view_if_needed()
    btn.click()


def _upload(page: Page, csv_path: str) -> None:
    _nav_to(page, "Data", "Load")
    _wait_stable(page, 1500)
    radio = page.locator(f"{_sid('load', 'source')} input[type=radio][value='upload']")
    radio.first.check()
    _wait_stable(page, 1200)
    page.locator(_sid("load", "file_upload")).set_input_files(csv_path)
    _wait_stable(page, 2000)
    _click_button(page, _sid("load", "load_btn"))
    _wait_stable(page, 4000)


def _timeline_date_options(page: Page) -> list[str]:
    _nav_to(page, "Visualize", "Timeline")
    _wait_stable(page, 2500)
    return [
        o.strip()
        for o in page.locator(f"{_sid('timeline', 'date_col')} option").all_inner_texts()
        if o.strip()
    ]


class TestMonthNamesAreNotOfferedAsATimeAxis:

    def test_t01_upload_the_sweep_repro(self, page: Page, tmp_path_factory):
        """A month column, a rate to plot, and no year anywhere in the file."""
        csv = tmp_path_factory.mktemp("timeline") / "campaign_by_month.csv"
        rows = ["month,subscribed_pct,calls"]
        months = ["mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        for i, month in enumerate(months):
            rows.append(f"{month},{5 + i * 0.7:.1f},{1000 + i * 37}")
        csv.write_text("\n".join(rows), encoding="utf-8")

        _upload(page, str(csv))
        expected = page.locator(_sid("ds", "dataset"))
        assert "campaign" in expected.inner_text().lower(), "the CSV did not load"

    def test_t02_month_is_not_offered_as_a_date_column(self, page: Page):
        options = _timeline_date_options(page)
        assert "month" not in [o.lower() for o in options], (
            f"Timeline still offers the month column as a date axis: {options}. "
            f"Dating those values gives year 1."
        )

    def test_t03_no_column_is_offered_rather_than_the_wrong_one(self, page: Page):
        """The old fallback was 'if no date columns, offer every column'."""
        options = _timeline_date_options(page)
        assert not options, (
            f"This file has no date column, so Timeline should offer none. "
            f"Offered: {options}"
        )

    def test_t04_pressing_plot_says_why_instead_of_drawing_year_one(self, page: Page):
        _nav_to(page, "Visualize", "Timeline")
        _wait_stable(page, 2000)
        _click_button(page, _sid("timeline", "run_btn"))
        _wait_stable(page, 2500)

        notice = page.locator(".shiny-notification")
        assert notice.count(), "Plot did nothing and said nothing"
        text = " ".join(notice.all_inner_texts()).lower()
        assert "date" in text, f"the message does not mention dates: {text!r}"
