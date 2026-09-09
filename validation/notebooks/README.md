# The notebooks

One per section of [`../SPEC.md`](../SPEC.md), plus `anchors.ipynb` for the
textbook results. Nothing here exists yet; the spec is the brief.

## The one rule

**Do not read `src/pyanalytica/`, and do not import it.** Everything these
notebooks are worth rests on being an independent computation. If a notebook
imports the tool, the comparison becomes the tool agreeing with itself, and
`tests/test_validation.py::test_the_notebooks_do_not_read_the_source` will say
so.

Use scipy, statsmodels, pingouin, R, a textbook, or paper — whatever you would
use if PyAnalytica did not exist.

## Running one

From the repository root, so `validation` is importable:

```python
from validation.record import record, note, save

record("means.titanic_age_by_sex.t", -2.499)
note("means.titanic_age_by_sex", "Welch: Levene rejected equal variance at .03")
save("means")
```

`save` writes `validation/expected/<section>.json`. That file, and nothing else,
is what the harness compares against.

## When the tool disagrees

Raise it. Do not edit the notebook to match — the notebook is the reference, and
a difference is the finding the exercise is for. Every defect found in this tool
so far has been in the presentation, not the arithmetic; a disagreement here
would be the first of its kind, which is exactly why it is worth looking for.
