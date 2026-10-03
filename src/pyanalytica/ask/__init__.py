"""Question-shaped analysis: the variable types pick the method.

``describe_one`` answers "what does this column look like?" and ``relate_two``
answers "how does Y relate to X?". Each returns an :class:`AskResult`, a
ladder of rungs: describe, picture, test, model. The panels show the first
rung and offer the rest.
"""

from pyanalytica.ask._result import TREAT_CHOICES, AskResult, Rung, resolve_kind
from pyanalytica.ask.one import describe_one
from pyanalytica.ask.two import relate_two

__all__ = ["AskResult", "Rung", "TREAT_CHOICES", "describe_one", "relate_two", "resolve_kind"]
