"""One line at the top of a panel saying what it answers and where else to look.

The old tabs were grouped by the kind of output (a table, a picture, a
p-value), so the same question lived in four places and nothing said so. The
Describe and Relate panels are now the front door; the specialised panels
under Advanced carry a signpost back to them.
"""

from __future__ import annotations

from shiny import ui


def signpost(text: str):
    return ui.p(text, class_="text-muted small mb-2 pa-signpost")
