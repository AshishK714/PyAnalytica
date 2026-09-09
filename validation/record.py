"""How a validation notebook records what it computed.

The notebooks are written without reading the tool's source, so this is the
whole interface between the two halves: the notebook writes values under agreed
keys, and the harness looks each key up and compares. Nothing else passes
between them -- in particular the notebook never imports pyanalytica, which is
the property that makes the comparison worth anything.

    from validation.record import record, save

    record("means.titanic_age_by_sex.t", -2.499)
    record("means.titanic_age_by_sex.df", 712)
    record("means.titanic_age_by_sex.p", 0.0127, tol=1e-4)
    note("means.titanic_age_by_sex", "Welch, because Levene rejected at 0.03")
    save("means")
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
EXPECTED = HERE / "expected"

#: Relative tolerance when a case does not give one. Tight, because two correct
#: implementations of the same quantity should agree to nearly machine
#: precision; anything looser hides a real difference in method.
DEFAULT_TOL = 1e-6

_values: dict[str, dict[str, Any]] = {}
_notes: dict[str, str] = {}


def record(key: str, value: Any, *, tol: float | None = None) -> Any:
    """Record one computed quantity. Returns it, so it can be inlined."""
    if key in _values:
        raise KeyError(
            f"{key!r} was already recorded as {_values[key]['value']!r}. "
            f"Two values under one key means one of them is being discarded."
        )
    _values[key] = {"value": _plain(value), "tol": tol if tol is not None else DEFAULT_TOL}
    return value


def note(key: str, text: str) -> None:
    """Record a choice that could have gone another way, and why.

    These are read by whoever compares the results. A difference with a note
    beside it is a discussion; a difference without one is a puzzle.
    """
    _notes[key] = text


def save(section: str) -> Path:
    """Write everything recorded so far to validation/expected/<section>.json."""
    if not _values:
        raise ValueError("nothing was recorded, so there is nothing to compare")

    EXPECTED.mkdir(parents=True, exist_ok=True)
    path = EXPECTED / f"{section}.json"
    payload = {
        "section": section,
        "values": _values,
        "notes": _notes,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {len(_values)} values to {path}")
    return path


def reset() -> None:
    """Start again -- useful when re-running a notebook from the top."""
    _values.clear()
    _notes.clear()


def _plain(value: Any) -> Any:
    """Whatever numpy or pandas handed back, as something JSON can hold."""
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, (bool, str)) or value is None:
        return value
    if isinstance(value, int):
        return value
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(as_float):
        return None
    return as_float
