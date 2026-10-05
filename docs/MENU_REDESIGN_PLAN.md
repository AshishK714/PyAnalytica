# Menu redesign: implementation plan

Written 4 October 2026, at version 0.10.4 (commit 9b75aec). This plan turns
the external review, `docs/PyAnalytica Menu Structure Review (v0.10.4).md`
(the "review"), into stages, work packages and sessions. Read the review
first; this file does not repeat its reasoning, only what to build, in what
order, and how to know it is done.

Related files:

| File | What it is |
|---|---|
| `docs/PyAnalytica Menu Structure Review (v0.10.4).md` | The review: 56 findings (S, C, T, L), naming tables, revised tree, stages |
| `MSTM_F_26/Week_6/PyAnalytica_menu_tree_0.10.4.md` | The menu as it was when reviewed, extracted from the code |
| `MSTM_F_26/Week_6/HW4_student_test_prompt.md` | The student-style acceptance test, run at the end of every stage |
| `docs/RELEASE_0.10.0_NOTES.md` | What 0.10.x added; the release notes a tester reads |
| `CHANGELOG.md` | Per-release detail, including the four test runs that shaped 0.10.x |

---

## 0. Scope decision, 4 October 2026: freeze, then a narrower Stage 1

Decided by the instructor:

- **Freeze until 18 October.** Learners are doing HW4 and the FPF conference
  report project (a Word template; charts, tables, within-group context
  checks, one interval or test; no models). Until the project is due, the
  app gets bug fixes and one addition only: a **Download PNG** button on every
  chart (0.10.5), so charts can go into the Word template. No menu moves.
  0.10.6 fixes what a student-style run of the project found (log in
  `MSTM_F_26/Week_6/FPF_app_test_0.10.5/`, a worked solution, not for
  learners): a rate chart with group sizes for a category outcome, rows-used
  wording, the bimodal shape sentence, Welch's df, the proportion difference
  order, Cross-tab labels, and Profile's missing counts.
- **Model and Report work is on hold.** Neither assignment needs it. Every
  finding below whose work package touches Model or Report is marked
  *deferred: Model/Report hold* in the tracker and is not part of Stage 1 or
  Stage 2 until the instructor lifts the hold. Stage 1 keeps the type system,
  labels and the Data, Describe and Relate fixes.
- **No confidence-interval feature for now.** Learners compute intervals by
  hand from what the app shows (n, mean, std dev per group; counts and rates
  from Cross-tab), using the formulas taught in class. The brief accepts an
  interval or a test, and the app gives the test. C12 is deferred.

Everything else that came up and is not being built now is in section 10,
the parking lot.

---

## 1. Who the app is for

Free, open-source software for teaching analytics through a graphical
interface, used from high school through undergraduate and master's
programmes, mostly in business schools, by learners with no programming
background. This audience governs every default (review open question 1).
Scaling between levels is done by course presets that hide tabs, sub-tabs
and sections (S11), not by a beginner or advanced mode.

---

## 2. Decisions to confirm before Session 1

Each has a recommendation. Record the answer here before work starts.

| # | Decision | Recommendation | Answer |
|---|---|---|---|
| D1 | Remove Advanced entirely in Stage 3 (S1)? | Yes, but keep a searchable **Find a method** index (method name, then where it now lives), because many courses and textbooks teach tests by name | |
| D2 | Drop the Run button for live results (open question 15)? | No. Keep Run. Live updates make model fits and large datasets feel slow and stale; revisit per panel later | |
| D3 | Spelling convention | American English throughout (Color, Summarize), matching most business-school textbooks and the code's own vocabulary (`color`, `hue`) | |
| D4 | Publish 0.10.4 to PyPI before Stage 1? | Yes, once the instructor's current students are past any project that relies on the 0.9.2 menu; it is tested and is a better base for students than 0.9.2 | |
| D5 | Default decimals | 2 for values, p-values to 3 with "< 0.001" (C16) | |
| D6 | The three course presets (S11) | **Intro** (Data, Describe, Relate, Report; no tests or models), **Standard** (adds tests and Model), **Full** (everything) | |
| D7 | Version numbers | Stage 1 = 0.11, Stage 2 = 0.12, Stage 3 = 0.13; 1.0 after a term in use | |
| D8 | Advanced during Stages 1 and 2 | Stays, with signposts and "More options" links; removed only in Stage 3 after the checklist passes | |

---

## 3. Answers to the review's open questions

From the code at 9b75aec. Findings that depended on an answer are adjusted
in the right-hand column.

| # | Question | Answer | Effect on the plan |
|---|---|---|---|
| 1 | Audience | High school to master's, mostly business schools (section 1) | Governs defaults |
| 2 | What does Profile show? | Three sub-tabs: Overview (shape, a "Column Types" summary), Quality (missing values, duplicates, flags), Columns (per-column statistics) | Overview (S6, T4) builds on it; type is shown but cannot be set |
| 3 | Does Apply overwrite; is there undo? | Transform's Apply and View's Apply to Dataset both replace the active dataset. `WorkbenchState` keeps an undo stack of 20 and a reset to the original, but **no control exposes either** | C13 gets a cheap first step in Stage 1: an Undo last change and Reset to original button. Steps applied stays in Stage 3 |
| 4 | Is a fit saved without a name? | Yes. Regression and Classify both save under a readable default name | C2 is done; only the label changes ("Model name") |
| 5 | Preparation inside models | Cluster and Reduce already standardise (`StandardScaler`, shown in the code). All models and tests drop rows with any missing value in the chosen columns, silently | C3 becomes "show the standardise step as a visible, default-on checkbox". New item **M1**: say how many rows were dropped for missing values on every model and test result |
| 6 | Regression output | scikit-learn `LinearRegression` for the fit; standard errors and p-values from the OLS formula in `model/regression.py` | No change; keep it. Category predictors (T1) must flow through that formula with the reference category named |
| 7 | Welch or pooled; intervals | Welch when Levene's test rejects equal spread, pooled otherwise. Intervals: one-sample t, correlation, one- and two-proportion tests. **No interval** for the difference of two means | C12 needs the two-sample mean-difference interval added to `analyze/means.py` |
| 8 | Drop first level default | Off | L5: turn on |
| 9 | Two Variables with a date or text column | Refused with a sentence; a date points to Timeline | S4 and T12 as reviewed |
| 10 | View filters combine how? | AND. `data/view.py` also supports OR, but the panel does not offer it | T6 adds "Match all / any conditions" |
| 11 | Report paths; panel names in files | Procedure records, builds, and exports JSON, Python and Jupyter; **it does not replay on new data**. Notebook exports the session's whole history. Saved sessions store datasets, not panel names. Panel names ("Relate > Group By / Summarize") appear as **text** in about 90 places: hints in bundled practice drills, refusal messages, signposts, docstrings | Renaming panels needs a sweep of those strings, not aliases. Add a test that every "Tab > Sub-tab" string in the source names a panel that exists |
| 12 | Signposts | One line atop each Advanced panel: what it offers, and which guided panel answers the same question with the test attached | Stage 1's "More options" link is their reverse |
| 13 | Assistant | Rule-based by default; uses Claude if `ANTHROPIC_API_KEY` is set and `anthropic` is installed. Sees the last entry of the session history. Natural Language Query matches column names in the question to build pandas code; whether it runs that code is to be checked in Session 2c | S10 as reviewed; check before moving it into a drawer |
| 14 | Does Evaluate adapt to model type? | Yes: confusion matrix and ROC for classifiers, error measures and residuals for regressions; sections absent when they do not apply | No change |
| 15 | Live results without Run | Possible in Shiny; see D2 | Not planned |

---

## 4. Rules for every session

These are what kept 0.10.x stable. They apply to every work package.

1. **No fitting to one assignment.** Changes must hold for any dataset and
   course. The HW4 test checks capability; it does not set design.
2. **The screen and the report agree.** Every table and chart a panel shows
   must come out the same when sent to the report. Extend
   `tests/test_ask/test_screen_equals_report.py` to each new or changed panel,
   including chart category order.
3. **Shown code is real library code** that runs as written, tested by
   executing it.
4. **The existing lint suites stay green** (`tests/test_ui/`): every control
   read, no bare `req()` in a button handler, refusal messages are sentences,
   no toast-only messages, at most one unconditional plot per panel, every code
   panel wired to the report.
5. **Rename sweeps.** Any change to a tab, sub-tab or label also updates every
   text mention (section 3, question 11), the browser tests' navigation, the
   docs' tester worksheets, and the release notes.
6. **One finding, one test.** Each finding fixed gets a regression test that
   names the finding ID in its docstring.
7. **Verification at the end of every session**, in this order, all of it:
   - unit suite with CI's ignore list;
   - every browser test file (about 30 minutes; run in the background);
   - build the wheel, install it in a new venv outside the repo, run the smoke
     script (import, a report through every guided case, the app answers HTTP
     200);
   - commit, tag, push to GitHub, and confirm CI is green on all five Python
     versions with `gh run list`;
   - at the end of each **stage**, a student-style run with
     `HW4_student_test_prompt.md`, compared with the previous run.
8. **PyPI only on the instructor's say-so.**

---

## 5. Stage 1: wording, types, defaults (version 0.11)

No panel moves; no learner's habit breaks. Two sessions.

### Session 1a: the type system and the shared picker (foundation)

Everything else in Stage 1 hangs on this.

**WP 1.1 One type function** (`core/types.py`)
- Five visible types: Number, Category (unordered or ordered), Date, Text,
  Identifier. "Groupable" becomes a property, `few_values`, not a sixth type.
- Fixes in the same function: T5 (a date groups only by period), T13 (a
  category with more than 30 values shows the top 10 and Other), T16 (any
  all-distinct whole-number column is an identifier, not only one named "id").
- A per-dataset **type override** stored in `WorkbenchState`, set from
  Overview in Stage 2 and from "For this analysis, treat as" now.
- Done when: one function answers "what type is this column, and can it
  group?", and every panel calls it. Unit tests for each rule.

**WP 1.2 One shared column picker** (`ui/components/column_picker.py`)
- Lists every column, grouped by type, each with a type label.
- Columns that do not fit the slot are shown greyed with a one-line reason,
  and where one exists a fix ("Make ranges in Data > Transform").
- Shiny's standard select cannot grey a single option with a reason; build it
  on selectize's disabled options and option groups, or a small custom
  component. Spike this first and record what worked.
- Done when: the picker is used by every panel in place of hand-filtered
  lists; a browser test opens each panel and checks greyed entries carry a
  reason.

**WP 1.3 Picker fixes that now become one-line slot rules**
T2 (Classify target greys many-valued numbers, with "use Regression"), T6
(View conditions by type; value picker for categories; date picker for dates;
"Match all / any"), T7 (Group By and Timeline colour accept few-value columns
only), T8 (Pivot functions follow the value's type), T9 (Distribution Plots
chart list follows the type), T10 (no category columns: say so, link to Make
ranges), T11 (Dummy and Ordinal Encode include few-value numbers), T17
(Convert Data Type uses the app's type names with the pandas name in
brackets, and offers only conversions the values allow).

### Session 1b: models, defaults, labels, presets

**WP 1.4 Category predictors** (T1, T15, L5)
- Regression and Classify accept category predictors; encode inside the fit
  (one 0/1 column per category, reference category left out and named in the
  output); the OLS p-values in `model/regression.py` cover the dummies.
- Shown code: a scikit-learn `Pipeline` with `OneHotEncoder(drop="first")`,
  or `pd.get_dummies(..., drop_first=True)`; pick one and use it everywhere.
- Regression with a 0/1 target shows a note linking to Classify (T15).
- Dummy Encode's "Drop first level" defaults on (L5).
- Done when: charges ~ region + smoker fits, the coefficient table names the
  reference categories, and the shown code reproduces the coefficients.

**WP 1.5 Defaults and dependent controls**
C1 (Purpose: Explain or Predict replaces the test-split default; Evaluate
offers Test Set only when rows were held out), C2 (label only), C3 ("Standardize
first" checkbox, on, already the behavior), C8 (Pivot shows Normalize and
Value only where they apply), C9 (Proportions shows Alternative for one- and
two-sample tests only), C10 (Alternative written as a sentence with the real
group names), C11 (pick which two groups to compare), C16 (decimals per D5),
C17 (Random seed and Max depth under More options; "No limit" checkbox), C15
(Treat as under its picker with the detected type), M1 (rows dropped for
missing values stated on every model and test).

**WP 1.6 Timeline period and function** (C6)
Period [as recorded, day, week, month, quarter, year] and "Summarize each
period by" [sum, average, count]; "Number of rows" as a value.

**WP 1.7 Course presets** (S11)
- Read `menus` from the course configuration; extend it to sub-tabs and
  sections; ship the three presets in D6 as YAML files.
- Done when: launching with each preset shows exactly its tabs; a test per
  preset.

**WP 1.8 Labels** (the review's section 5, all three tables, and C20)
- Apply every rename in the review's naming tables except the panel and tab
  renames, which belong to Stage 2 (they move with the panels). Respect D3.
- Chart Type and other choices keep their internal keys; only labels change,
  as Transform's actions did in 0.10.4.
- Keep the review's "terms learners must learn" unchanged.
- Rename sweep per rule 5.

**WP 1.9 Teaching wording and links** (L1, L2, L3, S1 stopgap, S7)
- L1: "is associated with" in answer sentences; one standing line under
  results from observed data.
- L2: the test heading names the method and the reason it was chosen.
- L3: the reversed reading is stated on screen.
- S1 stopgap: a **More options** link from each guided answer to the matching
  Advanced panel, pre-filled with the same variables.
- S7: Combine's description says only what exists.

**WP 1.10 Undo** (first step on C13)
Expose the existing undo stack and reset: **Undo last change** and **Reset to
original** in the header beside Active Dataset.

**Stage 1 acceptance:** 8 of the 13 high-severity findings closed (T1, T2,
T4, C1, C2, C3, C6, S11); student-style run shows no regression and no
"refused after Run" for a reason the picker could have shown.

---

## 6. Stage 2: move and merge panels (version 0.12)

Panels move once, born with their Stage 1 names. Old tab and sub-tab names
stay findable through the Find a method index (D1). Three sessions.

### Session 2a: Relate's tables, time and many variables
- **Summary Table** replaces Group By / Summarize, Pivot and Cross-tab (S2),
  with "Show as", "Show totals", type-aware "Summarize by", Save as dataset,
  and a **Chart this table** section [bar, line, heat map] (C7). The chi-square
  for counts moves with it.
- **Over Time** = Timeline moved to Relate (S4); Two Variables hands over to
  it when X is a date.
- **Many Variables** = Correlate moved to Relate (S3).
- Done when: every option of the three old table panels is reachable in
  Summary Table (checklist test), and the screen-equals-report test covers
  each "Show as".

### Session 2b: Data stage
- **View** becomes browse only; filter and sort move to Prepare (S5, S6).
- **Prepare** replaces Transform with the column-first design in review
  section 4 (T3, C14): Work on [One column | Rows | Whole table], actions
  grouped by type with other groups greyed and explained, "Save result as"
  new or replace, before-and-after Preview. Add the missing actions listed in
  review section 4 (keep rows, sort, sample, rename or combine categories, set
  order, date parts, days between, round, keep columns).
- **Overview** replaces Profile and lets the learner set each column's type,
  including Ordered category (T4, T14).
- **One Variable** answers dates and text (T12) and gains **Compare with a
  target** (C5); normality moves to Checks.
- **Combine** gains Stack rows, Reshape and flexible keys (S7), enabling
  paired comparison (C18) in Two Variables.
- A bundled dataset with a date and a money column (C19).

### Session 2c: Report, Learn, Assistant, consistency
- **Report** and **History** replace Report Builder, Notebook and Procedure
  (S8); a starter outline: Question, Data, Findings, Recommendation (S13).
- **Homework** moves under Learn (S12).
- **Assistant** becomes a side drawer opened from any page, with "Explain this
  result" on each answer (S10). Check first what Natural Language Query runs.
- Cluster and Reduce add their results as columns (C4).
- The two-sample mean-difference interval leads the test section (C12).
- The same tools (CSV, decimals, Expand) under every table and chart (C21).

**Stage 2 acceptance:** the revised tree in review section 6 matches the app
except Advanced and the Stage 3 components; the student-style run finds
nothing it cannot reach.

---

## 7. Stage 3: rebuild on the grammar (version 0.13)

Start with a design document (`docs/GRAMMAR_DESIGN.md`) written and agreed
before code. It must settle:

- **Chart component.** Roles (x, y, color, shape, size, facets), mark chosen
  from the types with allowed alternatives, statistic, position. The shown
  code library: seaborn.objects with classic-seaborn fallbacks for box and
  violin (the earlier recommendation), or another choice, decided in the
  document.
- **Test component.** specify, hypothesize, method (formula, with a
  shuffling view, L4), calculate (estimate, interval, p), visualize.
- **Model pipeline.** Fit merges Regression and Classify; preparation steps
  visible; outcome type picks the method family (S9).
- **Steps applied** in Prepare, each removable (C13).

Then, in order: chart component (replaces six chart builders), test component
(replaces Means, Proportions, Correlation and both test sections), model
pipeline, steps applied, and last **Advanced removed** (S1) after a checklist
confirms each of its options is reachable from a guided answer: violin and
strip plots, density curve, facets, marker shape and size, rank-based tests,
one-sided alternatives, expected proportions, target mean.

**Stage 3 acceptance:** every chart in the app is drawn by one component and
every test by one component, verified by the screen-equals-report and legend
tests over all combinations; the student-style run passes on the HW4 data and
on one dataset it has never seen.

---

## 8. Finding tracker

Every review finding, where it is handled, and its status. Update the status
column as work lands.

| ID | Severity | Stage / WP | Status |
|---|---|---|---|
| S1 | high | link in 1.9; removal in Stage 3 | |
| S2 | high | 2a | |
| S3 | medium | 2a | |
| S4 | medium | 2a | |
| S5 | high | 2b | |
| S6 | low | 2b | |
| S7 | medium | description 1.9; features 2b | |
| S8 | medium | 2c | deferred: Model/Report hold |
| S9 | medium | Stage 3 | deferred: Model/Report hold |
| S10 | medium | 2c | deferred: Model/Report hold |
| S11 | high | 1.7 | |
| S12 | low | 2c | |
| S13 | medium | 2c | deferred: Model/Report hold |
| C1 | high | 1.5 | deferred: Model/Report hold |
| C2 | high | 1.5 (label only; behavior already right) | deferred: Model/Report hold |
| C3 | high | 1.5 (visible checkbox; already standardizes) | deferred: Model/Report hold |
| C4 | medium | 2c | deferred: Model/Report hold |
| C5 | medium | 2b | |
| C6 | high | 1.6 | |
| C7 | high | 2a | |
| C8 | medium | 1.5 | |
| C9 | medium | 1.5 | |
| C10 | medium | 1.5 | |
| C11 | medium | 1.5 | |
| C12 | medium | 2c | deferred: Model/Report hold |
| C13 | medium | undo in 1.10; steps applied in Stage 3 | deferred: Model/Report hold |
| C14 | medium | 2b | |
| C15 | low | 1.5 | |
| C16 | low | 1.5 | |
| C17 | low | 1.5 | deferred: Model/Report hold |
| C18 | medium | 2b | |
| C19 | low | 2b | |
| C20 | low | 1.8 | |
| C21 | low | 2c | |
| T1 | high | 1.4 | deferred: Model/Report hold |
| T2 | high | 1.3 | deferred: Model/Report hold |
| T3 | high | 2b | |
| T4 | high | 1.1, 1.2; Overview in 2b | |
| T5 | medium | 1.1 | |
| T6 | medium | 1.3 | |
| T7 | medium | 1.3 | |
| T8 | medium | 1.3 | |
| T9 | medium | 1.3 | |
| T10 | medium | 1.3 | |
| T11 | medium | 1.3 | |
| T12 | medium | 2b | |
| T13 | medium | 1.1 | |
| T14 | medium | 2b | |
| T15 | medium | 1.4 | deferred: Model/Report hold |
| T16 | low | 1.1 | |
| T17 | medium | 1.3 | |
| L1 | medium | 1.9 | |
| L2 | medium | 1.9 | |
| L3 | medium | 1.9 | |
| L4 | medium | Stage 3 | |
| L5 | medium | 1.4 | deferred: Model/Report hold |
| M1 | new | 1.5 | deferred: Model/Report hold |
| Naming tables | | 1.8 (labels); 2a to 2c (panel names) | |

---

## 9. Session briefs

Paste one into a new Claude Code session started in the `Python_Radiant`
folder. Each assumes the decisions in section 2 are filled in.

### Session 1a

> Read `docs/MENU_REDESIGN_PLAN.md` (this plan) and the review it names. You
> are doing Session 1a: work packages 1.1 to 1.3, the type system, the shared
> column picker and the picker fixes. Start with a spike on how to show a
> greyed option with a reason in a Shiny select, and record the result in the
> plan. Follow every rule in section 4 of the plan, including the full
> verification at the end. Update the finding tracker as each item lands.
> Version 0.11.0a1 at the end of this session; do not publish to PyPI.

### Session 1b

> Read `docs/MENU_REDESIGN_PLAN.md` and the review. Session 1a is done (check
> the tracker). You are doing Session 1b: work packages 1.4 to 1.10. Category
> predictors (1.4) first; it is the most valuable change in the stage. Follow
> section 4's rules and verification, then run the student-style test with
> `MSTM_F_26/Week_6/HW4_student_test_prompt.md` as a fresh subagent and
> compare it with `HW4_app_test_0.10.4`. Release as 0.11.0 on GitHub.

### Session 2a, 2b, 2c

> Read `docs/MENU_REDESIGN_PLAN.md`, the review, and the tracker. You are
> doing Session 2X (section 6). Panels move with their final names; sweep
> every text mention of an old name (section 3, question 11). Follow section
> 4. At the end of 2c, run the student-style test and release 0.12.0 on GitHub.

### Stage 3 design

> Read `docs/MENU_REDESIGN_PLAN.md` section 7 and the review's section 2.
> Write `docs/GRAMMAR_DESIGN.md` covering the chart component, test component,
> model pipeline and steps applied, with the shown-code library decided and
> justified, worked examples for every current chart and test, and a migration
> checklist. Write no code in this session.

---

## 10. Parking lot: everything noted and not built yet

Collected from the review, the four student-style runs (logs in
`MSTM_F_26/Week_6/HW4_app_test*`) and the instructor's discussion. Each line
says where it would fit. Nothing here is scheduled until moved into a stage.

### From the fourth student-style run (0.10.4) and not fixed

| Item | Where it fits |
|---|---|
| Open sections are sent to the report silently: a section opened once stays open on later answers and its chart goes into the next Add to Report. Options: close sections on a new answer, or list what will be sent before adding | Stage 1, WP 1.9 (small) |
| The density view (hexbin) ignores Colour by: it pools both groups under a scatter that splits them | Stage 1, with the chart fixes; or Stage 3's chart component |
| Tables are misaligned inside Report Builder's editor (the export is fine) | Deferred: Model/Report hold |
| Two shades of the second colour (light in histograms and scatters, dark in boxes and bars) | Stage 3 chart component (one palette with one alpha rule) |
| Data > Load says "rows 1 through 12 of 100" for a 1,338-row file: the preview shows the first 100 rows and does not say so | Stage 1 labels |
| Pivot's empty choice reads "(None)", Cross-tab's "(None)", Normalize's "None"; everywhere else "(none)" | Stage 1 labels |
| The printed PDF has many part-blank pages | Deferred: Model/Report hold |
| Inside a report cell the table comes before the chart (same order as the screen) | Deferred: Model/Report hold; revisit with the report outline (S13) |

### From the project run (0.10.5) and not fixed

| Item | Where it fits |
|---|---|
| Ordered categories (Very Low, Low, High, Very High; High School, Bachelors, Masters) are shown in alphabetical order in tables, legends and charts. Needs a way to set a category order once (Transform) that every panel respects | Stage 1, with the type system (WP 1.1) |
| CSV downloads carry full precision while the screen rounds, so "37" sits next to "36.9" in a learner's write-up | Stage 1 labels and decimals (D5) |
| Text columns that hold numbers with a "%" or "$" are listed as categorical, with no hint. The conversion message, once tried, is clear | Stage 1, type system: flag "looks numeric" in Profile and the picker |
| "Treat as Number" on a text column refuses (correctly) but replaces the previous answer with the intro guide | Stage 1, WP 1.9 (keep the last answer on a refusal) |

### Ideas raised in discussion

| Item | Where it fits |
|---|---|
| **Confidence interval for a difference** (means, rates) in Two Variables' test section (C12). Learners compute it by hand for now | Deferred; revisit after the term |
| **Simpson's paradox flag**: when Colour by reverses the direction of the overall comparison in some or all groups, say so in the answer sentence | Stage 1 teaching wording (WP 1.9) or Stage 2a |
| **Grammar-of-graphics chart builder** (geom, stat, position as separate choices; "Bar" with "height shows count, percent, average, median, total") | Stage 3 design; the review's section 2 |
| **Average versus mean wording** everywhere a learner reads it; "Average (mean)" where the term must be learned | Stage 1 labels (the review's naming table covers it) |
| **Higher-resolution chart download** drawn on the server (the 0.10.5 button saves the on-screen image) | Small; any time after the freeze |
| **Student guide for the new menu**: one page mapping 0.9 paths to 0.10 paths, and `check_upgrade.py` raised to the published version, when 0.10.x goes to PyPI | Before any PyPI release (D4) |

### From the review, held with Model and Report

S8, S9, S10, S13, C1, C2, C3, C4, C12, C13, C17, T1, T2, T15, L5 and M1, as
marked in the tracker.
