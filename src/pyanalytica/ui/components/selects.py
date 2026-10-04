"""Updating a select input without losing what the user chose.

``ui.update_select(id, choices=...)`` with no ``selected`` resets the input to
the first choice. Every module refreshes its dropdowns whenever the active
dataset changes, so the pattern is everywhere, and it produces two distinct
faults:

* **The selection jumps.** A student picks a column, something unrelated
  refreshes the list, and they are silently moved to whichever option sorts
  first. This is how loading a second dataset used to move a student's work
  from ``tips`` to ``diamonds``.

* **The selection goes stale.** Between the list changing and the reset
  landing, the input still holds the old value -- which may not exist in the
  new data. A tester merging ``titanic`` with ``regions`` got
  ``KeyError: ['carat'] not in index``: ``carat`` is a *diamonds* column, left
  over from an earlier pairing.

:func:`update_choices` keeps the current value when it is still offered, and
otherwise falls back deliberately rather than by accident.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from shiny import reactive, ui


def _values(choices: Iterable[Any] | Mapping[Any, Any]) -> list[str]:
    """The selectable values, whether choices are a list or a {value: label} map."""
    if isinstance(choices, Mapping):
        return [str(key) for key in choices.keys()]
    return [str(choice) for choice in choices]


def _current(input: Any, input_id: str) -> str | None:
    """Read an input's current value, or None if it does not exist yet."""
    try:
        with reactive.isolate():
            value = getattr(input, input_id)()
    except Exception:  # noqa: BLE001 - the input may not be rendered yet
        return None
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        return None  # multi-selects are handled by update_multi_choices
    return str(value)


def update_choices(
    input: Any,
    input_id: str,
    choices: Iterable[Any] | Mapping[Any, Any],
    *,
    prefer: str | None = None,
    allow_none: bool = False,
) -> None:
    """Refresh a select's options while keeping the user's choice if it survives.

    Parameters
    ----------
    input:
        The module's ``input`` object.
    input_id:
        The select to update.
    choices:
        The new options, as a list or a ``{value: label}`` mapping.
    prefer:
        What to select when the current value is gone. Defaults to the first
        option.
    allow_none:
        When True, an empty selection is preserved rather than replaced with
        the first option -- for optional inputs such as "Group By".
    """
    # An optional select's empty choice was a blank row, which read as a
    # rendering fault rather than "no grouping". Give it a word. The value
    # stays "", so every panel's ``input.x() or None`` still works.
    if not isinstance(choices, Mapping):
        choices = list(choices)
        if choices and choices[0] == "":
            choices = {"": "(none)", **{str(c): str(c) for c in choices[1:]}}
    values = _values(choices)
    current = _current(input, input_id)

    if current is not None and current in values:
        selected: str | None = current
    elif allow_none and current == "":
        selected = ""
    elif prefer is not None and prefer in values:
        selected = prefer
    else:
        selected = values[0] if values else None

    ui.update_select(input_id, choices=choices, selected=selected)


def update_multi_choices(
    input: Any,
    input_id: str,
    choices: Iterable[Any] | Mapping[Any, Any],
) -> None:
    """The same, for a multi-select: keep whichever selections still exist."""
    values = set(_values(choices))

    try:
        with reactive.isolate():
            current = getattr(input, input_id)()
    except Exception:  # noqa: BLE001 - not rendered yet
        current = None

    kept = [str(v) for v in (current or []) if str(v) in values]
    ui.update_select(input_id, choices=choices, selected=kept or None)
