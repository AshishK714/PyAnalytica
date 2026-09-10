# Where we left off — 2026-09-09, after 0.9.1

Read this first when picking the project back up. It says what changed, what is
verified, what is still open, and what to do next.

## State

**v0.9.1 is live on PyPI**, tagged on GitHub, verified from a clean venv install
— not from the working tree. `main` and PyPI agree at `a550e8a`.

- 1164 unit tests, 20 skipped; browser suite green on Python 3.10 – 3.14
- Five releases in two days: 0.7.1, 0.7.2, 0.8.0, 0.9.0, 0.9.1
- Repo is `AshishK714/PyAnalytica`; `social-engineer-ai` only redirects

The QA sweep reached ~145 of 153 cases. Only section F — Practice, Homework and
AI — is unswept, deliberately: those three tabs are not used in BADM 579 this
term. They still ship and a student can open them, so they are worth a smoke
check before a release.

## The finding that matters most

Across the entire sweep, **not one defect was a wrong calculation.** scipy,
pandas and scikit-learn were never wrong. Every single defect was in the wrapper:

- a number labelled as something it was not (pivot percentages halved by the
  margin column)
- a control that was rendered but never read (the classification threshold
  slider)
- a refusal that named a pandas internal instead of saying what to do
- an export that could not run (`NameError: df` on the second line of every
  exported script)
- synthetic data wearing a real dataset's name

**Test the wrapper, not the statistics.** That is the single most transferable
conclusion in this project, and it is why the test classes below exist.

## What is open

Two issues, filed 9 Sep, one root cause: **rounding happens where a number is
computed, not where it is shown.**

- **#25 (severity:high, correctness)** — `round(p, 6)` floors any p below 5e-7
  to exactly `0.0`. Titanic Pclass × Survived is 4.5e-23 by scipy and is stored
  as zero, then rendered `p = 0.0000` by `mod_correlation.py:83`. A p-value is
  never zero, and this is the one number the course is built on. The correct
  formatter already exists at `ui/components/assumptions.py:39` but guards only
  the assumption lines.
- **#26 (severity:low)** — cross-tab rounds chi-square to 2dp and the
  proportions panel to 4dp, so two panels show the same statistic differently,
  and the rounding is carried into exports.

Fix direction for both: full precision in the result object, round in the render
layer, one rule per kind of quantity. When that lands,
`tests/test_reconciliation.py` can drop its `DISPLAY_*` tolerances and compare
exactly.

Everything else filed during the sweep — 24 issues — is closed.

## The one release gate still standing

**Validation notebooks.** The scaffolding is committed; the notebooks are not
written.

- `validation/SPEC.md` — a brief for someone who has never seen this source and
  **must not read it**. Written as questions, never methods, so it cannot leak
  the tool's own choices.
- `validation/record.py` — the only interface between the two halves.
- `tests/test_validation.py` — computes the tool's value per key and reports
  match / MISMATCH / unmapped. Skips until notebooks exist, so it is wired into
  CI before there is anything to run.

**Start a fresh session to write them.** If you look at how the tool computes
something and then compute it the same way, both can be wrong together and the
comparison passes green. That has already happened here: a test asserted pivot
rows summed to 100 and passed for two months because it summed the margin column
into the row, and 50 + 50 is also 100.

0.9.1 is the right build for Ashish's own class. It is not yet the build that
carries a credibility claim to another instructor.

## Test classes worth keeping green

- `test_reconciliation.py` — one quantity through two panels, required to agree.
  Needs no oracle at all: two implementations that disagree prove a bug without
  anyone knowing which is wrong. This is how the margins defect surfaced.
- `test_no_dead_controls.py` — every rendered control is actually read.
- `test_exports_run.py` — exported scripts are *executed*, not parsed.
- `test_progressive_disclosure.py` / `test_messages_stay.py` — ratchets with
  explicit shrinking exception lists.
- `test_e2e_*` — failures that happen outside module error handling.

## Next actions, roughly in order

1. **Write the validation notebooks**, blind, in a fresh session.
2. **Fix #25**, and #26 with it — they are one change.
3. **Tutorial videos.** Plan drafted at `MSTM_F_26/PYANALYTICA_VIDEO_PLAN.md`;
   13 episodes following the course module sequence. The start-to-finish episode
   must be out by **Fri 2 Oct** for the project due 18 Oct.
4. Section F smoke check before the next release.
5. **API key handling** — `core/profile.py` reads `ANTHROPIC_API_KEY` or stores
   a key in plaintext in `~/.pyanalytica/profile.yaml`. Nothing leaves the
   machine unless a key is set and none is by default, so this is not urgent —
   but settle it before anyone is told to use the AI tab.

## Rules learned the hard way

1. **No release for a problem no user has experienced.** 0.6.3 shipped a warning
   filter that was a no-op. Decision 12 in `docs/DECISIONS.md`.
2. **Verify against the artefact, not the source tree.** A substring check of
   module source once produced a false failure by matching a *comment*.
3. **Prove the test fails against the old behaviour.** A title-clipping test was
   written, passed, and was believed — against unfixed code, because 4.1px of
   headroom is not negative. A regression test that has never been seen red is
   not evidence.
4. **Moving a plot into a closed accordion makes `to_be_attached()` vacuous.**
   Two e2e assertions passed while asserting nothing. Open the section and
   require the `img`.
5. **A sweep that only checks for a toast will pass against a broken panel.**
   The first Transform sweep went green while `String: Extract` was double-
   wrapping its capture group, because the failure merely toasted.

## Operational gotchas

- **After a PyPI upload, pip lies for a few minutes.** `--no-cache-dir` proves a
  version is live. Do not mistake the cached index for a failed upload.
- **`~/.pypirc` has only a `[pypi]` section**, so a bare `twine upload` goes
  straight to production. Always pass `-r pypi` explicitly. There is still no
  `[testpypi]` section.
- **Probe, test and record with a clean `HOME`.** The app autosaves to
  `~/.pyanalytica/sessions`, so anything that launches it inherits a real
  session. This invalidated a refusal probe, and it put a stray model name into
  the first README screenshot capture. `tests/conftest.py` isolates `HOME` and
  `USERPROFILE`; do the same before recording video, where it cannot be cropped
  out afterwards.
- **`Apply` in Transform commits with no undo**, so browser tests must reload
  the dataset per case. A first sweep reported 14 false failures for this.
- **Python 3.10 installs pandas 2.3; pandas 3 needs 3.11**, and the two disagree
  about parsing. Write version-robust tests — a 0.7.2 merge went red in CI for
  exactly this, and the fix belonged in the product, not the test.
- **The full browser suite takes ~30 minutes.** Use
  `pytest tests -q --ignore-glob="tests/test_e2e*.py"` (~40 s) unless the change
  touches the UI.
