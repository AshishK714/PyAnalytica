"""A message that stays on the panel.

Every refusal and every failure in this app was a `ui.notification_show`: a
toast, gone in about five seconds, never in the panel. Three things follow from
that, and all three were reported.

The message cannot be re-read. In a teaching tool the error is often the most
instructive thing on screen -- it is the moment the tool explains why the
analysis is invalid -- and it is the one output that expires.

It cannot be screenshotted. Assignments ask for a picture of what happened.

And it hides a stale result. When a run fails, the panel keeps rendering the
*previous* one; once the toast expires the screen shows a confident answer
beside inputs that did not produce it. A message that stays, in the place the
result would be, is what marks it as gone.

The sweep found a fourth, later: a failure that only toasts is invisible to the
test suite as well. A browser test asserting "it rendered, no error element"
passes while the action fails, because the previous render is still there.

    status = status_server("status")          # in the panel's server
    status_ui("status"),                      # in its layout, above the result

    status.failed("Expected 2 groups, got 12.")   # clears the result too
    status.done("Transform applied.")
"""

from __future__ import annotations

from datetime import datetime

from shiny import module, reactive, render, ui

#: How many messages to keep, so a student can see the sequence they tried.
HISTORY = 4

_STYLES = {
    "error": ("alert-danger", "Could not do that"),
    "warning": ("alert-warning", "Check this"),
    "success": ("alert-success", "Done"),
}


@module.ui
def status_ui():
    return ui.output_ui("panel_status")


@module.server
def status_server(input, output, session):
    """Return a handle the panel uses to say what happened."""
    messages: reactive.Value[list[tuple[str, str, str]]] = reactive.value([])

    def _add(kind: str, message: str, *, toast: bool) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        messages.set(([(kind, message, stamp)] + messages())[:HISTORY])
        if toast:
            # Kept alongside the panel message: the toast is what catches the
            # eye of someone looking elsewhere on the page.
            ui.notification_show(
                message,
                type="error" if kind == "error" else kind,
                duration=8,
            )

    class Status:
        """What a panel says about its own last action."""

        def failed(self, message: str, *, toast: bool = True) -> None:
            """The action could not run. Say so where the result would be."""
            _add("error", message, toast=toast)

        def check(self, message: str, *, toast: bool = True) -> None:
            """The student has not finished choosing. Not an error."""
            _add("warning", message, toast=toast)

        def done(self, message: str, *, toast: bool = False) -> None:
            """It worked. Quiet by default -- the result is the confirmation."""
            _add("success", message, toast=toast)

        def clear(self) -> None:
            messages.set([])

        def last(self) -> tuple[str, str, str] | None:
            current = messages()
            return current[0] if current else None

    @render.ui
    def panel_status():
        current = messages()
        if not current:
            return ui.div()

        kind, message, stamp = current[0]
        css, heading = _STYLES.get(kind, _STYLES["warning"])
        earlier = current[1:]

        return ui.div(
            ui.div(
                ui.tags.strong(heading),
                ui.tags.span(f"  {stamp}", class_="text-muted small ms-2"),
                ui.p(message, class_="mb-0 mt-1"),
                class_=f"alert {css} mb-2",
            ),
            ui.tags.details(
                ui.tags.summary(
                    f"{len(earlier)} earlier message{'s' if len(earlier) > 1 else ''}",
                    class_="text-muted small",
                ),
                ui.tags.ul(
                    *[
                        ui.tags.li(f"{when} — {text}", class_="text-muted small")
                        for _, text, when in earlier
                    ],
                    class_="mb-0",
                ),
                class_="mb-2",
            ) if earlier else None,
        )

    return Status()
