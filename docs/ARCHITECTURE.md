# The Python Analytics Workbench
## Architecture & Development Plan

**Version:** 4.0  
**Author:** Ashish Khandelwal, University of Illinois at Urbana-Champaign  
**Date:** February 2026  
**Status:** Architecture & Planning

---

## 1. The Opportunity

### 1.1 The Gap

Radiant (Vincent Nijs, UCSD) proved that a browser-based analytics workbench can transform how business students learn data science. Built on R and Shiny, Radiant is structured as five R packages with a unified Shiny UI. It is widely used in business schools and is the de facto standard for no-code analytics education in the R ecosystem.

**There is no Python equivalent.**

Python dominates data science education and industry, but existing tools cover fragments — ydata-profiling for EDA, PyCaret for modeling, Sweetviz for reports — nothing integrates them into a pedagogically designed workbench. Jupyter notebooks break under classroom concurrency.

### 1.2 What Makes This Different

1. **Package-first.** `from workbench.explore import pivot` works in Jupyter, scripts, or the web UI. The UI is a layer, not the product.

2. **Show Code emits real pandas/sklearn.** Every UI action generates the equivalent pandas, matplotlib, or scikit-learn code — not workbench wrapper calls. Students graduate from point-and-click to programming with transferable skills.

3. **Homework inside the workbench.** Students load instructor-authored homework files, use the normal tools to find answers, and download a graded submission file. No accounts, no backend, no FERPA concerns. No analytics teaching tool has this.

4. **AI-augmented interpretation (Phase 4).** An embedded Socratic agent that challenges student interpretations rather than providing answers.

5. **Course-configurable.** Themes, bundled datasets, menu visibility, custom prompts — all via YAML. The workbench knows nothing about any specific course.

6. **Shinylive distribution.** Zero-server deployment via WebAssembly. Any instructor can try it without installing anything.

### 1.3 Publication Path

| Venue | Type | Timeline |
|-------|------|----------|
| **JOSS** (Journal of Open Source Software) | Software paper | After v1.0 stable |
| **JOSE** (Journal of Open Source Education) | Pedagogy paper | After one semester |
| **DSJ Innovative Education** | Empirical outcomes | After two semesters |

---

## 2. Technology Stack

### 2.1 Why Shiny for Python

An analytics workbench is stateful. A student loads datasets, merges tables, transforms columns, builds a pivot, then adjusts the visualization. Every step depends on the previous one.

**Streamlit** reruns the entire script on every widget interaction. State requires `st.session_state` hacks. Performance collapses under 50 concurrent users.

**Shiny for Python** maintains a reactive dependency graph. When the threshold slider changes, only threshold-dependent outputs recompute. This is the same framework Radiant uses (in R), proven for exactly this use case.

| Factor | Streamlit | Shiny for Python |
|--------|-----------|-----------------:|
| State model | Rerun everything | Reactive graph |
| Concurrent users | Poor | Good (async) |
| CSS/theming | Limited | Full Bootstrap |
| Zero-server | No | Shinylive (WASM) |
| Proof for this use case | None | **Radiant itself** |

**Why not Dash?** Callback-based — hundreds of explicit input→output wires for a complex workbench. Shiny infers the graph automatically.

**Why not Panel?** Viable but smaller community, no comparable success story.

### 2.2 Shiny APIs

**Core API** for the main shell (navbar, state, routing). **Express API** for simple individual pages. Both coexist naturally.

### 2.3 Shinylive: The Distribution Advantage

Compiles the entire app to WebAssembly, runs in the browser with zero server. An instructor at another university visits a URL and the workbench just works. No installation, no server costs, no IT department.

**Limitations:** Large datasets (>50MB) and heavy computation (model training) will be slow in-browser. Server deployment handles production classroom use. Shinylive is for try-before-you-install.

### 2.4 Deployment Options

| Option | Best For |
|--------|----------|
| **Server** (UIUC or AWS EC2 ~$30/mo) | Classroom with 50 students |
| **Shinylive** (static hosting, free) | Demos, workshops, adoption |
| **Docker** | Other institutions self-hosting |
| **pip install + local** | Package users, Jupyter integration |

### 2.5 Dependencies

```
# Core
pandas >= 2.0
numpy >= 1.24
matplotlib >= 3.7
seaborn >= 0.12
scipy >= 1.10
scikit-learn >= 1.3

# UI
shiny >= 1.0
htmltools >= 0.5

# AI (optional — Phase 4)
anthropic >= 0.20
# MCP server optional for external tool use

# Report (optional)
jinja2 >= 3.1
nbformat >= 5.9

# Testing
pytest >= 7.0
pytest-cov >= 4.0
playwright >= 1.40
```

---

## 3. Package Architecture

### 3.1 Structure

```
workbench/                          # Root package (name TBD, PyPI check needed)
│
├── core/
│   ├── state.py                    # Dataset store + operation history
│   ├── theme.py                    # Color palettes, plot defaults
│   ├── codegen.py                  # Emits raw pandas/matplotlib/sklearn code
│   ├── types.py                    # Smart column classification (numeric/categorical/datetime/id)
│   └── config.py                   # YAML course configuration loader
│
├── data/
│   ├── load.py                     # CSV, Excel, bundled datasets, URLs
│   ├── profile.py                  # Data quality: shape, dtypes, missing, duplicates, column stats
│   ├── view.py                     # Browse, search, filter, sort, sample
│   ├── transform.py                # Clean, convert, handle missing, outliers, new columns
│   ├── combine.py                  # Merge/join, append, reshape (wide↔long)
│   └── export.py                   # Save to CSV, Excel
│
├── explore/
│   ├── summarize.py                # Group-by aggregation with multiple functions
│   ├── pivot.py                    # Pivot tables with margins, %, formatting
│   └── crosstab.py                 # Cross-tabulation with chi-square, heatmap
│
├── visualize/
│   ├── distribute.py               # Univariate: histogram, box, violin, KDE, bar
│   ├── relate.py                   # Bivariate: scatter, hexbin, trend line, R²
│   ├── compare.py                  # Num×cat: grouped box, violin, bar of means, strip
│   ├── correlate.py                # Multivariate: correlation matrix, pair plot, facets
│   └── timeline.py                 # Time series: line, area, rolling avg, before/after
│
├── analyze/
│   ├── means.py                    # t-test, ANOVA (with assumption checks built in)
│   ├── proportions.py              # Chi-square test
│   └── correlation.py              # Pearson/Spearman significance, CI
│
├── model/
│   ├── regression.py               # Linear regression with interpretation
│   ├── classify.py                 # Logistic regression, decision trees
│   ├── evaluate.py                 # Confusion matrix, ROC, AUC, profit curves, fairness
│   ├── cluster.py                  # K-means, hierarchical, profiling
│   └── reduce.py                   # PCA, scree plot, loadings (exploratory, not predictive)
│
├── ai/                             # Phase 4
│   ├── interpret.py                # Plain-English interpretation (rule-based + LLM)
│   ├── suggest.py                  # Context-aware next-step recommendations
│   ├── challenge.py                # Socratic questioning based on current analysis
│   └── query.py                    # Natural language → pandas operation
│
├── homework/
│   ├── schema.py                   # YAML homework file validation
│   ├── loader.py                   # Parse homework file, present questions
│   ├── grader.py                   # Auto-grade numeric, MC, checkpoint questions
│   └── submission.py               # Generate downloadable submission file (JSON)
│
├── report/
│   ├── notebook.py                 # Append-only session log
│   └── export.py                   # HTML, Python script, Jupyter notebook
│
├── datasets/
│   ├── __init__.py                 # list_datasets(), load_dataset('jobmatch')
│   ├── jobmatch/                   # Recruiting simulation (4 tables)
│   ├── diamonds/                   # Classic (matches Radiant)
│   └── tips/                       # Simple starter
│
├── ui/
│   ├── app.py                      # Entry point: shiny run workbench/ui/app.py
│   ├── components/
│   │   ├── dataset_selector.py     # Global reactive dataset dropdown
│   │   ├── column_picker.py        # Smart selector (numeric vs categorical)
│   │   ├── code_panel.py           # "Show Code" expandable panel
│   │   ├── homework_panel.py       # Task panel for homework questions
│   │   └── chat_panel.py           # Phase 4: agent sidebar
│   └── modules/                    # One Shiny module per page
│       ├── data/                   # mod_load, mod_profile, mod_view, mod_transform, mod_combine, mod_export
│       ├── explore/                # mod_summarize, mod_pivot, mod_crosstab
│       ├── visualize/              # mod_distribute, mod_relate, mod_compare, mod_correlate, mod_timeline
│       ├── analyze/                # mod_means, mod_proportions, mod_correlation
│       ├── model/                  # mod_regression, mod_classify, mod_evaluate, mod_cluster, mod_reduce
│       ├── homework/               # mod_homework
│       ├── ai/                     # mod_assistant (Phase 4)
│       └── report/                 # mod_notebook
│
└── themes/
    ├── default.py                  # Colorblind-safe as default (accessibility first)
    ├── gies.py                     # Navy #13294B, Orange #E84A27
    └── minimal.py                  # Grayscale, print-friendly
```

### 3.2 Key Design Decisions

**Profile moved to Data.** Checking data quality is the first thing you do after loading. Having it under a separate menu forces unnecessary navigation. The workflow is now: Load → Profile → View → Transform → Combine.

**Normality folded into Means.** Normality testing is a diagnostic — you check assumptions before choosing a test. It's a panel within the means/ANOVA page, not a standalone destination.

**Reduce (PCA) stays in Model but is clearly labeled.** PCA is grouped with Cluster under Model because students encounter both post-midterm. But the UI and documentation frame it as "understand structure" not "predict." The Model menu is internally organized as Predict (Regression, Classify) | Evaluate | Understand (Cluster, Reduce).

**Relate and Correlate remain separate.** "Relate" is detailed investigation of two variables (scatter, trend line, residuals). "Correlate" is broad overview of many variables (matrix, pair plot). Different analytical purposes, different cognitive modes. The names could be improved — suggestions: "Scatter" and "Overview" — but the split is correct.

**Default theme is colorblind-safe.** Accessibility is the default, not an option. Branded themes (Gies, etc.) override colors but maintain accessibility structure (line styles, markers, patterns).

### 3.3 The Separation That Matters

Every UI module calls package functions. Package works without UI. UI works without understanding package internals.

```python
# In Jupyter — no UI, no Shiny, just the package:
from workbench.explore.pivot import create_pivot_table
import pandas as pd

events = pd.read_csv("events.csv")
result = create_pivot_table(events, "seniority", "event_type", "candidate_id", "count")
print(result)
```

```python
# In the Shiny UI — calls the same function:
@module.server
def pivot_server(input, output, session, get_current_df):

    @render.data_frame
    def pivot_result():
        df = get_current_df()
        return create_pivot_table(df, input.row_var(), input.col_var(),
                                  input.value_var(), input.agg())
```

### 3.4 Show Code: Emitting Real Pandas

This is a core design decision. "Show Code" generates the raw pandas/matplotlib/sklearn equivalent of every UI action — **not** workbench package calls.

```python
# When a student creates a pivot table in the UI, Show Code displays:

import pandas as pd

df = pd.merge(events, candidates, on="candidate_id", how="inner")
result = df.pivot_table(
    index="seniority",
    columns="event_type",
    values="candidate_id",
    aggfunc="count",
    margins=True
)
print(result)
```

Not: `from workbench.explore.pivot import create_pivot_table` — that teaches the workbench API, which is useless outside the workbench.

Implementation: each package function has a companion `_to_code()` method that returns the equivalent pandas string. The codegen module assembles these into a runnable script, tracking variable names and import statements.

```python
# workbench/core/codegen.py

class CodeGenerator:
    """Accumulates pandas/matplotlib/sklearn code for the entire session."""

    def __init__(self):
        self.imports: set[str] = {"import pandas as pd"}
        self.lines: list[str] = []
        self.var_names: dict[str, str] = {}  # dataset_name → variable_name

    def record(self, code: str, imports: list[str] | None = None):
        """Record a code snippet and any needed imports."""
        if imports:
            self.imports.update(imports)
        self.lines.append(code)

    def export_script(self) -> str:
        """Full runnable Python script."""
        header = sorted(self.imports)
        return "\n".join(header) + "\n\n" + "\n\n".join(self.lines)
```

### 3.5 State Management

The Shiny reactive graph owns which dataset is currently selected. The state object is a dumb store — it holds datasets and history, nothing else.

```python
# workbench/core/state.py

class WorkbenchState:
    """Stores loaded datasets and operation history. No UI logic."""

    datasets: dict[str, pd.DataFrame]       # {"candidates": df, "events": df, ...}
    originals: dict[str, pd.DataFrame]       # Untouched copies for "reset"
    history: list[Operation]                 # Append-only log
    codegen: CodeGenerator                   # Accumulates pandas code

    def load(self, name: str, df: pd.DataFrame): ...
    def get(self, name: str) -> pd.DataFrame: ...
    def update(self, name: str, df: pd.DataFrame, operation: Operation): ...
    def undo(self) -> None: ...
    def reset(self, name: str) -> None: ...
    def dataset_names(self) -> list[str]: ...
```

```python
# ui/app.py — Shiny owns the "current" selection

def server(input, output, session):
    state = WorkbenchState()

    # Reactive: which dataset is selected (Shiny manages this)
    @reactive.calc
    def current_df():
        return state.get(input.dataset())

    # Pass the reactive getter to all modules — they call current_df() when they need data
    mod_view.view_server("view", current_df)
    mod_pivot.pivot_server("pivot", current_df)
    # ...
```

No `state.current`. No mixing imperative and reactive paradigms.

### 3.6 Shiny Module Pattern

Every page follows the same pattern:

```python
@module.ui
def page_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            # Inputs: column selectors, options, toggles
        ),
        # Main: output table or chart
        # Code panel: "Show Code" expander (raw pandas)
    )

@module.server
def page_server(input, output, session, get_current_df):
    # 1. Update column choices when dataset changes
    # 2. Call package function with user inputs
    # 3. Render output
    # 4. Record equivalent pandas code
```

Once one module works, the pattern replicates across all ~20 pages.

### 3.7 Main Application Shell

```python
# ui/app.py

app_ui = ui.page_navbar(
    ui.nav_panel("Data",
        ui.navset_tab(
            ui.nav_panel("Load", mod_load.ui("load")),
            ui.nav_panel("Profile", mod_profile.ui("profile")),
            ui.nav_panel("View", mod_view.ui("view")),
            ui.nav_panel("Transform", mod_transform.ui("transform")),
            ui.nav_panel("Combine", mod_combine.ui("combine")),
            ui.nav_panel("Export", mod_export.ui("export")),
        )
    ),
    ui.nav_panel("Explore",
        ui.navset_tab(
            ui.nav_panel("Summarize", mod_summarize.ui("summarize")),
            ui.nav_panel("Pivot", mod_pivot.ui("pivot")),
            ui.nav_panel("Cross-tab", mod_crosstab.ui("crosstab")),
        )
    ),
    ui.nav_panel("Visualize", ...),
    ui.nav_panel("Analyze", ...),
    ui.nav_panel("Model", ...),
    ui.nav_panel("Homework", mod_homework.ui("hw")),  # visible when homework loaded
    ui.nav_panel("Report", ...),

    header=dataset_selector_ui("ds"),
    title="Analytics Workbench",
)
```

---

## 4. Menu Organization & Page Specifications

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ANALYTICAL WORKFLOW                             │
│                                                                     │
│  DATA           EXPLORE        VISUALIZE      ANALYZE      MODEL    │
│  ────           ───────        ─────────      ───────      ─────    │
│  "Get it        "Aggregate     "Show me       "Is this     "Predict │
│   ready"         & compare"     patterns"      real?"       & understand"│
│                                                                     │
│  Load           Summarize      Distribute     Means        ┌Predict─┐│
│  Profile        Pivot          Relate         Proportions  │Regression││
│  View           Cross-tab      Compare        Correlation  │Classify ││
│  Transform                     Correlate                   ├Evaluate─┤│
│  Combine                       Timeline                    │Evaluate ││
│  Export                                                    ├Understand┤│
│                                                            │Cluster  ││
│                                                            │Reduce   ││
│                                                            └─────────┘│
│                                                                     │
│  + HOMEWORK (visible when homework file loaded)                     │
│  + AI (Phase 4: Socratic agent as chat sidebar)                     │
│  + REPORT (accumulates throughout)                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.1 DATA — "Get it ready"

#### Data > Load
- Radio: Bundled Datasets / Upload File (.csv, .xlsx, .tsv) / From URL
- Bundled datasets from config (e.g., ☑ candidates ☑ jobs ☑ companies ☑ events)
- On load: shape, column names, dtypes, first 5 rows, memory usage
- **Show Code:** `candidates = pd.read_csv('candidates.csv')`

#### Data > Profile
- **Overview:** Shape, dtypes, memory; per-column: type, non-null %, unique count, sample values
- **Quality flags:** Missing values (sorted desc), duplicates, constant columns, potential IDs, type mismatches
- **Column deep dive:** Click any column → numeric: full stats + histogram; categorical: value counts + bar; datetime: range + distribution
- This is the first stop after loading. "What do I actually have?"

#### Data > View
- Filter: column → condition (=, ≠, >, <, between, in, contains, is null) → value
- Multi-filter with AND/OR
- Sort: up to 3 levels
- "Apply filter to dataset" vs "Preview only"
- **Show Code:** `df = df[df['salary'] > 50000].sort_values('name')`

#### Data > Transform
Sub-tabs: Missing Values · Data Types · Duplicates · Outliers · String Ops · New Column

Each sub-tab: select column(s) → choose action → preview before/after → apply.

**New Column** supports: arithmetic, conditional (if/else), date extraction, binning, rank, lag/lead, cumulative, concat, log/sqrt/z-score/normalize.

**Show Code:** `df['salary_log'] = np.log(df['salary'])`

#### Data > Combine
Sub-tabs: Merge/Join · Append · Reshape

**Merge:** Left table → right table → key column(s) → join type → result shape, unmatched counts, preview. This is where most data problems reveal themselves.

**Show Code:** `merged = pd.merge(events, candidates, on='candidate_id', how='inner')`

#### Data > Export
Dataset selector, format (CSV, Excel), download.

---

### 4.2 EXPLORE — "Aggregate & compare"

#### Explore > Summarize
Group by 1-2 columns, select value columns, choose aggregation functions (count, sum, mean, median, min, max, std, nunique). % of total option. Sortable result table.

**Show Code:** `df.groupby('seniority')['salary'].agg(['mean', 'median', 'count'])`

#### Explore > Pivot
Row variable(s), column variable, value, aggregation. Display: raw / % of row / % of column / % of total. Margins (none/row/col/both). Conditional formatting (gradient).

**Show Code:** `pd.pivot_table(df, index='seniority', columns='event_type', values='candidate_id', aggfunc='count', margins=True)`

#### Explore > Cross-tab
Two categorical variables. Display: counts, row %, col %, total %. Chi-square test with plain English interpretation. Optional heatmap.

**Show Code:** `pd.crosstab(df['seniority'], df['industry'], margins=True, normalize='index')`

---

### 4.3 VISUALIZE — "Show me patterns"

Every visualization page has:
- Column selectors appropriate to the chart type
- Gies/default/colorblind palette
- Download button (PNG, SVG)
- **Show Code** emitting matplotlib/seaborn

#### Visualize > Distribute — "What does ONE variable look like?"
Numeric: histogram (bins slider), box, violin, KDE; mean/median reference lines.
Categorical: bar (horizontal/vertical, sorted), pie/donut; counts or %.

#### Visualize > Relate — "How do TWO numeric variables relate?"
Scatter (default), hexbin for large data. Trend line with R² and correlation. Optional: color by categorical, size by numeric.

#### Visualize > Compare — "How does a numeric differ across groups?"
Box (default), violin, bar of means with error bars, strip plot. Sort by mean/median. Summary statistics table below chart.

#### Visualize > Correlate — "Patterns across MANY variables?"
Correlation matrix (Pearson/Spearman, upper triangle, |r| threshold filter). Pair plot (up to 6 columns, color by categorical). Faceted small multiples.

#### Visualize > Timeline — "How does something change over time?"
Datetime × numeric, optional group-by. Aggregation level (raw/hourly/daily/weekly/monthly). Line/area/bar. Rolling average overlay. Before/after split line.

---

### 4.4 ANALYZE — "Is this real?"

Every analysis page shows: test statistic, p-value, confidence interval, effect size, plain English interpretation, and assumption checks.

#### Analyze > Means
- One-sample t-test, two-sample t-test, one-way ANOVA
- **Built-in assumption panel:** normality check (Shapiro-Wilk, QQ plot), homogeneity of variance (Levene's). If assumptions violated, suggests non-parametric alternative
- English: "The mean salary for Senior ($85,200) is significantly higher than for Entry ($52,400), t(1842) = 12.3, p < .001, d = 0.74"

#### Analyze > Proportions
- Chi-square test of independence
- Expected frequencies, standardized residuals
- English: "There is a significant association between seniority level and industry, χ²(8) = 42.3, p < .001"

#### Analyze > Correlation
- Pearson r, Spearman ρ, with p-value and 95% CI
- Scatter + trend line visualization
- English: "Moderate positive correlation (r = 0.42, p < .001). Correlation does not imply causation."

---

### 4.5 MODEL — "Predict & understand"

Model menu is organized into three sections:

**Predict:**

#### Model > Regression
Linear regression. Coefficient table with interpretation. Diagnostics: residual plot, QQ, leverage/influence. VIF for multicollinearity. Train/test split option.
English: "A one-unit increase in experience is associated with a $2,340 increase in salary, holding other variables constant."

#### Model > Classify
Logistic regression / decision tree. Threshold slider with live confusion matrix update. Cost-sensitive evaluation. ROC curve, precision-recall curve, lift chart.

**Evaluate:**

#### Model > Evaluate
Unified evaluation page. Confusion matrix, accuracy/precision/recall/F1, AUC. Business metrics: profit curve, expected value calculation. Fairness metrics: demographic parity, equalized odds, disparate impact ratio.

**Understand:**

#### Model > Cluster
K-means with elbow plot and silhouette scores. Cluster profiling: mean/mode of each variable by cluster. Visualization: scatter colored by cluster, radar/parallel coordinates.
Note in UI: "Clusters are analytical conveniences, not fixed types in reality."

#### Model > Reduce
PCA. Scree plot with cumulative variance explained. Loadings table and biplot. Recommendation for number of components.
Note in UI: "PCA reveals structure in your data. It's exploratory — not predictive."

---

## 5. Homework Module

### 5.1 Design Philosophy

No accounts. No backend. No FERPA concerns. The workbench is client-side software. Canvas handles identity and grades.

### 5.2 Workflow

**Instructor:**
1. Authors a homework YAML file with questions tied to a dataset
2. Posts it on Canvas as a downloadable file
3. Creates a Canvas assignment with file upload submission

**Student:**
1. Opens the workbench, loads the homework YAML (like loading a dataset — just a file input)
2. Homework panel appears with questions and a task list
3. Uses normal workbench tools (Data, Explore, Visualize, Analyze, Model) to find answers
4. Types answers into the homework panel
5. Sees instant feedback on auto-graded questions (numeric, multiple choice)
6. Clicks "Download Submission" → gets a JSON file
7. Uploads that file to Canvas

### 5.3 Homework YAML Format

```yaml
# hw1_data_exploration.yaml
title: "Homework 1: Data Exploration"
dataset: "jobmatch"          # must match a bundled or loadable dataset
version: 1                   # increment to invalidate old submissions

questions:
  - id: q1
    text: "How many unique candidates are in the dataset?"
    type: numeric
    answer_hash: "a9f51566bd6705f7ea6ad54bb9deb449"   # sha256 of "5000"
    tolerance: 0
    points: 5
    hint: "Use the Profile page on the candidates table."

  - id: q2
    text: "What is the overall offer acceptance rate (as a decimal, e.g. 0.42)?"
    type: numeric
    answer_hash: "e4d909c290d0fb1ca068ffaddf22cbd0"
    tolerance: 0.01
    points: 10

  - id: q3
    text: "Which industry has the most job postings?"
    type: multiple_choice
    options: ["Technology", "Healthcare", "Finance", "Retail", "Manufacturing"]
    answer_hash: "d2d2d2..."
    points: 10

  - id: q4
    text: "Merge events with candidates. How many rows in the result?"
    type: checkpoint          # validates student performed the operation
    answer_hash: "..."
    tolerance: 0
    points: 5

  - id: q5
    text: >
      Create a pivot table of event_type × seniority (column %).
      Which seniority level has the highest application rate relative
      to their representation? Explain what this means for recruiting.
    type: free_response
    points: 20
    rubric: "Identifies correct group (5pts), explains business implication (10pts), notes limitations (5pts)"

  - id: q6
    text: "Create a visualization showing the salary distribution by seniority. Download and describe what you see."
    type: free_response
    points: 15
    rubric: "Appropriate chart type (5pts), correct interpretation (5pts), discusses spread not just center (5pts)"
```

**Answer security:** Answers are stored as hashes (SHA-256). The grader hashes the student's input and compares. Students cannot reverse-engineer answers from the YAML file. For numeric answers with tolerance, the grader checks a range of values against the hash. For multiple choice, each option is hashed and compared.

### 5.4 Submission File

```json
{
  "homework_id": "hw1_data_exploration",
  "homework_version": 1,
  "submitted_at": "2026-01-27T14:32:00",
  "student_name": "self-reported",

  "answers": [
    {"id": "q1", "response": 5000, "auto_score": 5, "max": 5},
    {"id": "q2", "response": 0.43, "auto_score": 10, "max": 10},
    {"id": "q3", "response": "Technology", "auto_score": 10, "max": 10},
    {"id": "q4", "response": 198432, "auto_score": 5, "max": 5},
    {"id": "q5", "response": "Entry-level candidates have the highest...", "auto_score": null, "max": 20},
    {"id": "q6", "response": "The box plot shows that Senior roles...", "auto_score": null, "max": 15}
  ],

  "auto_total": 30,
  "auto_max": 30,
  "pending_review": 35,
  "grand_max": 65,

  "session_log": [
    {"step": 1, "time": "14:02", "action": "load", "dataset": "candidates", "rows": 5000},
    {"step": 2, "time": "14:03", "action": "profile", "dataset": "candidates"},
    {"step": 3, "time": "14:05", "action": "load", "dataset": "events", "rows": 198432},
    {"step": 4, "time": "14:08", "action": "merge", "left": "events", "right": "candidates", "on": "candidate_id", "result_rows": 198432},
    {"step": 5, "time": "14:12", "action": "pivot", "rows": "event_type", "cols": "seniority", "agg": "count"},
    {"step": 6, "time": "14:18", "action": "visualize.compare", "x": "seniority", "y": "salary", "chart": "box"}
  ]
}
```

The student sees their auto-graded score before downloading. Free-response and visualization questions show "Pending instructor review." They know where they stand.

The instructor downloads all submissions from Canvas. The session log is there to see HOW the student worked, but grading can focus on just the answers.

### 5.5 Architecture

```
workbench/homework/
├── schema.py          # Validate YAML structure, supported question types
├── loader.py          # Parse YAML, present questions to UI
├── grader.py          # Hash student answer → compare to answer_hash
└── submission.py      # Assemble answers + session log → downloadable JSON
```

No server component. No database. No Canvas API integration (v1). The submission file is just a file on the student's computer until they upload it to Canvas themselves.

---

## 6. Course Configuration

The workbench ships with a default configuration. Instructors can override it with a YAML file.

### 6.1 Default Configuration (no course, self-learner or general user)

```yaml
# default_config.yaml — ships with the package
theme: "default"             # colorblind-safe palette

menus:
  data: true
  explore: true
  visualize: true
  analyze: true
  model: true
  homework: true             # visible when homework file loaded
  ai: false                  # Phase 4
  report: true

prompts:
  enabled: false             # no pedagogical prompts for general users

datasets:
  bundled: ["diamonds", "tips"]
```

### 6.2 Course Configuration Example

```yaml
# course_config.yaml — instructor creates this for their course

course:
  name: "BADM 576 — Data Science and Analytics"
  institution: "University of Illinois at Urbana-Champaign"

theme: "gies"

datasets:
  bundled: ["jobmatch"]

menus:
  data: true
  explore: true
  visualize: {visible: true, after_date: "2026-01-29"}    # date-based, not week-based
  analyze: {visible: true, after_date: "2026-02-05"}
  model: {visible: true, after_date: "2026-03-12"}        # post-midterm
  homework: true
  ai: false
  report: true

prompts:
  enabled: true
  # Custom prompts triggered by specific actions
  custom:
    - trigger: "merge_completed"
      text: "Check the row count. Did it increase? Decrease? Stay the same? Why?"
      show_once: true
    - trigger: "pivot_created"
      text: "Read across rows first, then down columns. Where are the surprises?"
      show_once: true
    - trigger: "mean_calculated"
      text: "The mean tells you the center. What does the spread look like?"
      show_once: true

ai:
  provider: "anthropic"
  mode: "socratic"
```

Key differences: date-based visibility (not week numbers), prompts fire once then retire, general users get no prompts.

---

## 7. The AI Agent (Phase 4)

### 7.1 Design Principle

**UI for action.** Students make analytical choices — which dataset, which columns, which test. The menu structure scaffolds thinking.

**Agent for challenge.** After the student creates output, the agent asks the question they haven't thought to ask. Like a great TA, at scale.

### 7.2 Architecture

The agent runs in the same Python process as the Shiny app. It calls package functions directly — no MCP overhead for the embedded use case.

```
Student uses Shiny UI → creates output
    ↓
Agent receives: current output + session history + course context
    ↓
Agent responds: question, interpretation, or next-step suggestion
    ↓
Displayed in chat sidebar
```

MCP server is an optional, separate interface for external tools (Claude Desktop, Claude Code) to interact with the workbench. It's not needed for the embedded agent.

### 7.3 What the Agent Does

1. **Challenges assumptions:** "You filtered out records with missing salaries. That's 23% of the data. Who are those people? Is the missingness random?"

2. **Connects to concepts:** "You're looking at averages across groups. But last week you saw how averages can mislead — what does the distribution within each group look like?"

3. **Suggests next steps:** "You've found that salary and experience correlate. Before concluding experience causes higher salary — what other variables might explain both?"

4. **Interprets on demand:** Student clicks "Explain this" → plain-English interpretation calibrated to their level.

5. **Refuses to shortcut:** "I can help you think through it, but you need to make the analytical choices. What question are you trying to answer?"

### 7.4 Cost & Fallback

Claude Sonnet: ~$5-15 per class session (50 students × ~20 short interactions). ~$150-500/semester. If context is heavy (full DataFrame descriptions), costs may be 2-3x higher — manage by sending column summaries, not raw data.

Rule-based fallback works fully without an API key: static interpretations of test results, basic "did you check..." prompts, standard coefficient explanations.

---

## 8. Development Plan

### 8.1 Phases & Milestones

Development time is in **effort-hours**, not calendar weeks. A faculty member building with Claude Code might do 10-15 productive hours per week during breaks, less during the semester.

#### Phase 1: Core + Data (~40-60 hours)
*Milestone: Load all 4 JobMatch tables, profile, view, filter, merge, export.*

1. `core/state.py`, `core/types.py`, `core/theme.py`
2. `data/` — all 6 modules
3. `ui/app.py` — main shell with navbar and dataset selector
4. `ui/components/` — dataset_selector, column_picker, code_panel
5. `ui/modules/data/` — all 6 Shiny modules
6. Tests: load, merge, transform roundtrips

#### Phase 2: Explore + Visualize (~30-40 hours)
*Milestone: Summarize, pivot, cross-tab, all 5 chart types, code export.*

1. `explore/` — 3 modules
2. `visualize/` — 5 modules
3. `core/codegen.py` — pandas code generation for all operations so far
4. `ui/modules/explore/` and `ui/modules/visualize/`

#### Phase 3: Analyze + Model (~30-40 hours)
*Milestone: t-tests, chi-square, correlation, regression, classification, clustering, PCA, evaluation.*

1. `analyze/` — 3 modules
2. `model/` — 5 modules
3. `ui/modules/analyze/` and `ui/modules/model/`
4. Course config system (date-based menu visibility)

#### Phase 4: Homework + Report (~20-30 hours)
*Milestone: Instructor authors YAML, student completes and downloads graded submission.*

1. `homework/` — schema, loader, grader, submission
2. `ui/components/homework_panel.py`
3. `ui/modules/homework/`
4. `report/` — session log, export (script, notebook, HTML)

#### Phase 5: AI Agent + Polish (~20-30 hours)
*Milestone: Socratic agent in chat sidebar, rule-based fallback, LLM enhancement.*

1. `ai/` — interpret, suggest, challenge, query
2. `ui/components/chat_panel.py`
3. Theme polish, config loader, prompts system
4. Feature-complete v1.0

#### Phase 6: Package + Publish (~20-30 hours)
*Milestone: `pip install [name]` → `[name] launch` → workbench running.*

1. `pyproject.toml`, entry points, `__init__.py` files
2. Documentation (mkdocs)
3. CI/CD (GitHub Actions)
4. PyPI release, Shinylive build, Docker image
5. JOSS paper draft

**Total estimate: 160-230 hours.** At 15 hours/week, that's 11-16 weeks of focused development. Realistic for a summer build with Claude Code assistance.

### 8.2 What Claude Code Can Build

**Confidently:** All package functions, Shiny modules (templated), state management, codegen, unit tests, packaging.

**Needs human guidance:** AI prompt engineering, UX defaults (what feels right for students), visual polish, deployment configuration.

**Cannot do:** Classroom testing, concurrent load testing, student UX pilot.

### 8.3 Testing Strategy

| Layer | What | Tool |
|-------|------|------|
| **Unit** | Each function in data/, explore/, etc. | pytest |
| **Integration** | Full workflows: load → merge → pivot → chart | pytest + fixtures |
| **Data validation** | JobMatch checklist (15 items) | pytest parametrized |
| **UI smoke** | Each Shiny module loads without error | playwright |
| **Load** | 50 concurrent users | locust |
| **UX pilot** | 3-5 students before semester starts | Manual |

---

## 9. Decisions Needed Before Building

| Decision | Options | Recommendation |
|----------|---------|----------------|
| **Package name** | Check PyPI availability | TBD — need to search |
| **AI provider** | Anthropic / OpenAI / both | Anthropic (natural fit, MCP ecosystem) |
| **License** | AGPLv3 / MIT / Apache 2.0 | MIT (easiest adoption) |
| **Hosting Spring 2026** | UIUC server / AWS EC2 | AWS EC2 (reliable, ~$30/mo) |
| **v1 scope** | Phases 1-4 (core + homework) / Phase 5 (agent) later? | Ship 1-4 for class, agent as v1.1 |
| **Homework answer format** | Hashed answers in YAML / separate answer file | Hashed (single file simpler) |

---

## 10. Maintenance Model

**During semester:** Mostly ignore GitHub. Critical bugs: 30-minute fix with Claude Code.

**During breaks:** Batch-process issues. 20 issues ≈ one day with Claude Code.

**Annual investment:** 3-5 days/year, batched into breaks.

**Design for low maintenance:** Small dependency surface (pandas, matplotlib, scipy, scikit-learn, shiny — all stable). Pin versions. 200+ tests + CI. Set expectations in README: "Maintained by a faculty member. Response times may be slow during semester. PRs welcome."

**The real risk:** Not lack of maintenance — it's a core dependency making a breaking change. Mitigate by pinning versions and upgrading deliberately.
