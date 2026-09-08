# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

The Model tab, swept against an independent sklearn computation for the first
time. **The arithmetic was clean** -- coefficients, accuracies, AUC, k-means
sizes and PCA variance all matched to four decimals, including the leakage
check the coursework is built around, where AUC goes 0.6335 to 0.8644 once a
column recorded after the outcome is added. Every defect below is in how a
number was labelled, or in a control that did nothing.

### Fixed

- **Regression reports the held-out R-squared.** Setting Test Split to 0.3 held
  rows back, fitted without them, computed predictions on them -- and then
  printed the *training* R-squared, labelled simply "R²". That is the one
  number the split exists to avoid. On 25 columns of pure noise the panel read
  0.4886 where the honest figure is -1.5012, and the student who split the data
  precisely in order to check was the one most misled. Both figures are now
  shown, each labelled by the rows it came from.
- **The Classification Threshold slider works.** Model > Evaluate rendered it
  and never read its value, so moving it from 0.5 to 0.9 left the confusion
  matrix and every metric identical -- in the panel where trading precision
  against recall is the entire lesson. The threshold now decides the
  predictions, and the metrics say which threshold produced them.
- **Text features are refused in words.** `job` as a feature gave
  `could not convert string to float: 'admin.'`, a raw sklearn message naming a
  value rather than a column, from the panel where picking `job` is the first
  thing anyone tries. Regression, all three classifiers, clustering and PCA now
  name the column, show its values, and point at Data > Transform > Dummy
  Encode (One-Hot).

### Fixed (Timeline, on pandas 2)

- **Month and weekday names are recognised directly**, rather than inferred
  from what `pd.to_datetime` does with them. What it does depends on the pandas
  version: 3.x dates "mar" to year 1 and plots it, 2.x refuses it as out of
  bounds. Both refuse the column, but on pandas 2 the reader used to get the
  vaguer "does not hold dates" instead of the sentence explaining that the
  values name a month with no year to place it in. Python 3.10 installs pandas
  2.3.3 -- pandas 3 needs 3.11 -- so this was every 3.10 user.

### Fixed (Data > View)

- **A filter that cannot mean anything is refused instead of answered.** Every
  value typed into the filter box arrives as text, and the same mistake used to
  produce three different results, none of them a message: `age == "Mobile"`
  gave 0 rows, which reads as "no records match"; `age > "Mobile"` gave a raw
  TypeError traceback; and `channel > "60"` gave **all 41,188 rows**, because
  "Mobile" sorts after "60" alphabetically. The last is the dangerous one -- a
  meaningless filter silently returned the whole dataset, and every count taken
  afterwards was wrong while looking ordinary. All three now say which column
  holds what, and what to do instead.
- **The "in" filter reads numbers as numbers.** It was the one operator whose
  values were not coerced to the column's type, so `age in 34, 41` matched
  nothing while `age == 34` worked.
- **A refused filter no longer empties the panel.** The check runs as the filter
  is added, so a filter that cannot work never enters the list. Accepting it and
  failing later took out the table, the row count and the download together,
  with the reason shown nowhere.

### Changed

- Accuracy is reported next to the majority-class baseline. On the campaign
  data a model scores 0.889 while answering "No" every time scores 0.8873, and
  accuracy alone does not show that.

### Added

- `tests/test_ui/test_no_dead_controls.py` -- an AST check that every control
  the app renders is read by the code behind it. Milliseconds, no browser. It
  found the threshold slider and reports clean otherwise.
- `tests/test_e2e_evaluate.py` -- Model > Evaluate had no browser coverage at
  all. Six tests, four of which fail against the old code.
- `tests/test_model/test_honest_metrics.py`, including a standing regression for
  the leakage result itself.

## [0.7.2] - 2026-09-07

The second half of the sweep's silent-wrong-answer set. 0.7.1 fixed the two
that lost work or inverted a question; this one fixes the defect that drew a
convincing chart of dates that do not exist.

### Fixed

- **Timeline no longer invents dates.** Any column could be chosen as the date
  axis, and `pd.to_datetime` does not refuse much: month names with no year came
  back as March-December of **year 1**, and the panel drew a confident
  "subscribed_pct over Time" line chart of dates that do not exist. Probing
  pandas found two more of the same shape -- a column of years (2019, 2020) is
  read as *nanoseconds* since 1970, stacking every point on one instant, and
  clock times silently pick up today's date. The date axis is now validated:
  the dropdown offers only columns that can carry a timeline, and the library
  refuses one it cannot justify, naming the column, showing its own values and
  saying what to do instead. The refusal appears on the panel, where it can be
  read, rather than in a five-second toast.
- A column of four-digit years is still accepted -- it is a reasonable thing to
  plot -- but the chart carries a note saying it was read as calendar years.
  Where a choice is made on the reader's behalf, the choice travels with the
  figure into the report and the export.

### Added

- `date_like_rate()` in `data.dates`, so a caller can tell "none of these are
  dates" from "most of these are dates and a few are not". Those need different
  advice, and giving the wrong one sends the reader to the wrong screen.
- `tests/test_e2e_timeline.py`: the dropdown half of the fix, which only a
  browser can check. It fails against the old code.

## [0.7.1] - 2026-09-07

A hotfix for students already running the tool. Everything here came out of a
153-case sweep of every panel against a 41,188-row teaching dataset, where each
number was checked against an independent pandas/scipy/sklearn computation
rather than against the app itself. These three are the ones that lose work or
answer a question nobody asked; upgrade before the next assignment.

### Fixed

- **Add Binned Column no longer destroys the session.** `pd.cut` names its bins
  with pandas `Interval` objects, which Shiny cannot serialise -- and it raised
  downstream of this module's error handling, so no message ever reached the
  screen. The panel simply stopped responding, and the reload it took to recover
  started a new session, discarding the dataset and every derived column. Bins
  are now named in readable text ("37.2 to 57.5"), in order, and the data grid
  coerces any other dtype it cannot encode rather than wedging the session.
- **Pivot row and column percentages are no longer halved by Show Margins.**
  With margins on, the divisor included the "All" total, counting every cell
  twice: `channel` x `subscribed` read 47.4 / 2.6 where the answer is
  94.8 / 5.2, and every row totalled 50%. Cross-tab was never affected, so the
  two panels disagreed on the same quantity. Show Code now prints the margin
  slice it actually used.
- **Proportion tests say which level they treated as a success.** The Success
  Value control defaulted to the alphabetically first level, so a Yes/No outcome
  tested "No" and reported the inverse question with a correct-looking sentence
  and the sign flipped. Binary outcomes now default to the minority level, the
  result leads with "Testing subscribed = Yes.", the summary table names the
  level, and the control is labelled "Which value counts as a 'success'?".

### Changed

- Pivot percentages are rounded for display only, not inside the computation, so
  the decimals control can recover the precision. A 0.04% category no longer
  displays as 0.
- `docs/INSTALL.md` pinned `pyanalytica==0.6.4`, two releases behind. It now
  installs 0.7.1.

### Tests

880 unit tests, up from 860. `test_pivot_normalize_index` was passing *because*
of the margins bug -- it summed the "All" column into the row, so 50 + 50 came
to 100 and looked correct. It now checks the data columns alone.

## [0.7.0] - 2026-09-03

Data > Transform could destroy a column and report success. Everything here came
out of driving the app through the Transform tab against a real teaching dataset
whose percentage columns are stored as text.

### Fixed

- **Converting a column no longer empties it silently.** Convert Data Type used
  pandas' `errors="coerce"` and never looked at the result, so converting a
  column of `"96%"` to a number turned all 5,000 values into blanks, showed
  "Transform applied", and logged nothing. Conversions that would turn real
  values into blanks are now refused, and the message says how many values
  failed, gives an example, and points at String: Replace.
- **The Column selector no longer resets after Apply.** Applying a transform
  replaces the active dataset, which re-rendered the sidebar and quietly reset
  Column to the first column in the table. A second Apply then landed on the
  wrong column -- in testing this converted an ID column to blanks in one click.
  Selections now survive the re-render.
- **Converting text to true/false reads the values instead of their length.**
  `astype(bool)` treats every non-empty string as True, so a Yes/No column
  became all True, silently reversing every "No". Yes/no, true/false, y/n and
  1/0 are now mapped by meaning, and anything unrecognised is refused.
- **Operations on the wrong column type explain themselves.** Stripping
  whitespace from a numeric column, filling text with a mean, or z-scoring text
  raised raw `AttributeError`/`TypeError` tracebacks. They now say which column,
  what type it is, and what is needed instead. Converting a column with decimals
  to a whole number is refused rather than crashing.
- **Add Rank now refuses text, as Add Z-score already did.** Ranking a text
  column silently succeeded and ranked it alphabetically.
- **Add Log no longer disagrees with the code it shows you.** It clamped values
  to 1e-10, so log(0) came out as -23.03 while the generated snippet
  `np.log(df["x"])` would give `-inf`. Non-positive values are now refused and
  the snippet matches what ran.
- **Calculated columns accept ordinary column names.** The expression guard
  matched forbidden words as substrings, so `open_rate * 2`,
  `direct_cost + indirect_cost` and `exit_survey_score - 1` were all rejected.
  Matching is now on whole identifiers.
- **An incomplete category order is refused.** Ordinal Encode silently turned
  any category missing from a supplied order into a blank.
- **Data > Profile flags numbers-stored-as-text in string columns too.** The
  check only looked at object columns, so it missed exactly the case that
  follows a String: Replace.

### Added

- **String: Replace** -- clear characters that stop a column being read as a
  number, such as a `%` suffix or a thousands comma. Missing values stay
  missing rather than becoming the text "nan".
- **String: Extract** -- pull a pattern out of a text column into a new column.
- **Add Calculated Column** -- a new column from an arithmetic expression.
- **Add Conditional Column** -- a new column from a condition, with typed values
  read as numbers where they look like numbers, so a 1/0 indicator averages.
- **Add Binned Column** -- cut a numeric column into labelled bands.
- **Keep original column** option on Dummy Encode, which previously always
  replaced the source column.

These five operations already existed in `data/transform.py` but had never been
wired into the Transform tab, so no one could reach them.

## [0.6.4] - 2026-08-25

Four bugs that reached real people, and the sweep behind them. Every item here
was reported by someone using the app, not found by a test.

### Fixed

- **A trained model is now always saved.** Regression and Classify only saved
  when the "Save Model As" box had been typed into, and it is empty by default.
  So running a model saved nothing, said nothing, and Model > Evaluate and
  Model > Predict stayed permanently empty with no explanation. Models are now
  named after their type and target when the box is blank -- `linear_regression_Fare`,
  `logistic_Survived` -- and the confirmation says where to find them.

- **Cluster and Reduce explain why they will not run.** Both needed two or more
  features and enforced it with `req()`, which aborts without a word: picking
  one variable and pressing Run produced no chart, no message and no error.
  Reported as "cluster and reduce are not working", which is exactly how it
  looked. The Features control is a plain multi-select, so clicking a second
  variable deselects the first unless you hold Ctrl -- and nothing said so.
  Both now explain themselves, and name the Ctrl/Cmd trick.

- **A refused run no longer leaves the previous result on screen.** Running a
  PCA, deselecting everything, and pressing Run again kept the old scree plot
  and loadings displayed, which reads as the answer to what was just asked.

- **No button refuses in silence anywhere.** The three reports above were one
  bug in three places, so every `req()` in the UI was classified by what
  triggers it: 48 sat inside handlers fired by a button press, across 21
  modules, and every one could abort without a word. All 48 now explain
  themselves. The 53 render guards, where an empty region before the first run
  is honest, are unchanged.

- **Model > Regression and Classify no longer leak pandas internals on the
  first click.** Target and Features are populated from the same column list,
  so the first column starts selected in both, and pressing Run immediately
  produced `Expected unique column names, got: 'Survived' 2 times`. The target
  is now dropped from the features with a note, or explained when it was the
  only one.

- **Three `UserWarning`s no longer print on every start.** The Practice module
  passed `qid=qid` into per-question callbacks that are already closed over a
  per-question factory, and Shiny warns about a parameter it cannot supply.
  Unlike the `DeprecationWarning`s of 0.6.3, `UserWarning` *is* shown to
  students by default -- these were the warnings actually reaching them, and
  the filter added in 0.6.3 would not have caught them.

### Changed

- The launcher window now names itself and explains that it is the app, can be
  minimised, and must not be closed. `docs/INSTALL.md` documents starting it
  minimised via the Desktop shortcut's **Run: Minimised** property, in
  preference to hiding it with `pythonw` or a `.vbs` wrapper -- an invisible
  server is one a student cannot stop, and reclaiming the port would mean Task
  Manager.

### Added

- `tests/test_ui/test_no_silent_refusals.py` -- a source-level rule over all 30
  UI modules forbidding a bare `req()` inside a `@reactive.event` handler, plus
  a companion asserting the messages are real sentences. Browser tests could
  not catch this class of bug: every one of them selects valid inputs first, so
  they exercise the path that works. The static rule also covers the modules
  nobody has written a browser test for at all.
- `docs/TEST_PLAN_INSTRUCTOR.md` -- an acceptance pass weighted towards what
  automation is structurally blind to: whether the numbers are actually right,
  what the console prints, and the screens nothing has ever opened.
- Browser coverage for Model > Evaluate, which had none, and for every refusal
  path above. 829 unit tests, 65 browser tests.

## [0.6.3] - 2026-08-24

### Added

- **`starlette` and `uvicorn` are now declared dependencies.** The tutor proxy
  imports them directly; until now they arrived only because shiny installs
  them, so the proxy depended on shiny's internal choice of web stack.
- **`markdown` joins the `[report]` extra.** Report export imports it behind a
  fallback, so exports had been degrading to plain text for anyone who
  installed without extras.
- `scripts/audit_dependencies.py` — reports what is imported without being
  declared, declared without being imported, and which versions actually
  resolve against the floors in `pyproject.toml`.

### Changed

- The launcher suppresses `DeprecationWarning`, `PendingDeprecationWarning`
  and `FutureWarning` from libraries. `PYANALYTICA_WARNINGS=1` restores them.

  **Correction to what this release originally claimed.** It was published
  saying this stopped seaborn deprecation notices reaching students during a
  boxplot or heatmap. It does not, because those were never reaching them:
  `MatplotlibDeprecationWarning` subclasses `DeprecationWarning`, which Python
  hides outside `__main__`. They were visible under pytest, and that was
  mistaken for what a student sees. The warnings a student genuinely saw were
  `ShinyDeprecationWarning`, which subclasses `RuntimeWarning` and which shiny
  forces to display — fixed at source in 0.6.2, and this filter would not have
  caught them. The filter is kept as insurance, not as a fix.

## [0.6.2] - 2026-08-24

The first student email arrived on day one. Nothing had failed -- the app
started and opened -- but the console filled with deprecation warnings and he
reasonably reported it as an error. That, plus fixes finished after 0.6.1.

### Fixed

- **No more wall of warnings on startup.** Shiny 1.7 renamed
  `render.download` and made the old name warn once per decorated function;
  with eleven of them, every start printed twenty-plus lines of yellow text.
  The app now uses whichever name the installed Shiny provides, so it is quiet
  on new versions and still runs on old ones. Development had been pinned to
  an older Shiny than students receive, which is why this surfaced from a
  student rather than from us.
- **`GET /favicon.ico` no longer returns 404** on every start.
- **Practice showed no feedback when an answer was checked.** All six questions
  wrote to the same output, so nothing appeared. The score counter updated,
  which is why the automated tests passed while the feature was unusable.
- The Practice sidebar kept saying "load the tips dataset" after tips was
  loaded.

### Changed

- **Date columns in uploaded files are recognised automatically.** A CSV has no
  types, so a date column arrived as text, Profile reported `str`, and Timeline
  had no date axis to offer. Only columns whose values actually look like dates
  are converted, and at least 95% must parse -- an order reference such as
  `2024-001` is left alone, and numbers are never reinterpreted.
- Python 3.14 is now tested in CI, because that is what UIUC AnyWare ships.

## [0.6.1] - 2026-08-23

Everything here came from one human tester working through the first five
sessions of the test worksheet on `titanic` and his own CSVs. The automated
suite had passed all of it.

### Fixed

- **Pivoting by a numeric column crashed.** The pivot's column labels become
  integers and the data grid failed with "'DataFrame' object has no attribute
  'dtype'", which reached the student as raw text where a table should be. Not
  dataset-specific: pivoting tips by `sex` worked and by `size` did not.
- **Dropdowns reset or went stale.** `update_select` without an explicit
  `selected` snaps the input to the first choice, and between the list changing
  and the reset landing the old value is still live — merging two datasets
  raised `['carat'] not in index`, naming a column from a dataset chosen
  earlier. 49 call sites across 19 modules now preserve the current value.
- **Loading a dataset did not switch to it**, so students loaded a file and
  then had to find the dropdown themselves.
- **Binary and small-integer columns could not be grouped by.** `Survived`
  (0/1) and `Pclass` (1-3) classify as numeric, so neither appeared in any
  "group by" or "cross-tabulate by" list — on the course's main teaching
  dataset. They are offered now; their classification is unchanged, so they
  remain valid regression targets.
- **Correlate with one column selected did nothing at all** — no chart, no
  message. It now explains that a correlation needs two columns.
- `examples/hw1_tips` and its grading demo asked for the mean of `total_bill`
  with the value from the real seaborn dataset rather than the bundled one.

### Changed

- Browser tests assert what is rendered rather than that elements exist, and a
  new suite varies the *data* — numeric versus string pivot labels, binary
  outcomes, degenerate selections — instead of only the module under test.
  Unit 640 → 737; browser 36 → 47.

## [0.6.0] - 2026-08-23

### Changed

- **The app no longer grades homework.** An assignment in a student's hands now
  contains no answer material at all, because an answer their computer can
  check is an answer they can extract: multiple-choice answers fell by hashing
  the options the file already listed, and numeric answers by sweeping values
  at the stated tolerance, both in under a second. Marking happens on the
  instructor's machine against a key that never leaves it.
- **Submissions carry evidence, not verdicts.** No `correct`, no
  `points_earned`, no `auto_total` — a score computed on the student's machine
  was a claim, not a fact. The work log is now taken from the procedure
  recorder, so it carries the pandas/sklearn code behind each step rather than
  only a description, and recording starts when an assignment is opened.
- **Submissions export as HTML** with the same JSON embedded: readable in an
  LMS, parseable by a grading script, one file to upload. Format version
  `pyanalytica.submission/2`; the 0.5.x shape is not readable by this release.
- The `graded:` question flag is gone. It marked which questions had to hide
  their answers, and now they all do.

### Added

- **Practice tab** — self-check drills with instant feedback, separate from
  assignments. Drills carry no marks, so their answers are in plaintext;
  pretending to hide a derivable answer would be theatre. Two bundled drills.
- **`pyanalytica-hw`**, the instructor command line: `build` turns a master
  file into a student assignment plus an answer key, `grade` marks a folder of
  LMS downloads into a gradebook CSV, `inspect` prints one submission.
  Identity comes from the LMS filename, not from the name a student typed.
- `docs/INSTRUCTOR.md` — authoring and marking, end to end.

### Fixed

- An unanswered checkpoint scored a point: submissions now list every question,
  so testing for the presence of an id was always true. Blank counts as
  unanswered.
- A free-response answer containing `</script>` closed the embedded JSON block
  early in an exported submission.
- `examples/hw1_tips` asked for the mean of `total_bill` with 19.79, the value
  from the real seaborn dataset. The bundled data is synthetic and its mean is
  25.29, so every student would have been marked wrong.

## [0.5.1] - 2026-08-22

### Fixed

- `pyanalytica` now accepts `--port`, `--host`, `--no-browser`, and
  `--version`. It previously called `run_app()` with no argument parsing, so
  every option was silently ignored — `--port 8001` still bound 8000, and a
  mistyped option did nothing rather than reporting the mistake.
- The app opens a browser on start instead of leaving students to find the
  address themselves.
- If port 8000 is busy (usually the app already running in another window),
  a free port is chosen and reported, rather than crashing with
  "address already in use". An explicitly requested port still fails loudly.

## [0.5.0] - 2026-08-22

> Note: releases 0.2.0 through 0.4.6 were not recorded here.

### Added

- **Homework authoring** (`homework/authoring.py`) — a master file holds
  plaintext answers and stays on the author's machine; `build()` derives the
  student copy and the instructor answer key from it. Questions marked
  `graded: true` ship with no answer material at all, so their answers cannot
  be recovered from the student copy. Questions left ungraded keep a hash for
  immediate in-app feedback.
- **Authoritative re-grading** (`homework/regrade.py`) — scores collected
  submissions from their raw answers using the instructor key, ignoring the
  scores the student's app wrote into the file. Reports (but does not act on)
  disagreements between claimed and recomputed totals.
- `_assert_code()` coverage in the end-to-end suite: every tested module must
  emit a Show Code snippet that parses as valid Python and contains the
  expected call.
- Browser tests now run in CI.

### Fixed

- **Active dataset no longer resets when the selector refreshes.** Any state
  change — applying a transform, loading a second file — silently switched the
  active dataset to whichever name sorted first alphabetically.
- End-to-end suite repaired: 19 of 40 tests were failing and had never run in
  CI. Test runs are now isolated from `~/.pyanalytica`, so they neither inherit
  state from previous runs nor overwrite the user's own saved session.
- Numeric answers entered as text (`"19.790"`) are coerced before comparison
  during re-grading, instead of being marked wrong.
- Profile tests no longer read a real `ANTHROPIC_API_KEY` from the
  environment, which decided their outcome and printed the key on failure.

## [0.1.0] - 2025-02-10

### Added

#### Core & Data (Phase 1)
- Column type classification (NUMERIC, CATEGORICAL, DATETIME, ID, TEXT)
- `CodeSnippet` system — every function returns equivalent pandas/sklearn code
- Dataset loading with `load_bundled()` and `load_dataset()`
- DataFrame profiling with missing-value and type summaries
- Data transformation: rename, retype, filter, compute, combine

#### Explore & Visualize (Phase 2)
- Group summarize, pivot tables, crosstabs, frequency tables
- Histogram, boxplot, bar chart, scatter plot, line chart, heatmap
- Correlation matrix visualization

#### Analyze & Model (Phase 3)
- Compare group means and proportions with hypothesis tests
- Linear regression and logistic classification
- Model evaluation with metrics, residual plots, confusion matrices

#### Homework & Report (Phase 4)
- YAML-based homework schema with hash-checked grading
- Report export: HTML, Python script, Jupyter notebook

#### AI Agent (Phase 5)
- Rule-based and optional LLM interpretation of results
- AI-powered analysis suggestions
- Challenge questions for student engagement
- Natural-language data queries

#### Enhanced Model & Procedure Builder (Phase 6)
- Model store for saving and reusing trained models
- Prediction from saved model artifacts
- Procedure recorder: capture, replay, and export analysis workflows
- Procedure exports: JSON, Python script, Jupyter notebook
- Decimals control moved to per-module inline widget
- User profile system (`~/.pyanalytica/profile.yaml`)

#### Package & Publish (Phase 7)
- Single-source version via hatchling dynamic versioning
- `python -m pyanalytica` entry point
- Explicit sdist includes for reliable CSV bundling
- GitHub Actions CI (Python 3.10-3.13)
- Accurate README with correct API examples
- This changelog
