"""A button must never do nothing without saying why.

Three separate people reported the same bug in three different modules --
Correlate with one column, then Cluster, then Reduce -- and the cause was
identical each time: ``req()`` inside a handler fired by a button press. It
aborts the render silently, so the student sees no chart, no message and no
error. The button looks broken.

Browser tests could not catch this class of bug, because every one of them
selected valid inputs first: they exercised the path that works. So this is a
source-level rule instead, which holds for modules nobody has written a browser
test for yet.

The rule
--------

``req()`` is right in a render that has nothing to show *yet* -- before the
first run, an empty region is honest. It is wrong once the student has acted.
So: any function decorated with ``@reactive.event`` must route its ``req()``
calls through ``require()``, which shows the reason before giving up.

If this test fails, the fix is not to add an exemption. It is to write the
sentence the student needs to read.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

MODULES_DIR = Path(__file__).resolve().parents[2] / "src" / "pyanalytica" / "ui" / "modules"


def _module_files() -> list[Path]:
    return sorted(MODULES_DIR.rglob("mod_*.py"))


def _triggered_functions(tree: ast.AST):
    """Functions that only run because the student did something."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        decorators = [ast.unparse(d) for d in node.decorator_list]
        if any(d.startswith("reactive.event") for d in decorators):
            yield node, decorators


def test_the_modules_directory_is_where_we_think_it_is():
    assert MODULES_DIR.is_dir(), MODULES_DIR
    assert len(_module_files()) > 20


@pytest.mark.parametrize("path", _module_files(), ids=lambda p: p.stem)
def test_no_bare_req_in_a_user_triggered_handler(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))

    offenders = []
    seen: set[int] = set()
    for func, decorators in _triggered_functions(tree):
        for node in ast.walk(func):
            if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "req"):
                continue
            if node.lineno in seen:
                continue  # nested walks reach the same call twice
            seen.add(node.lineno)
            source = ast.unparse(node)
            if "require(" not in source:
                offenders.append(
                    f"  {path.name}:{node.lineno} in {func.name}() "
                    f"[{', '.join(decorators)}]\n      {source}"
                )

    assert not offenders, (
        "req() aborts without telling the student anything, and these run only "
        "because the student pressed something:\n"
        + "\n".join(offenders)
        + "\n\n  Use require(condition, message) from "
        "pyanalytica.ui.components.requirements.\n"
        "  In an effect:  if not require(cond, msg): return\n"
        "  In a render:   req(require(cond, msg))"
    )


def _is_forwarded_exception(node: ast.AST) -> bool:
    """Is this message str(exc), or str(exc) with something added to it?"""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _is_forwarded_exception(node.left) or _is_forwarded_exception(node.right)
    return (
        isinstance(node, ast.Call)
        and getattr(node.func, "id", "") == "str"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
    )


@pytest.mark.parametrize("path", _module_files(), ids=lambda p: p.stem)
def test_every_require_message_is_written_for_a_beginner(path: Path):
    """The message is the whole point, so check it is worth reading.

    Guards against the failure mode where this rule gets satisfied with
    require(cond, "invalid input") -- which tells a student no more than the
    silence it replaced.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))

    bad = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "require"):
            continue
        if len(node.args) < 2:
            continue
        message = node.args[1]
        # Constant, or an implicitly concatenated run of constants.
        if isinstance(message, ast.Constant) and isinstance(message.value, str):
            text = message.value
        elif isinstance(message, ast.JoinedStr):
            text = "".join(
                v.value for v in message.values
                if isinstance(v, ast.Constant) and isinstance(v.value, str)
            )
        elif isinstance(message, ast.Name):
            # A shared constant such as NO_DATASET; its wording is checked once
            # in test_the_shared_messages_are_sentences rather than at every
            # call site.
            continue
        elif _is_forwarded_exception(message):
            # require(False, str(exc)) forwards a message the library composed,
            # e.g. Timeline refusing a date axis or View refusing a filter that
            # cannot mean anything. Those sentences name the column, quote the
            # offending values and say which screen fixes it -- more than a
            # literal here could -- and each is asserted in the tests for the
            # function that raises it. Judging them from this file would mean
            # reading the string that is not here.
            continue
        else:
            text = ast.unparse(message)

        if len(text) < 20:
            bad.append(f"  {path.name}:{node.lineno} too terse: {text!r}")
        elif not text.rstrip().endswith((".", "!", "?")):
            bad.append(f"  {path.name}:{node.lineno} not a sentence: {text!r}")

    assert not bad, (
        "A refusal message is read by someone who does not yet know the "
        "vocabulary. Say what to do:\n" + "\n".join(bad)
    )


def test_the_shared_messages_are_sentences():
    """The constants the call sites reuse get the same scrutiny, once."""
    from pyanalytica.ui.components import requirements

    shared = {
        name: value
        for name, value in vars(requirements).items()
        if name.isupper() and isinstance(value, str)
    }
    assert shared, "expected at least NO_DATASET"

    for name, text in shared.items():
        assert len(text) >= 20, f"{name} is too terse: {text!r}"
        assert text.rstrip().endswith((".", "!", "?")), f"{name} is not a sentence: {text!r}"
