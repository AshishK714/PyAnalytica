# PyAnalytica Menu Structure Review (v0.10.4)

Oct 4, 2026 · @AV

## 1. Summary

The spine of the app is right. Data, Describe, Relate, Model, Report is already a workflow, and the two guided panels (One Variable, Two Variables) choose the method from the column types better than the method menus of SPSS, jamovi or Radiant do. The edges are what fail.

1. **Advanced is a second app.** It is organised by kind of output (plots, tests), it repeats the guided panels under different labels, and nothing in a guided panel leads to it.
2. **Variable types are handled three ways and never shown.** Columns vanish from pickers without explanation, Transform offers 19 actions for any column, Regression hides category predictors, and Classify accepts a continuous target.
3. **The same job has several homes with different words.** Three table builders sit in Relate, three routes lead to a correlation, three Jupyter exports sit under Report, and colour grouping has four names.

Should the app be organised as a grammar of analytics? Yes as the architecture underneath and as the fixed vocabulary of every panel. No as a compose-it-yourself front door. A grammar rewards people who already know what they want to say; beginners need finished sentences first and the parts second. So keep stages at the top, keep question shapes inside Describe and Relate, extend that idea to Model, and turn Advanced from a place into a state: the options behind each guided answer.

This review judges the tree against the audience in the prompt (high school to master's), not the narrower one in the tree file's own header.

## 2. The grammar

Stages at the top, question shapes inside the analysis stages, and one vocabulary of roles and layers across all of them.

### Top level: stages

Learners at every level know which part of the job they are in (getting data ready, looking, comparing, writing up) long before they know a method's name. PPDAC, GAISE, CRISP-DM and the R for Data Science cycle agree on that order and differ only in labels. The current top level is already five stages plus four things that are not stages (Learn, Homework, Advanced, AI Assistant). The fix is to make the stage row hold only stages.

- **Not question shapes at the top.** Describe, Relate and Model are question shapes; Data and Report are not. Shapes belong one level down, where they already work.
- **Not descriptive, diagnostic, predictive, prescriptive.** That taxonomy classifies finished analyses, not steps a learner takes, and the tree holds nothing prescriptive.
- **No Test stage.** Inference is a layer on a comparison, as in `infer`, where the test follows from the variables specified. A Test tab makes the learner pick a test by name, which is the mistake the guided panels exist to prevent.
- **No Question or Decide tab.** Each would be an empty form. The question and the recommendation belong where they are written: the first and last blocks of the report.

| Stage | The learner's question | Composable parts | Borrowed from |
| --- | --- | --- | --- |
| Data | Is the data ready to answer with? | Verbs on a table: load, look, check types, change a column, keep rows, keep columns, sort, combine, reshape, export | dplyr; CRISP-DM data understanding and preparation |
| Describe | What does one variable look like? | Roles: Variable, Split by. Layers: sentence, numbers, chart, comparison with a target, checks | JMP Distribution; GAISE analyse |
| Relate | Does Y differ or move with X? | Roles: Outcome (Y), Predictor or group (X), Colour by, Split by. Layers: sentence, numbers, chart, how sure, equation | JMP Fit Y by X; infer |
| Model | What explains or predicts Y from many X? | Purpose (explain or predict), outcome, predictors, preparation (encode, standardise, missing), method, fit, evaluate, predict | tidymodels; CRISP-DM modelling and evaluation |
| Report | What should the reader do? | Question, evidence blocks sent from panels, conclusion, export | PPDAC Conclusion; R4DS communicate |

Learn (simulation, practice, homework) and the Assistant sit outside the stage row. They support every stage and are not steps in an analysis.

### Composable parts, and the fixed panels they replace

| Grammar | Parts shown in the interface | Fixed panels today that should be built from these parts |
| --- | --- | --- |
| Answer layers (every result) | In one order everywhere: 1 sentence, 2 numbers, 3 chart, 4 how sure (interval, test), 5 checks, 6 equation, 7 code | One Variable and Two Variables already do this. Model panels and Advanced do not |
| Chart | Data (dataset plus row filter); roles mapped to x, y, colour, shape, size; mark chosen from the types, with allowed alternatives; statistic (bins, averages, trend line, smoothing); split into panels (columns, rows) | Advanced > Distribution Plots, Scatter, Group Plots; Describe > Correlate and Timeline; the charts inside both guided panels. Six chart builders, one grammar |
| Test | Specify (from the roles); hypothesise (null and alternative written as sentences); method (formula by default, shuffling as a second view); calculate (estimate, interval, p); visualise | Advanced > Means, Proportions, Correlation; the Test sections of both guided panels |
| Data verbs | One verb per step, column chosen first, steps listed and removable | Transform's flat list of 19; filter and sort inside View; Group By in Relate |
| Model | Prepare, specify, fit, evaluate, predict as visible steps | Regression and Classify (two panels that differ only in the outcome's type); Cluster and Reduce (no visible preparation) |

### The variable-type rule

**Every column has one visible type, set in one place. Every picker lists every column, grouped by type. Columns that fit the slot are enabled; the rest are greyed with a one-line reason and, where one exists, a one-click fix. After the choice, the panel picks its method from the types and says which method and why. Nothing is refused after Run for a reason the app could have known before Run.**

This replaces all three current approaches. Hiding columns leaves a learner hunting for one that has disappeared, which is worst exactly when the type was read wrongly (a price column with a currency sign read as text). Refusing after Run teaches by punishment. Adapting after the choice is right and stays.

Types: Number, Category (unordered or ordered), Date, Text, Identifier. Groupable stops being a hidden sixth type and becomes a visible property: few values, can group.

| Slot | Number | Category | Date | Text or Identifier |
| --- | --- | --- | --- | --- |
| Variable to describe | summary, histogram | counts, bar chart | earliest, latest, counts per period | distinct count, most common values, no chart |
| Outcome (Y) | yes | yes | greyed: a date cannot be an outcome | greyed |
| Predictor or group (X) | yes | yes | yes, gives the over-time view | greyed |
| Colour by, Split by | only with few values; otherwise greyed with a link to Make ranges (bins) | yes; many values shows the top 10 and Other | by period: year, quarter, month, weekday | greyed |
| Value to summarise | every function | count, distinct count, most common | count, earliest, latest | count, distinct count |
| Model predictor | yes | yes, turned into 0/1 columns automatically with the reference category named | through a date part | greyed |
| Prepare actions | number actions | category and text actions | date actions | text actions |

### On the six principles

- **Principle 1 (question shape) is right and under-applied.** Model is still named by method and Advanced by output.
- **Principle 2 (guided front door) is right, but behind it has been built as somewhere else.** Options should hang off the answer, so growing means opening a section, not learning a second menu.
- **Principles 3 and 4 hold.** The sentence, table, chart, test, equation order in Two Variables is the best thing in the tree.
- **Principle 5 (real code) constrains the grammar, and should.** Role names must map one to one onto the arguments the learner will see: x, y, hue, col, row in seaborn; a scikit-learn Pipeline for preparation. That mapping is how Hue leaked into a label. Keep the mapping, fix the label.
- **Principle 6 (general capability) depends on the `menus` setting, which the app never reads.** Without per-course hiding, general means everything visible to everyone.

Scaling from high school to master's should use two mechanisms and no mode switch: sections closed by default, and course presets that hide tabs, sub-tabs and sections. A global beginner or advanced mode makes the instructor's screen differ from the student's.

### Patterns worth borrowing

| Tool | Borrow | Why it suits these learners | Do not copy |
| --- | --- | --- | --- |
| JMP | Role boxes (Y, X, By) with type icons; options hanging off each result | Same slots every time; depth is one click from the answer | The number of platforms and the menu depth |
| Tableau | Show Me greys chart types that do not fit the chosen fields and says what they need; dates drill by year, quarter, month | It is the greyed-with-reason rule, proven on beginners; makes dates groupable sensibly | The blank shelf canvas as a starting point |
| jamovi | Type icon on every variable; results update as options change, with no Run step | Removes the whole class of refused after Run | The Analyses menu by test family |
| SPSS | Variable View: type and measurement level set once per dataset | One home for types | The Analyze menu by method name |
| Orange | Evaluate as its own step; models compared side by side | Makes the modelling grammar visible | The free-form canvas |
| Radiant | Transform starts from the variable, then a transformation type grouped as change, create, clean; one chart builder with facet row, facet column and fill | Nearest sibling in audience; it is the Transform redesign in section 4 | Its Basics menu by test name (Means, Proportions), which Advanced has inherited |

## 3. Findings

56 findings: 13 high, 34 medium, 9 low. IDs: S structure and placement, C controls and defaults, T variable types, L teaching value. Naming is in section 5.

| ID | Where | Problem | Why it matters for these learners | Severity | Recommendation | Effort |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | Advanced (whole tab) | Organised by kind of output, not question shape. Repeats the guided panels with other labels. Its signposts point back to guided panels; no guided panel points forward | A learner who outgrows a guided answer starts again elsewhere. A beginner reads Advanced as not for me and never finds a faceted box plot | high | Remove the tab. Attach its options to the guided answers as Chart options and Test options, pre-filled with the same variables. Until then, add a More options link from each guided answer | large (link: small) |
| S2 | Relate > Group By / Summarize, Pivot, Cross-tab | Three table builders overlap. Cross-tab is Pivot with count; Group By is Pivot without a column variable. Two Variables produces a fourth version | The learner must choose a tool before knowing the difference, and each names the percent option differently | high | Merge into one Summary Table: Rows, Columns (optional), Values (optional), Summarise by, Show as | medium |
| S3 | Describe > Correlate; Relate > Two Variables; Advanced > Correlation | Correlation has three homes under three tabs. Relating variables is filed under Describe | Learner cannot tell which gives the r to report | medium | Move Correlate to Relate as Many Variables. Fold Advanced > Correlation into Two Variables as test options | medium |
| S4 | Describe > Timeline | A number against a date is a two-variable question filed under Describe. Two Variables lists no date case | A learner with a date as X does not know which panel answers | medium | Move to Relate as Over Time. Two Variables hands over to it when X is a date | small |
| S5 | Data > View | Filter and sort with Apply to Dataset are data-changing verbs in a panel named View. Transform has no row filter | A learner wanting to keep some rows looks in Transform and finds nothing; a learner browsing in View can change the data | high | View becomes browse only. Keep rows where and Sort rows move to Prepare | medium |
| S6 | Data: sub-tab order | Profile comes before View | Learners look at rows before summaries of them | low | Load, View, Overview, Prepare, Combine, Export | small |
| S7 | Data > Combine | Description promises merge, append, reshape; only merge has controls. One key, which must have the same name in both datasets | Stacking two months of sales is commoner in class data than a join. Wide to long is needed for before-and-after data | medium | Add Stack rows and Reshape, or delete the words. Allow different key names and more than one key | medium |
| S8 | Report > Report Builder, Notebook, Procedure | Two report paths and three Jupyter exports, with nothing saying which to use. Notebook is also one of Report Builder's export formats | Learner exports the wrong one for a business reader | medium | Report (curated) and History (everything, plus record and replay). One Jupyter export in each | medium |
| S9 | Model: sub-tabs | Named by method (Regression, Classify, Cluster, Reduce) while Describe and Relate are named by question. The fit, evaluate, predict order is interrupted | Learner must tell regression from classification before starting, which the outcome's type could decide | medium | Fit, Evaluate, Predict (with an outcome); Find Groups, Reduce Variables (without). Outcome type picks the method family | large |
| S10 | AI Assistant (tab) | A helper placed as a destination. Interpret Result needs the result in view, and opening the tab leaves it | Learner must carry the result in their head or paste it | medium | Side drawer opened from the header on any page; an Explain this result button on each answer | medium |
| S11 | Course configuration: `menus` | The setting exists and is not read. Every tab always shows | It is the only mechanism for scaling between levels, and an instructor cannot hide the Assistant for an assessment | high | Read it. Extend it to sub-tabs and sections. Ship three presets | small |
| S12 | Homework (top level); Learn > Practice | Two question-file panels at different menu levels | A top-level slot spent on a non-stage | low | Move Homework under Learn | small |
| S13 | Whole tree | No place for the business question or the recommendation. Nothing prescriptive | PPDAC's first and last steps are what a business reader needs most | medium | Report offers a starter outline: Question, Data, Findings, Recommendation. No Decide tab until there is content for it | small |
| C1 | Model > Regression, Classify: Test Split | Default 0 in Regression, 0.3 in Classify. Evaluate defaults to Test Set, which a default regression does not have | Explain versus predict is the main fork in modelling and it is hidden in a slider default | high | Replace with Purpose: Explain (use every row) or Predict (hold out 30%). Offer Test Set in Evaluate only when rows were held out | small |
| C2 | Model > Regression, Classify: Save Model As | Evaluate and Predict need a saved model, yet saving looks optional | If no name means no saved model, learners reach Evaluate with an empty list | high | Save every fit under a readable default name | small |
| C3 | Model > Cluster, Reduce | No standardise control in the tree | K-Means and PCA on raw columns are dominated by the column with the largest units | high, if not done internally | Standardise first (checkbox, on), visible in the shown code | small |
| C4 | Model > Cluster, Reduce | No way to add cluster labels or component scores as columns | Segments are only useful once profiled in Relate | medium | Add group as a column; Add components as columns | small |
| C5 | Describe > One Variable > Test | Default test is normality for a number and fit to an even split for a category | Neither is the question a beginner brings. Is the average different from the target is | medium | Compare with a target (one-sample t-test or proportion, with interval). Normality moves to Checks | medium |
| C6 | Describe > Timeline: Aggregation | Names the period, not the function, so monthly could be a sum or an average. No quarter or year. Value must be a number, so rows cannot be counted | Sum versus average changes the story. Orders per month is the first thing a business learner tries | high | Period (as recorded, day, week, month, quarter, year) and Summarise each period by (sum, average, count). Add Number of rows as a value | small |
| C7 | Advanced > Group Plots; Relate tables | bar\_of\_means is the only chart of a summary. No chart of totals by category | Sales by region is the commonest business chart | high | Chart this table section on Summary Table: bar, line, heat map | medium |
| C8 | Relate > Pivot: Normalize, Value Variable | Normalize applies to count only but always shows. Value Variable shows when aggregation is count and is ignored | Controls that silently do nothing | medium | Show a control only when it applies (absorbed by S2) | small |
| C9 | Advanced > Proportions: Alternative | Shown for independence and goodness of fit, where direction has no meaning | An option that cannot work | medium | Show for one- and two-sample tests only | small |
| C10 | Advanced > Means, Proportions, Correlation: Alternative | Less and Greater do not say which group comes first | A one-sided test in the wrong direction is a silent error | medium | Write it as a sentence with the real names: Mean of A is less than mean of B | small |
| C11 | Advanced > Means, Proportions: two-sample tests | A group variable with three or more values is refused after Run | Learners often want two of several groups | medium | Let the learner pick the two groups to compare | small |
| C12 | Relate > Two Variables: Test | The tree shows significance tests and no interval for the size of the difference | A business reader needs how big, give or take, before could it be chance | medium | Lead the section with the estimate and its 95% interval, then the test | medium |
| C13 | Data > Transform | No undo or list of applied steps in the tree | A wrong Apply that cannot be reversed makes learners afraid to try | medium | Steps applied list, each removable | large |
| C14 | Data > Transform: Drop Missing Rows, Drop Duplicates | A column is picked first, but nothing says whether the action uses that column or the whole row | Different rows are removed under each reading | medium | Separate column actions from row actions (section 4) | small |
| C15 | Relate > Two Variables: control order | Treat Y as and Treat X as sit apart from Y and X and do not show the detected type | The override is offered before the learner knows what it overrides | low | Put each under its picker with the detected type shown | small |
| C16 | Common: decimals | Default 4 | Too many for a business report; invites false precision | low | Default 2; p-values to 3, with < 0.001 | small |
| C17 | Model: Random Seed; Max Depth (0 = None) | Shown at the same level as Target | Noise before the required choices; a magic number | low | Move under More options; replace 0 = None with a No limit checkbox | small |
| C18 | Whole tree | No paired comparison (before and after on the same rows) | A staple of business cases; learners will misuse the two-sample test | medium | Add to Two Variables once Reshape exists | medium |
| C19 | Data > Load: Bundled Dataset | diamonds, tips and titanic have no date column | Over Time cannot be tried without an upload | low | Add one bundled dataset with a date and a money column | small |
| C20 | Learn > Simulate | Sample Size means number of draws in one mode and size of each sample in another. Goodness-of-fit tests on simulated data add little | Same label, two meanings, in the panel that teaches sampling | low | Number of values to draw; Size of each sample (n). Keep the section closed | small |
| C21 | Common controls | CSV, decimals and Expand appear on some panels and not on similar ones (no decimals on Classify, Evaluate, Cluster, Reduce) | Learners expect the same tools under every answer | low | Same set on every panel that shows a table or a chart | small |
| T1 | Model > Regression, Classify: Features | Category columns are not offered | Region, segment and gender are the usual business predictors. Manual dummy coding first teaches a mechanical step before the idea | high | Accept categories, encode inside the pipeline, name the reference category in the output | medium |
| T2 | Model > Classify: Target | Any number is offered, including continuous ones | One class per distinct value: the wrong method made easy | high | Grey many-valued numbers: Use regression, or make ranges first | small |
| T3 | Data > Transform: Action, Column | 19 actions for any column; type checked after Preview or Apply | The learner cannot learn which action suits which type | high | Section 4 | medium |
| T4 | Every picker | Types are never shown. Groupable is a hidden type | The learner cannot predict why a column is missing | high | Type column in Overview; type icon and grouping in every picker; greyed with reason | medium |
| T5 | Column types: Groupable | Includes dates with any number of values | A date with 300 values is offered for colour and facets | medium | Dates group only by period | small |
| T6 | Data > View: Operator, Value | Every operator for every type; Value is free text | Greater than on text and contains on numbers fail or mislead | medium | Conditions by type; value picker for categories; date picker for dates | medium |
| T7 | Relate > Group By; Describe > Timeline: Group By | Continuous numbers accepted as group keys | A table or chart with one group per price | medium | Few-value columns only; others greyed with Make ranges | small |
| T8 | Relate > Pivot: Value, Aggregation | Mean and sum offered for any column | Average of a text column | medium | Functions follow the value's type | small |
| T9 | Advanced > Distribution Plots: Chart Type | Histogram, boxplot and violin offered for categories; checked after Plot | Wrong chart for the type is the first chart mistake | medium | Chart list follows the type | small |
| T10 | Relate > Cross-tab; Advanced > Proportions | When no column is groupable, every column is offered | Tables with a row per distinct value | medium | Say there are no category columns and link to Make ranges | small |
| T11 | Data > Transform: Dummy Encode, Ordinal Encode | Offered for text and category only | Number-coded categories (region 1 to 4) are the ones that most need 0/1 columns | medium | Include few-value numbers | small |
| T12 | Describe > One Variable | Dates, text and identifiers are refused | The panel adapts for two of five types | medium | Date: earliest, latest, counts per period. Text and identifier: distinct count, most common values | medium |
| T13 | Column types: Category | Under 5% distinct counts as a category | In 10,000 rows a column with 400 values becomes a 400-bar chart | medium | Category up to 30 values; above that show the top 10 and Other | small |
| T14 | Column types | No ordered category | Low, Medium, High sort alphabetically in tables and charts | medium | Set category order in Prepare; Ordered category in Overview | medium |
| T15 | Model > Regression: Target | 0/1 numbers are accepted without comment | Straight-line regression on a yes-or-no outcome | medium | Note with a link to the classification method | small |
| T16 | Column types: Identifier | Requires id in the column name | Order numbers and postcodes pass as numbers and appear as predictors | low | Flag any all-distinct whole-number column; let Overview set it | small |
| T17 | Data > Transform: Convert Data Type | Six pandas names beside the app's own type names | Two type systems for one idea | medium | App type names with the pandas name in brackets; offer only conversions the values allow | small |
| L1 | Relate > Two Variables: labels and Model section | Outcome, predictor and a fitted equation invite a causal reading | Causation from correlation | medium | Answer sentence says is associated with. One standing line under results from observed data | small |
| L2 | Relate > Two Variables: Test | The panel picks the test; the tree does not show it saying why | Which method fits which question is the course's main lesson | medium | Heading names method and reason: Two-sample t-test, because Y is a number and X has 2 groups | small |
| L3 | Relate > Two Variables | Category Y with number X is read the other way round | The learner asked one question and is answered another | medium | Say so on screen; later, show the chance of Y rising with X | small |
| L4 | Whole tree | Every test is formula-based | Shuffling needs no distribution theory, suits the youngest learners, and is what GAISE recommends | medium | See it by shuffling view in the test component | large |
| L5 | Data > Transform: Dummy Encode: Drop first level | If off by default, every 0/1 column goes into a regression | Perfect overlap among predictors, with no explanation | medium | On by default; the need disappears with T1 | small |

## 4. Transform redesign

Choose what to work on first, then see only the actions that fit it. Rename the sub-tab Prepare, since it will also hold the row filter and sort that View holds today.

### Order of choices

1. **Work on:** One column, Rows, or Whole table.
2. **Column** (for One column): the picker groups columns by type and shows each type.
3. **Action:** the groups Any type and the column's own type are open. Groups for other types are shown closed and greyed with the reason, for example: Text actions: this column is a Number. The learner sees that the list depends on the type instead of wondering where an action went.
4. **Options** for the action. These also follow the type: Fill in missing values offers average and median only for numbers.
5. **Save result as:** New column (name suggested, such as price\_log) or Replace this column. Today the Add actions always create and the String actions always replace. One control makes it the learner's choice everywhere.
6. **Preview:** before and after for the first rows, with counts of values changed and values that would become missing. Then **Apply**.
7. The step joins a **Steps applied** list and can be removed.

### The 19 current actions by type

| Current action | Suits | New group | New label | Change |
| --- | --- | --- | --- | --- |
| Fill Missing Values | any type; methods by type | One column: any type | Fill in missing values | Number: average, median, most common, a value, previous, next. Category and text: most common, a value. Date: previous, next, a value |
| Drop Missing Rows | any type | One column: any type, and Rows | Remove rows where this is missing; Remove rows with any missing value | Two actions, so the scope is explicit |
| Rename Column | any type | One column: any type | Rename | None |
| Drop Column(s) | any type | Whole table | Remove columns | Add its opposite, Keep columns |
| Convert Data Type | any type | One column: any type | Change type | Offer only targets the values allow; show how many values would go missing |
| Drop Duplicates | whole rows | Rows | Remove duplicate rows | No column picker |
| Dummy Encode (One-Hot) | category, few-value number | Category | Make 0/1 columns (dummy / one-hot) | Include few-value numbers |
| Ordinal Encode | category | Category | Number the ordered categories (ordinal) | Set the order by dragging, not typing |
| Add Calculated Column | uses several columns | Whole table | New column from a formula | Click a column name to insert it |
| Add Conditional Column | uses several columns | Whole table | New column from a condition | Same |
| Add Binned Column | number; date by period | Number | Make ranges (bins) | None |
| Add Log Column | number, positive values | Number | Logarithm (log) | Before Apply, say how many values are zero or negative |
| Add Z-score Column | number | Number | Standardise (z-score) | None |
| Add Rank Column | number, date | Number | Rank | None |
| String: Lowercase | text, category | Text | lower case | Offered for categories too |
| String: Uppercase | text, category | Text | UPPER CASE | Same |
| String: Strip Whitespace | text, category | Text | Remove extra spaces | Same |
| String: Replace | text, category | Text | Find and replace | Same |
| String: Extract | text | Text | Extract by pattern (regular expression) | Give two worked patterns under the box |

### Actions the tree lacks

- **Rows:** Keep rows where (moved from View), Sort rows (moved from View), Take a random sample.
- **Category:** Rename or combine categories; Set category order.
- **Date:** Take a part (year, quarter, month, weekday); Days between two dates. Today the only date action is conversion to datetime.
- **Number:** Round.
- **Whole table:** Keep columns.

Group By / Summarize is the one data verb to leave out of Prepare. It becomes Summary Table in Relate, with a Save as dataset button for the cases where the summary is the next step's input.

## 5. Naming

One word per idea, and the analytical term in brackets after the plain one wherever a learner must learn it.

### The same idea under several names

| Current labels | Proposed | Reason |
| --- | --- | --- |
| Colour by, Color By, Hue, Group By (Distribution Plots, Timeline) | Colour by | One role, one name, one spelling. The shown code still says hue, which is where the learner meets the term |
| Facet Column, Facet Row | Split into panels (facets): across, down | Facet is worth learning but says nothing on first sight |
| Style By, Size By | Marker shape by, Marker size by | Style of what is unclear |
| (none), (None), None | (none) | Three spellings of the empty choice |
| Column, Variable, Variable X, Numeric Variable, Value Column, Row Variable(s) | Column in Data; Variable in Describe, Relate and Model | A column becomes a variable when it is analysed. Say so once in Overview |
| Y (the outcome), Target (Y), Target, Numeric (Y), Outcome Variable, Variable Y | Outcome (Y) | Six names for one role |
| X (the grouping or predictor), Features (X), Features, Category (X), Group Variable, Grouping Variable, Variable X | Predictor or group (X) in Relate; Predictors (X) (features) in Model | Features is the word in scikit-learn code, so keep it in brackets |
| Aggregation Functions (Group By), Aggregation (Pivot), Aggregation (Timeline) | Summarise by; Period in Over Time | Timeline's Aggregation means the period, not the function |
| Show % of Total, Normalize, Display, Show Percentages | Show as: values, % of row, % of column, % of total | Four names for one choice |
| Show Margins | Show totals | Margins is statistician's shorthand |
| Mean, mean, Std Dev, std, std dev, 50% (median) | Average (mean), Middle value (median), Standard deviation (std dev) | One form everywhere, carrying both words |
| Treat it as, Treat Y as, Treat X as | For this analysis, treat as | Says the override is temporary |
| Alternative Hypothesis: Two-sided (`!=`), Less (`<`), Greater (`>`); Alternative: Two-sided, Less than, Greater than | Alternative, written as a sentence: is different from, is less than, is greater than | Two forms today, and neither says which group comes first |
| One-sample t-test, One-Sample Proportion | Sentence case throughout | Mixed capitalisation |
| Plot, Describe, Answer, Summarize, Create Pivot, Create Cross-tab, Run Test | Show in Describe and Relate; Fit in Model | One action word per stage |
| Colour (British) beside Summarize (American) | One convention throughout | Pick by the main audience |
| Combine (sub-tab), Merge (button), merged (default name), Join (key, type) | Combine for the sub-tab and button; Match rows on a key (join) for the method | Three words for one operation |

### Internal code names shown to learners

| Current labels | Proposed | Reason |
| --- | --- | --- |
| correlation\_matrix, pair\_plot | Correlation matrix; Scatter plot matrix (pair plot) | Underscored identifiers |
| boxplot, violin, bar\_of\_means, strip | Box plot; Violin plot; Bar chart of averages; Individual points (strip plot) | Same |
| hexbin | Density (hexbin) | Matches the guided panel's Density view (hexbin) |
| pearson, spearman | Pearson (straight-line); Spearman (rank order) | Proper names need capitals and a gloss |
| raw, daily, weekly, monthly | As recorded, By day, By week, By month | Raw is jargon |
| mean, median, mode, ffill, bfill, value | Average (mean), Middle value (median), Most common value (mode), Previous value (forward fill), Next value (back fill), A value I type | ffill and bfill are pandas method names |
| `==`, `!=`, `>`, `<`, `>=`, `<=`, contains, isnull, notnull | is, is not, is greater than, is less than, is at least, is at most, contains, is missing, is not missing | The operators appear in the shown code, where they belong |
| int, float, str, category, datetime, bool | Whole number (int), Decimal number (float), Text (str), Category, Date (datetime), True/False (bool) | Matches the app's own type names |
| inner, left, right, outer | Only matching rows (inner), All left rows (left), All right rows (right), All rows from both (outer) | Join types are worth learning; the plain half says what each keeps |
| loc, scale, mu, n, p | Mean (loc), Standard deviation (scale), Average count (mu), Number of trials (n), Chance of success (p) | scipy argument names |

### Labels a beginner would not understand

| Current label | Proposed | Reason |
| --- | --- | --- |
| r Threshold (shown with absolute-value bars) | Hide correlations weaker than | Says what the control does |
| Rolling Window | Moving average over (periods); 0 is off | Unit and off state were unstated |
| Show KDE | Show smooth curve (density) | Acronym |
| Test Split | Share of rows held out for testing | Says what is split and why |
| Random Seed | Random seed (same number, same result) | Purpose in the label |
| Save Model As | Model name | It is required for Evaluate and Predict |
| Max Depth (0 = None) | Maximum depth, with a No limit checkbox | Magic number |
| Classification Threshold | Cut-off for predicting the outcome (threshold) | Plain word first |
| Save to Workbench | Save predictions as a dataset | Workbench appears nowhere else in the tree |
| Dummy Encode (One-Hot); Drop first level | Make 0/1 columns (dummy / one-hot); Leave out the first category (needed for regression) | Says the result and why the option exists |
| Ordinal Encode | Number the ordered categories (ordinal) | Same |
| String: | Text: | String is a programming word; the app's type is Text |
| Join Key | Match rows on | Plain |
| Hypothesized Mean; Hypothesized Proportion (p0) | Target value; Target share (p0) | Business learners think in targets and benchmarks |
| Test (section) | How sure? Could this be chance? | Estimate and interval come before the test |
| Normality (Shapiro-Wilk) | Is it bell-shaped? (normality, Shapiro-Wilk) | Question form, like Choosing k |
| Mann-Whitney U; Kruskal-Wallis H | Rank-based comparison of 2 groups (Mann-Whitney U); of 3 or more groups (Kruskal-Wallis H) | Says when to use it |
| Multicollinearity (VIF); Diagnostic plots | Do the predictors overlap? (multicollinearity, VIF); Check the assumptions (residual plots) | Same |
| Ascending (checkbox) | Order: smallest first, largest first | A choice, not a tick |
| Profile; Transform; Timeline; Correlate | Overview; Prepare; Over Time; Many Variables | Sub-tab names that say what the learner does there |
| Cluster; Reduce; Run PCA | Find Groups (clustering); Reduce Variables (PCA); Run | Reduce alone says nothing |
| Report Builder; Notebook; Procedure | Report; History; Reusable steps | Notebook collides with the Jupyter export; Procedure is opaque |
| HTML, Jupyter, JSON (buttons) | Download as: Web page (HTML), Jupyter notebook, Report file (.json) | Bare nouns as buttons |
| Interpret Result; Natural Language Query | Explain this result; Ask about my data | Plain |

Keep these terms unchanged, because learners must learn them: regression, classification, logistic regression, decision tree, random forest, K-Means, t-test, ANOVA, chi-square, ROC curve, residuals, median, standard deviation, elbow plot, scree plot.

## 6. Revised tree

Nine tabs become six and 32 panels become 21, with every current option kept. Unmarked lines are unchanged. Describe is left with one panel; that is honest, since describing is a one-variable question, and the tab keeps its place in the workflow.

```
PyAnalytica
│
├── Header bar
│   ├── Active Dataset · Remove
│   ├── Session name · Save · Session · Load
│   └── Assistant (side drawer, opens on any page)            [moved] from the AI Assistant tab
│       ├── Mode  [Suggest next step | Explain this result |
│       │          Challenge my thinking | Ask about my data]  [renamed]
│       ├── quick-prompt buttons · chat box
│       └── shown or hidden by the course configuration       [new]
│
├── Data
│   ├── Load
│   │   ├── Data Source  [Bundled Dataset | Upload File | From URL]
│   │   │   ├── → when Bundled:  Dataset  [diamonds | tips | titanic |
│   │   │   │                              one with a date column [new]]
│   │   │   ├── → when Upload:   Upload CSV/Excel  (.csv .xlsx .xls .tsv)
│   │   │   └── → when URL:      URL · Dataset Name
│   │   └── button: Load Dataset
│   │
│   ├── View                                  [moved] ahead of Overview; browse only
│   │   ├── Find rows: Column · Condition [fits the column's type]
│   │   │              · Value [picker fits the type]
│   │   ├── buttons: Add condition · Clear all
│   │   ├── Sort by · Order [Smallest first | Largest first]  [renamed] from Ascending
│   │   ├── link: Keep only these rows (goes to Prepare > Rows)  [new]
│   │   └── Apply to Dataset                                  [removed]
│   │
│   ├── Overview                              [renamed] from Profile
│   │   ├── rows · columns · missing values · duplicate rows
│   │   ├── per column: name · type · Treat as [Number | Category |
│   │   │               Ordered category | Date | Text | Identifier]  [new]
│   │   │               · few values, can group · missing · distinct · examples
│   │   └── Refresh Profile                                   [removed]; updates on its own
│   │
│   ├── Prepare                               [renamed] from Transform
│   │   ├── Work on  [One column | Rows | Whole table]        [new]
│   │   ├── → One column:  Column (grouped by type), then Action
│   │   │                  (groups for other types greyed, with the reason)
│   │   │     Any type:  Rename · Change type · Fill in missing values
│   │   │                · Remove rows where this is missing
│   │   │     Number:    Make ranges (bins) · Logarithm (log) · Standardise (z-score)
│   │   │                · Rank · Round [new]
│   │   │     Category:  Rename or combine categories [new] · Set category order [new]
│   │   │                · Make 0/1 columns (dummy / one-hot)
│   │   │                · Number the ordered categories (ordinal)
│   │   │     Text:      lower case · UPPER CASE · Remove extra spaces · Find and replace
│   │   │                · Extract by pattern (regular expression)
│   │   │                (also offered for categories)
│   │   │     Date:      Take a part [year | quarter | month | weekday] [new]
│   │   │                · Days between two dates [new]
│   │   ├── → Rows:        Keep rows where [moved] from View
│   │   │                  · Sort rows [moved] from View
│   │   │                  · Remove duplicate rows · Remove rows with any missing value
│   │   │                  · Take a random sample [new]
│   │   ├── → Whole table: New column from a formula · New column from a condition
│   │   │                  · Keep columns [new] · Remove columns
│   │   ├── Save result as  [New column (name suggested) | Replace this column]  [new]
│   │   ├── buttons: Preview · Apply
│   │   └── Steps applied (each can be removed)               [new]
│   │
│   ├── Combine
│   │   ├── How  [Match rows on a key (join) | Stack rows (append) [new] |
│   │   │         Reshape (wide to long, long to wide) [new]]
│   │   ├── → join:  Left Dataset · Right Dataset
│   │   │            Match rows on: left column(s) · right column(s)
│   │   │                           [renamed] from Join Key; names may differ [new]
│   │   │            Keep  [Only matching rows (inner) | All left rows (left) |
│   │   │                   All right rows (right) | All rows from both (outer)]
│   │   │                           [renamed] from Join Type
│   │   │            for each shared column: [Keep left | Keep right | Keep both] · suffixes
│   │   ├── Result Name
│   │   └── button: Combine                                   [renamed] from Merge
│   │
│   └── Export
│       ├── Export Format  [CSV | Excel (.xlsx)]
│       └── button: Download
│
├── Describe
│   └── One Variable
│       ├── Variable  Columns: all, grouped by type           [renamed] from Column
│       ├── For this analysis, treat as  [detected type first] [renamed]; under the picker
│       ├── Split by (optional)  Columns: few-value
│       │                        [moved] from Advanced > Distribution Plots: Group By
│       ├── button: Show                                      [renamed] from Describe
│       ├── answer by type:  Number and Category as now
│       │                    Date: earliest, latest, counts per period   [new]
│       │                    Text, Identifier: distinct count, most common values  [new]
│       └── Sections:
│           ├── Chart options             [merged] from Advanced > Distribution Plots
│           │     Chart  [Number: histogram | box plot | violin plot · Category: bar chart]
│           │     Bins · Show smooth curve (density) · Show percentages · Orientation
│           │     Split into panels (facets): across · down
│           ├── Compare with a target     [merged] from Advanced > Means, Proportions
│           │     Number:   Target value · Alternative (as a sentence)
│           │               gives the interval and a one-sample t-test
│           │     Category: Which value counts · Target share
│           │               gives the interval and a one-sample proportion test
│           │               or Expected shares: goodness of fit
│           └── Checks   Is it bell-shaped? (normality, Shapiro-Wilk)  [moved] from Test
│
├── Relate
│   ├── Two Variables
│   │   ├── Outcome (Y) · For this analysis, treat as         [renamed]
│   │   ├── Predictor or group (X) · For this analysis, treat as  [renamed]
│   │   ├── Colour by (optional)  Columns: few-value
│   │   ├── button: Show                                      [renamed] from Answer
│   │   ├── answer by types: as now, and
│   │   │     date X: hands over to Over Time                 [new]
│   │   │     category Y, number X: says on screen that it is shown
│   │   │                           the other way round       [new]
│   │   └── Sections:
│   │       ├── [named for its chart], as now
│   │       ├── Chart options             [merged] from Advanced > Scatter, Group Plots
│   │       │     Chart  [number by category: box plot | violin plot |
│   │       │             bar chart of averages | individual points
│   │       │             · number by number: scatter | density (hexbin)]
│   │       │     Colour by · Marker shape by · Marker size by · Show trend line
│   │       │     Split into panels (facets): across · down
│   │       ├── How sure? Could this be chance?               [renamed] from Test
│   │       │     estimate and 95% interval, then the test,
│   │       │     named with the reason it was chosen         [new]
│   │       │     Test options  [merged] from Advanced > Means, Proportions, Correlation
│   │       │       Alternative (as a sentence)
│   │       │       · Rank-based version (Mann-Whitney U, Kruskal-Wallis H, Spearman)
│   │       │       · Which two groups to compare [new]
│   │       │       · Two-proportion test for a 2 by 2 table
│   │       │       · See it by shuffling [new]
│   │       ├── Checks   [moved] from Advanced: Assumption checks, Expected counts
│   │       └── Model: the same answer as an equation
│   │
│   ├── Over Time                             [moved] from Describe > Timeline, [renamed]
│   │   ├── Date  Columns: date, or text that looks like dates
│   │   ├── Value  Columns: number, plus Number of rows [new]
│   │   ├── Period  [As recorded | By day | By week | By month |
│   │   │            By quarter [new] | By year [new]]        [renamed] from Aggregation
│   │   ├── Summarise each period by  [sum | average (mean) | count]  [new]
│   │   ├── Colour by (optional)  Columns: few-value          [renamed] from Group By
│   │   ├── Chart  [line | area | bar]
│   │   ├── Moving average over (periods)  [0..30, 0 is off]  [renamed] from Rolling Window
│   │   └── button: Show
│   │
│   ├── Many Variables                        [moved] from Describe > Correlate, [renamed]
│   │   ├── Variables (multi)  Columns: number
│   │   ├── Chart  [Correlation matrix | Scatter plot matrix (pair plot)]  [renamed]
│   │   ├── Method  [Pearson (straight-line) | Spearman (rank order)]
│   │   ├── Hide correlations weaker than  [0..1, 0]          [renamed]
│   │   └── button: Show
│   │
│   └── Summary Table          [merged] from Group By / Summarize, Pivot, Cross-tab
│       ├── Rows (multi)  Columns: few-value; dates by period
│       ├── Columns (optional)  Columns: few-value
│       ├── Values (optional, multi)  Columns: all; none means count the rows
│       ├── Summarise by  [fits the value's type: count | average (mean) |
│       │                  middle value (median) | sum | min | max |
│       │                  standard deviation | distinct count]
│       ├── Show as  [values | % of row | % of column | % of total]
│       │            (only where it applies)
│       ├── Show totals (checkbox, on)                        [renamed] from Show Margins
│       ├── buttons: Show · Save as dataset [new]
│       └── Sections: Chart this table [bar | line | heat map] [new]
│                     · Could this be chance? (chi-square, for counts)
│
├── Model
│   ├── Fit                                   [merged] from Regression, Classify
│   │   ├── Purpose  [Explain (use every row) |
│   │   │             Predict (hold out rows for testing)]    [new]
│   │   ├── Outcome (Y)  Columns: number or category;
│   │   │                many-valued numbers only as numbers
│   │   ├── Predictors (X) (features) (multi)  Columns: number and category;
│   │   │                categories become 0/1 columns, reference category named  [new]
│   │   ├── Method, offered by the outcome's type:
│   │   │     number:    [Linear regression | Decision tree [new] | Random forest [new]]
│   │   │     category:  [Logistic regression | Decision tree | Random forest]
│   │   │     → Decision tree:  Maximum depth
│   │   │     → Random forest:  Number of trees · Maximum depth · No limit (checkbox)
│   │   ├── Model name (filled in; editable)                  [renamed] from Save Model As
│   │   ├── More options: Share of rows held out for testing [0.1..0.5, 0.3]
│   │   │                 · Random seed · Save train/test as datasets
│   │   ├── button: Fit
│   │   └── Sections: Do the predictors overlap? (multicollinearity, VIF)
│   │                 · Check the assumptions (residual plots)
│   │
│   ├── Evaluate
│   │   ├── Saved Model
│   │   ├── Evaluate On  [Test Set | Training Set]  (Test Set only if rows were held out)
│   │   ├── → two-class classifier: Cut-off for predicting the outcome (threshold) [0..1, 0.5]
│   │   ├── button: Evaluate
│   │   └── Sections (those that fit the model): ROC curve · Predicted vs actual · Residuals
│   │
│   ├── Predict
│   │   ├── Saved Model
│   │   ├── Data Source  [Training Set | Test Set | Loaded Dataset | Upload New CSV]
│   │   ├── Save Predictions As
│   │   └── buttons: Run Prediction
│   │                · Save predictions as a dataset          [renamed] from Save to Workbench
│   │
│   ├── Find Groups (clustering)              [renamed] from Cluster
│   │   ├── Method  [K-Means | Hierarchical]
│   │   ├── Variables (multi)  Columns: number; others greyed with the reason
│   │   ├── Standardise first (checkbox, on)                  [new]
│   │   ├── Number of groups (clusters)  [2..15, 3]
│   │   ├── buttons: Run · Add group as a column [new]
│   │   └── Sections: Cluster scatter plot · Choosing k (elbow plot)
│   │
│   └── Reduce Variables (PCA)                [renamed] from Reduce
│       ├── Variables (multi)  Columns: number
│       ├── Standardise first (checkbox, on)                  [new]
│       ├── buttons: Run · Add components as columns [new]
│       └── Sections: Component loadings · How many components? (scree plot) · Biplot
│
├── Report
│   ├── Report                                [renamed] from Report Builder
│   │   ├── Report Title · Author
│   │   ├── buttons: Start from outline (Question, Data, Findings, Recommendation) [new]
│   │   │            · Import from reusable steps · Run All Cells · Add Text · Clear
│   │   ├── Show Code (switch) · Preview
│   │   ├── Download as  [Web page (HTML) | Jupyter notebook | Report file (.json)]  [renamed]
│   │   ├── Load Report (.json)
│   │   └── each cell: as now
│   │
│   └── History                               [merged] from Notebook, Procedure
│       ├── every action of the session, in order
│       ├── Download as  [Web page (HTML) | Python script (.py) | Jupyter notebook (.ipynb)]
│       └── Reusable steps                                    [moved] from Procedure
│           ├── Name · Description
│           ├── buttons: Start Recording / Stop Recording · Build · Clear Steps
│           ├── Download (.json) · Load (.json)
│           └── Download Python · Download Jupyter            [removed]; History exports both
│
├── Learn                                     [moved] after Report
│   ├── Probability and Sampling              [renamed] from Simulate
│   │   ├── Simulation  [Distributions | Central Limit Theorem | Law of Large Numbers]
│   │   ├── Distribution  [Normal | Binomial | Poisson | Uniform | Exponential]
│   │   │     parameters: Mean (loc) · Standard deviation (scale) · Number of trials (n)
│   │   │                 · Chance of success (p) · Average count (mu)   [renamed]
│   │   ├── → Distributions:  Number of values to draw [renamed] from Sample Size
│   │   │                     · Probability Calculator, as now
│   │   ├── → Central Limit Theorem:  Size of each sample (n) · Number of samples (k)
│   │   ├── → Law of Large Numbers:   Max Observations
│   │   ├── Seed (optional) · button: Simulate
│   │   └── Sections: Goodness-of-fit tests
│   ├── Practice                              as now
│   └── Homework                              [moved] from the top level; controls as now
│
├── Advanced                                  [removed]; every option has a home above
└── AI Assistant                              [moved] to the header bar
```

## 7. Order of work

Three stages, each shippable alone. Stage 1 fixes 8 of the 13 high-severity findings without moving a panel.

### Stage 1: wording, filters, defaults

No learner's habit changes; every panel stays where it is.

- **Labels:** everything in section 5.
- **Types made visible (T4):** one shared type function and one shared picker with type icons, grouping, and greyed-with-reason. Then the picker fixes: T2, T5, T7, T8, T9, T10, T11, T13, T16, T17, and View's conditions by type (T6).
- **Category predictors in Regression and Classify (T1).** Medium effort, and the single most valuable change in this stage.
- **Defaults and dependent controls:** C1, C2, C3, C8, C9, C10, C11, C16, C17, L5.
- **Timeline's period and function (C6).**
- **Read the `menus` setting (S11).**
- **A More options link** from each guided answer to its Advanced panel, pre-filled with the same variables (the stopgap for S1).
- **Teaching wording:** L1, L2, L3.
- **Combine's description** cut back to what exists (S7).

Depends on: one type-detection function and one picker component used by every panel. If each panel builds its own picker today, build the shared one first; everything else in the stage hangs on it.

### Stage 2: move and merge panels

- Summary Table replaces Group By, Pivot and Cross-tab, with Chart this table (S2, C7).
- Correlate and Timeline move to Relate (S3, S4).
- View becomes browse only; Transform becomes Prepare with the column-first design; Overview shows and sets types (S5, S6, T3, T14, C14).
- One Variable gains Compare with a target and answers for dates and text (C5, T12).
- Report and History replace the three Report panels; the report outline arrives (S8, S13). Homework moves under Learn (S12). The Assistant becomes a drawer (S10).
- Smaller additions: cluster and component columns (C4), intervals in the test section (C12), Stack rows, Reshape and flexible keys (S7), paired comparison (C18), a bundled dataset with dates (C19), even common controls (C21).

Depends on: stage 1's names, so merged panels are born with their final labels; the type rule, which Summary Table and Prepare are built on; the `menus` setting, so an instructor mid-course can keep the old panels for a term; and aliases for old panel names wherever saved sessions, procedures, drills and homework files refer to them.

### Stage 3: rebuild on the grammar

- One chart component replaces the six chart builders.
- One test component replaces Means, Proportions, Correlation and both Test sections, and adds the shuffling view (L4).
- One model pipeline: Fit merges Regression and Classify, with preparation as visible parts (S9).
- Steps applied in Prepare (C13).
- Advanced is removed last (S1), after a checklist confirms each of its options is reachable from a guided answer: violin and strip plots, density curve, facets, marker shape and size, rank-based tests, one-sided alternatives, expected proportions, target mean.

Depends on: stage 1's role names, which become the components' slot names; stage 2's merges, which leave fewer callers to convert; and two checks on every component. The shown code must still be plain library code (principle 5), and the report must render through the same component as the screen (principle 4).

## 8. Open questions

The tree lists controls, not behaviour, so these could not be judged. Several findings (C2, C3, C12, C13, L2, L5) are conditional on the answers.

1. **Audience.** The tree file's header describes a first course for master's students in technology management; the prompt says high school to master's. Which governs the defaults?
2. **Overview.** What does Profile show today, and does it show each column's type?
3. **Changing data.** Do Apply in Transform and Apply to Dataset in View overwrite the active dataset or create a new one? Is there any undo?
4. **Saved models.** Is a fit saved when Save Model As is blank? What does Evaluate show when no rows were held out?
5. **Preparation inside models.** Do Cluster and Reduce standardise internally? How do models and tests treat rows with missing values?
6. **Regression output.** Does the answer show coefficients with p-values, and from which library? scikit-learn gives none, and statsmodels is not in the stated list.
7. **Tests.** Is the two-group t-test Welch or pooled? Do intervals appear anywhere?
8. **Dummy coding.** Is Drop first level on or off by default?
9. **Two Variables.** What happens with a date or a text column, given that Treat as offers only Number and Category?
10. **View filters.** Do several filters combine with and, or with or?
11. **Report paths.** Does Procedure replay on new data, and how does it differ from Notebook in practice? Do saved sessions, procedures, drills or homework files refer to panels by name?
12. **Signposts.** What do the signposts on Advanced panels say?
13. **Assistant.** What can it see (the dataset, the last result), and does Natural Language Query run code?
14. **Evaluate.** Do its three sections already adapt to the model's type?
15. **Live results.** Can panels update without a Run button in the app's framework at classroom dataset sizes? It would remove the refused-after-Run category entirely.

## 9. What works well

- **The layered answer in Two Variables:** sentence, table, chart, then Could this be chance?, then The same answer as an equation. That sequence is the grammar; the rest of the app should copy it.
- **Treat as** on the guided panels, which lets a 1 to 5 rating be read as a number and then as a category.
- **Section titles phrased as questions with the term in brackets:** Choosing k (elbow plot), How many components? (scree plot), Expected counts (if the variables were unrelated).
- **Which value counts as a success?** with the rarer of two as the default.
- **Convert Data Type refusing a conversion that would blank values,** and Combine asking what to do with each shared column.
- **Evaluate and Predict as separate steps** on saved models.
- **Show Code and Add to Report on every panel,** with real library code.
