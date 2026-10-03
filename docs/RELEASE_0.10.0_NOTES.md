# What changed in 0.10.0, and how to test it

> **0.10.1 (same day)** fixes what a student-style run of a nine-question
> assignment found; the run's log is in the course folder
> `MSTM_F_26/Week_6/HW4_app_test/friction_log.md`. Add to Report on Describe
> and Relate now sends one cell per rung (the answer, plus each open section),
> so the report shows the table the student saw; coloured scatter lines keep
> their colours when re-run; Report Builder has a reader view (Show Code off),
> readable tables, a Move to box, distinct cell names, a load step that
> explains itself, and print layout that does not leave half-blank pages.
> Details in CHANGELOG under 0.10.1. Section 4 below describes 0.10.0.

Written 2 October 2026 for the next session, which will work through a
nine-question visualization assignment in the app and report every point of
friction. Commit b60950b, tag v0.10.0, pushed to GitHub, **not on PyPI**.
Students are on 0.9.2.

To run it: `Python_Radiant\.venv\Scripts\python.exe -m pyanalytica`
(an editable install, so the source tree is what runs). `--port N` and
`--no-browser` are accepted.

## 1. The menu

| Tab | Sub-tabs | Was |
|---|---|---|
| Data | Load, Profile, View, Transform, Combine, Export | unchanged |
| **Describe** | **One Variable**, Correlate, Timeline | Correlate and Timeline were Visualize |
| **Relate** | **Two Variables**, Group By / Summarize, Pivot, Cross-tab | the tables were Explore |
| Model | Regression, Classify, Evaluate, Predict, Cluster, Reduce | unchanged |
| **Learn** | Simulate, Practice | Simulate was Explore; Practice was top-level |
| Homework | | unchanged |
| Report | Report Builder, Notebook, Procedure | unchanged |
| **Advanced** | Distribution Plots, Scatter, Group Plots, Means, Proportions, Correlation | Visualize > Distribute / Relate / Compare and the three Analyze panels, renamed, every option kept |
| AI Assistant | | unchanged |

Explore, Visualize and Analyze no longer exist as tabs. Each Advanced panel
has a one-line signpost at the top saying what it does and which Describe or
Relate panel answers the same question with the test attached.

Extensions that declared `parent="Explore"`, `"Visualize"` or `"Analyze"`
land under Relate, Describe and Advanced respectively.

## 2. Describe > One Variable

Pick a column, press **Describe**.

- A number: sentence (range, median, mean, skew remark), `describe()` table
  with a missing row, histogram with mean and median lines. Sections:
  *Another picture* (boxplot), *Test* (Shapiro-Wilk, with the n > 30 caveat).
- A category: sentence (most and least common), count and percent table,
  bar chart. Sections: *Another picture* (horizontal percent bars), *Test*
  (chi-square goodness of fit against an even split).
- **Treat it as**: auto / number / category. Auto reads a numeric column with
  12 or fewer whole-number levels as a category and the sentence says so.
- Refuses, with a sentence, a date (points to Timeline), an identifier, free
  text, an empty column.

## 3. Relate > Two Variables

Pick Y and X, optionally **Colour by**, press **Answer**. The two column
types pick the analysis:

| Y | X | Rung 1 on screen | Another picture | Test | Model |
|---|---|---|---|---|---|
| number | category | group table (count, mean, median, std), boxplots | bar of means with 95% CI | two-sample t-test for 2 groups, one-way ANOVA above, assumption lines | regression on group dummies: the same means as coefficients |
| number | number | n, r, r², slope, intercept; scatter with fitted line | hexbin | Pearson correlation test with CI | the fitted line as an equation |
| category | category | row-percent cross-tab, grouped count bars | percent-of-all bars | chi-square with Cramer's V, sparse-cell warning | pointer to Model > Classify |
| category | number | read the other way round, roles swapped, sentence says so | | | pointer to Model > Classify |

- The sentence always names the cell that stands out and states how each
  column was read. The test rung says which test it chose and why.
- **Colour by** (a third, categorical column, 12 or fewer levels): group
  table becomes two-way and the sentence names the cell; boxplots and bars
  get a hue; the scatter gets one fitted line per colour and the table gives
  r within each group plus "all"; the cross-tab nests by colour and the bar
  chart gets one panel per colour. The test rung notes that the test itself
  ignores the colour.
- **Treat Y as / Treat X as**: as above. The guide shown before the first
  run lists the table above.
- Refuses: the same column twice, a colour that is Y or X or numeric with
  many levels, a category with more than 12 groups, fewer than 3 rows.
- Show Code is every rung's code in order under headings, and runs as one
  cell in Report Builder.
- Rung-2 figures are drawn only when their section is open; opening it
  re-runs the analysis. The procedure recorder gets one step per press.

## 4. Add to Report on every panel

The **Add to Report** button sits beside **Show Code** on every panel that
shows code (24 panels). It sends the last shown code to Report > Report
Builder as a code cell with a badge (load, transform, visualize, analyze,
ask, model, ...) and a description. Imports are inferred from the code's
prefixes (`pd.`, `np.`, `plt.`, `sns.`, `stats.`); Report Builder pre-imports
those anyway. Pressing it before running anything says so.

Found while wiring it: Report Builder's watcher for outside additions
re-triggered itself and froze the session (busy spinner forever) on the
first press from any panel. Fixed; covered by a browser test. **Watch for
any other way to make the busy indicator stick.**

The report path is now: run panels, press Add to Report on each, open
Report > Report Builder, Add Text cells between them, Run All Cells,
download HTML, print to PDF from the browser. There is no PDF export.

## 5. Transform > Add Binned Column takes cut points

New **Cut points** box, e.g. `30` or `18, 35, 50`. A value equal to a cut
point goes in the upper bin; ends are padded with infinities so no value
falls outside; bins are named "under 30", "30 to under 35", "50 and above",
or whatever is typed in Bin labels. Blank cut points keeps the old
equal-width behaviour with Number of bins.

## 6. Scatter trend lines

Advanced > Scatter (and the scatter inside Two Variables) now draws one
fitted line per group with Colour By, labelled with its R², and one line per
panel with facets. Before, Colour By drew one line through everything and
facets drew none. Shown code does the same.

## 7. Fixed in 0.9.2, same day, already on PyPI

A `result` table repeating under every later Report Builder cell; printed
output invisible in the HTML export; the grouped-histogram snippet that
seaborn rejected; `errorbar=None` missing from the bar-of-means snippet;
`markdown` now a core dependency.

## Known gaps and things not done

- `menus` in a course config has never had an effect (`is_menu_visible` is
  imported, never called). Keys renamed, not wired.
- Two Variables has no facet option, only colour. Facets remain in Advanced.
- One Variable has no "compare to a value" test; Advanced > Means and
  Proportions do that.
- The course videos and Canvas pages for Weeks 4 to 6 name the old tab paths.
- The ANOVA and t-test snippets quote group levels as strings, so with a
  numeric grouping column (1/2) the shown test code compares against `"1"`
  and finds no rows. Pre-existing, not fixed.

## How to report friction

For each step: the panel, what was pressed, what was expected, what
happened, and whether a sentence on screen explained it. Silence, a stuck
busy spinner, a chart without a title, a table a student cannot download, or
a choice the student had to know a statistics term to make are all findings.
The design rule is general capability on sound UI and pedagogy, never a fit
to one assignment.

Tests: 1228 unit, 143 browser, all green at b60950b.
