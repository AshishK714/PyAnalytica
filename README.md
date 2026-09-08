<div align="center">

# PyAnalytica

**A Python analytics workbench for teaching data science**

[![Python](https://img.shields.io/badge/python-%3E%3D3.10-3776ab?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.7.2-667eea.svg)](https://pypi.org/project/pyanalytica/)
[![Shiny](https://img.shields.io/badge/built%20with-Shiny%20for%20Python-764ba2.svg)](https://shiny.posit.co/py/)
[![Tests](https://img.shields.io/badge/tests-901%20passing-22c55e.svg)]()

*Interactive data exploration, visualization, statistical analysis, and machine learning — with a "Show Code" button that reveals the pandas & sklearn code behind every operation.*

</div>

---

## Feature Highlights

| Category | Capabilities |
|----------|-------------|
| **Data** | Load CSV/Excel/bundled datasets, profile columns, view/filter, transform (rename, retype, compute, filter, fill missing, sample), combine (merge/concat), export |
| **Explore** | Group-by summarize with percent-of-total, pivot tables, cross-tabulation with chi-squared |
| **Visualize** | Histograms, density, box/violin, scatter, line, bar, heatmap correlation, timeline |
| **Analyze** | Independent & paired t-tests, one-way ANOVA, proportion z-tests, chi-squared, Pearson/Spearman correlation |
| **Model** | Linear & logistic regression, k-NN/SVM/tree/random-forest classification, k-means/hierarchical clustering, PCA, model evaluation, saved-model prediction |
| **Homework** | YAML-based assignments with hash-checked answers, automatic grading, submission export |
| **Report** | Export analyses as HTML reports, Python scripts, or Jupyter notebooks |
| **AI** | Rule-based + optional LLM interpretation, next-step suggestions, challenge questions, natural-language data queries |
| **Workflow** | Procedure builder to record, replay, annotate, and export multi-step analysis pipelines |

---

<details>
<summary><strong>Screenshots</strong></summary>

> Screenshots coming soon. The app features a modern gradient + glassmorphism UI with:
> - Indigo-to-purple gradient navbar
> - Glassmorphism panels with frosted-glass effect
> - Clean data grids with gradient headers
> - Dark-themed "Show Code" panels
> - Polished form controls with accent focus rings

</details>

---

## Quick Start

### Launch the interactive workbench

```bash
pyanalytica                # CLI entry point (after pip install)
python -m pyanalytica      # or run as a module
```

### Use as a Python library

Every analytics function returns a `(result, CodeSnippet)` tuple. The `CodeSnippet` contains the equivalent pandas/sklearn code so students can see what runs under the hood.

```python
from pyanalytica.data.load import load_bundled
from pyanalytica.data.profile import profile_dataframe
from pyanalytica.visualize.distribute import histogram
from pyanalytica.visualize.relate import scatter
from pyanalytica.explore.summarize import group_summarize

# Load a bundled dataset
df, code = load_bundled("tips")

# Profile the dataframe — column types, missing values, summary stats
profile = profile_dataframe(df)

# Visualize
fig, code = histogram(df, "total_bill", bins=20)
fig, code = scatter(df, x="total_bill", y="tip", color_by="smoker")

# Summarize — group_cols, value_cols, agg_funcs are all lists
result, code = group_summarize(
    df,
    group_cols=["day"],
    value_cols=["tip"],
    agg_funcs=["mean"],
)
```

---

## The CodeSnippet Pattern

Every analytics function in PyAnalytica returns a tuple of `(result, CodeSnippet)`. The `CodeSnippet` dataclass holds the equivalent pandas/sklearn code so students can learn what happens behind the UI:

```python
from pyanalytica.core.codegen import CodeSnippet

# CodeSnippet(code="df.groupby(['day'])['tip'].mean()", imports=["import pandas as pd"])

# In the Shiny UI, the "Show Code" button renders this as a copyable code block.
# The emitted code uses real pandas/sklearn calls — never wrapper functions.
```

---

## Installation

```bash
# Core package (Shiny UI + all analytics)
pip install pyanalytica

# With AI integration (Anthropic Claude)
pip install "pyanalytica[ai]"

# With Jupyter notebook export
pip install "pyanalytica[report]"

# Everything (recommended)
pip install "pyanalytica[all]"
```

To update to the latest version:

```bash
pip install --upgrade pyanalytica
```

> **Switching from a GitHub install?** Run `pip uninstall pyanalytica` first, then install from PyPI above.

### Install from source (for development)

```bash
git clone https://github.com/social-engineer-ai/PyAnalytica.git
cd PyAnalytica
pip install -e ".[dev,all]"
```

---

## Bundled Datasets

| Name | Rows | Columns | Description |
|------|------|---------|-------------|
| `tips` | 244 | 7 | Restaurant tipping data (total_bill, tip, sex, smoker, day, time, size) |
| `diamonds` | 53,940 | 10 | Prices and attributes of round-cut diamonds |
| `candidates` | 5,000 | 12 | JobMatch simulation — job candidates with skills and experience |
| `jobs` | 500 | 10 | JobMatch simulation — job postings |
| `companies` | 200 | 8 | JobMatch simulation — companies |
| `events` | 15,000 | 6 | JobMatch simulation — recruiting events (applications, interviews, offers) |

```python
from pyanalytica.datasets import list_datasets, load_dataset

list_datasets()          # ['candidates', 'companies', 'diamonds', 'events', 'jobs', 'tips']
df = load_dataset("diamonds")
```

To regenerate bundled datasets:

```bash
PYTHONPATH=src python -m pyanalytica.datasets.generate
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Shiny for Python UI                   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Modules: mod_load, mod_profile, mod_view, ...   │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │  Components: dataset_selector, code_panel,       │   │
│  │  decimals_control, chat_panel, download_result   │   │
│  └──────────────┬───────────────────────────────────┘   │
├─────────────────┼───────────────────────────────────────┤
│                 │      Analytics Packages                │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │  data/   explore/   visualize/   analyze/        │   │
│  │  model/  homework/  report/      ai/             │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │  Core: codegen, state, config, theme, profile,   │   │
│  │  model_store, procedure, session, column_utils   │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

The architecture follows a **package-first** design:
- **Core** provides shared utilities (CodeSnippet generation, state management, configuration)
- **Analytics packages** (`data/`, `explore/`, `visualize/`, `analyze/`, `model/`) contain pure functions that work independently of any UI
- **UI modules** in `ui/modules/` call analytics functions and handle Shiny reactivity
- `WorkbenchState` is a simple data store; the Shiny reactive graph manages the current selection

---

## Configuration

### User Profile

PyAnalytica reads user preferences from `~/.pyanalytica/profile.yaml` (auto-created on first use):

```yaml
# ~/.pyanalytica/profile.yaml
api_key: ""          # Anthropic API key for AI features
decimals: 3          # Default decimal places for numeric output
theme: default       # UI theme

# Instructor fields (optional)
instructor_name: ""
institution: ""
course: ""
```

**Precedence:** Environment variable > profile.yaml > built-in default

| Setting | Env Variable | Default |
|---------|-------------|---------|
| API key | `ANTHROPIC_API_KEY` | (none) |
| Decimals | `PYANALYTICA_DECIMALS` | 3 |
| Theme | `PYANALYTICA_THEME` | default |

### Course Configuration

Instructors can place a `pyanalytica.yaml` in the working directory to control which menu items are visible (with optional date-gating):

```yaml
menus:
  - name: Data
    visible: true
  - name: Model
    visible: true
    after: "2025-02-15"   # Only show after this date
  - name: Homework
    visible: true
```

---

<details>
<summary><strong>For Instructors</strong></summary>

### Homework Framework

Create YAML-based assignments with hash-checked answers:

```yaml
# homework1.yaml
title: "Homework 1: Exploratory Data Analysis"
dataset: tips
due_date: "2025-03-01"
questions:
  - id: q1
    type: numeric
    prompt: "What is the mean total bill?"
    answer_hash: "sha256:..."    # Hash of the correct answer
    tolerance: 0.01
  - id: q2
    type: multiple_choice
    prompt: "Which day has the highest average tip?"
    choices: ["Thur", "Fri", "Sat", "Sun"]
    answer_hash: "sha256:..."
  - id: q3
    type: dataframe
    prompt: "Create a summary table of mean tip by day"
    answer_hash: "sha256:..."
```

**Question types:** `numeric`, `multiple_choice`, `text`, `dataframe`

Generate answer hashes:

```python
from pyanalytica.homework.schema import hash_answer
hash_answer(19.7859)    # 'sha256:...'
hash_answer("Sun")      # 'sha256:...'
```

Students complete assignments in the Homework tab and export submissions as JSON files for grading.

</details>

---

## AI Features

PyAnalytica includes four AI-powered modules that work in **rule-based mode** by default and can be enhanced with an Anthropic API key:

| Module | Rule-based | LLM-enhanced |
|--------|-----------|-------------|
| **Interpret** | Template-based statistical interpretation of results | Claude provides nuanced, context-aware explanations |
| **Suggest** | Heuristic next-step recommendations based on data types | Claude suggests analyses tailored to the specific dataset |
| **Challenge** | Pre-written critical thinking questions | Claude generates Socratic questions about the analysis |
| **Query** | Keyword-based column/operation matching | Claude translates natural language to pandas code |

Set your API key via environment variable or user profile:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Procedure Builder & Reports

### Recording workflows

The Procedure Builder records every analytics operation as a reproducible step:

1. Click **Start Recording** in the Report > Procedure tab
2. Perform your analysis (load data, transform, visualize, model, etc.)
3. Each step is captured with its code snippet and can be annotated with comments
4. **Stop Recording** when done

### Export formats

| Format | Description |
|--------|-------------|
| **JSON** | Full roundtrip format — reload procedures later |
| **Python script** | Standalone `.py` file with all imports and code |
| **Jupyter notebook** | `.ipynb` with markdown headers and code cells |
| **HTML report** | Rendered HTML with results and visualizations |

```python
from pyanalytica.core.procedure import Procedure

proc = Procedure.from_json("my_analysis.json")
proc.to_python("my_analysis.py")
proc.to_notebook("my_analysis.ipynb")
```

---

## Development

### Setup

```bash
git clone https://github.com/social-engineer-ai/PyAnalytica.git
cd PyAnalytica
pip install -e ".[dev,all]"

# Generate bundled datasets
PYTHONPATH=src python -m pyanalytica.datasets.generate
```

### Run tests

```bash
PYTHONPATH=src python -m pytest tests/ -v
```

### Build

```bash
pip install build
python -m build
```

### Project structure

```
PyAnalytica/
├── src/pyanalytica/
│   ├── __init__.py              # Package version
│   ├── __main__.py              # python -m pyanalytica entry
│   ├── core/                    # Shared utilities
│   │   ├── codegen.py           # CodeSnippet + on_record hook
│   │   ├── column_utils.py      # ColumnType classification
│   │   ├── config.py            # CourseConfig + menu visibility
│   │   ├── model_store.py       # ModelArtifact + ModelStore
│   │   ├── procedure.py         # ProcedureStep / Procedure / Recorder
│   │   ├── profile.py           # UserProfile + get_api_key()
│   │   ├── session.py           # Session save / load / list
│   │   ├── state.py             # WorkbenchState
│   │   └── theme.py             # Theme management
│   ├── data/                    # Load, profile, transform, combine, export
│   ├── explore/                 # Summarize, pivot, crosstab
│   ├── visualize/               # Distribute, relate, compare, correlate, timeline
│   ├── analyze/                 # Means, proportions, correlation
│   ├── model/                   # Regression, classify, cluster, reduce, evaluate, predict
│   ├── homework/                # Schema, loader, grader, submission
│   ├── report/                  # Notebook + export
│   ├── ai/                      # Interpret, suggest, challenge, query
│   ├── datasets/                # Bundled CSV data + generator
│   └── ui/                      # Shiny application
│       ├── app.py               # Main app entry point
│       ├── www/style.css         # Glassmorphism CSS theme
│       ├── components/          # Reusable UI components
│       └── modules/             # Feature modules (data/, explore/, visualize/, ...)
├── tests/                       # 274 tests across 42 test files
├── pyproject.toml               # Build config (hatchling)
├── CHANGELOG.md                 # Version history
└── LICENSE                      # MIT License
```

---

## Contributing

1. **Fork** the repository
2. **Create a branch** for your feature (`git checkout -b feature/my-feature`)
3. **Write tests** for new functionality
4. **Run the test suite** to ensure all tests pass
5. **Submit a pull request** with a clear description

### Code style

- All analytics functions return `(result, CodeSnippet)` tuples
- CodeSnippets emit real pandas/sklearn code, never wrapper calls
- Use `ColumnType` for column classification instead of ad-hoc dtype checks
- Keep UI modules thin — business logic belongs in analytics packages

---

## License

MIT License. Copyright 2026 Ashish Khandelwal.

See [LICENSE](LICENSE) for details.

---

## Acknowledgements

PyAnalytica is inspired by [Radiant](https://vnijs.github.io/radiant/) by Vincent Nijs (UC San Diego) — a comprehensive R/Shiny analytics platform for business education.

Built with [Shiny for Python](https://shiny.posit.co/py/), [pandas](https://pandas.pydata.org/), [scikit-learn](https://scikit-learn.org/), [matplotlib](https://matplotlib.org/), [seaborn](https://seaborn.pydata.org/), and [SciPy](https://scipy.org/).

AI features powered by [Anthropic Claude](https://www.anthropic.com/).

Developed for teaching at the University of Illinois at Urbana-Champaign.
