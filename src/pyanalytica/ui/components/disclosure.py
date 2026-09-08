"""Show the answer; offer everything else.

Every panel used to render everything it could compute, so the answer to the
question the student asked shared the screen with three things they did not ask
for. Across 30 panels that came to 103 outputs and 18 plots, against eight uses
of a collapsible container in the whole app. See `docs/DISCLOSURE.md`.

The tiers:

1. **The answer** -- the result sentence and the one table that answers the
   question asked. Always visible, never inside one of these.
2. **Supporting evidence** -- the numbers behind the answer. `supporting()`.
3. **Diagnostics** -- plots that check the model rather than state the result.
   `diagnostics()`, which also gives them room; the 350px boxes they used to
   live in are why their titles clipped.

Shiny does not render an output while it is hidden, and renders it when it is
revealed -- both halves verified against a live app rather than assumed. So a
closed section costs nothing to draw. It can still cost something to *compute*,
because the library builds figures during the fit; that is what the
``diagnostics=`` flag on those functions is for.
"""

from __future__ import annotations

from shiny import ui

#: Disclosed plots get room. The old fixed 350px box was shorter than the
#: figures drawn into it, which is what clipped their titles.
PLOT_HEIGHT = "520px"


def supporting(title: str, *content, open: bool = False):
    """A section holding the numbers behind the answer.

    The title lives *inside* the section. A heading placed above one sits in the
    layout whether or not the thing it names exists -- which is how a failed
    evaluation came to show "Confusion Matrix" over an empty page.
    """
    return ui.accordion(
        ui.accordion_panel(title, *content),
        open=open,
        class_="mb-3",
    )


def diagnostics(title: str, *content, open: bool = False):
    """A section holding plots that check the result rather than state it.

    Closed by default: a diagnostic nobody asked for competes with the answer
    for the only screen either of them has.
    """
    return ui.accordion(
        ui.accordion_panel(
            title,
            ui.card(*content, full_screen=True),
        ),
        open=open,
        class_="mb-3",
    )
