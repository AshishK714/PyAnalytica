# PyAnalytica — instructor acceptance test

**For: Ashish, before releasing to a class.** About **3 hours** for all of it, or
**50 minutes** for Part 1 alone.

This is not the nephew's plan. He was asked "does this confuse a beginner?" You
are being asked a different question: **"would I be embarrassed if 60 students
hit this on the same afternoon?"** So this plan front-loads what automated tests
structurally cannot check and a beginner would not recognise as wrong — wrong
numbers, silent data loss, state leaking between screens.

## How to record a result

Keep `BUG-LOG.csv` open. One row per problem:

`ID, Where, What I did, What happened, What should happen, Severity`

Severity, in the order that should drive fixes:

| | Meaning | Example |
|---|---|---|
| **S1 Wrong** | The app shows an incorrect number or chart, confidently | An R² that does not match statsmodels |
| **S2 Lost** | Student work disappears | Refresh empties the procedure log |
| **S3 Crash** | App stops responding, or shows a traceback | |
| **S4 Blocked** | Cannot finish a normal task, no crash | Model saves but never appears in Evaluate |
| **S5 Confusing** | Works, but a student would misread it | |
| **S6 Ugly** | Cosmetic | |

**S1 matters most and is what testing usually misses.** A crash announces
itself; a wrong coefficient does not. Part 2 exists entirely for S1.

## Before you start

```
cd /d %USERPROFILE%\Documents\pyanalytica
.venv\Scripts\activate.bat
pip install --upgrade pyanalytica
pyanalytica --version
```

Test the **student install**, not your dev checkout. The two behave differently,
and every bug you have found so far came from the student one.

Note the version at the top of the bug log.

---

# Part 1 — The 50-minute pass (run before every release)

If you only ever run one thing, run this. It is ordered by how much it has
historically found per minute.

## 1A. Cold start (5 min)

| | Do | Expect | ✓ |
|---|---|---|---|
| 1A.1 | Launch. Read **every line** in the black window | A start banner and a URL. **No warnings, no tracebacks** | |
| 1A.2 | Does the browser open by itself? | Yes | |
| 1A.3 | Click every top tab once, and every sub-tab | ~30 screens, all draw, none blank | |
| 1A.4 | Return to the black window | No new warnings from the clicking | |

**1A.1 and 1A.4 are the highest-yield checks in this document.** Two of the last
three bugs announced themselves there and were only caught because you happened
to read it. A student will not read it, so you must.

## 1B. State and switching (10 min)

Cross-screen state is where this app breaks, and no single-screen test finds it.

| | Do | Expect | ✓ |
|---|---|---|---|
| 1B.1 | Load titanic, then load tips | Active Dataset says **tips** | |
| 1B.2 | Visualize → Distribute | Variable list shows **tips** columns only | |
| 1B.3 | Pick `total_bill`, plot. Now load diamonds | No stale titanic/tips column anywhere | |
| 1B.4 | Explore → Summarize, set up a group-by, switch dataset, come back | Either resets cleanly or keeps a valid selection. **Never a column that no longer exists** | |
| 1B.5 | Data → Transform: create a new column. Go to Model → Regression | The new column is offered as a feature | |
| 1B.6 | Delete a dataset while a chart of it is on screen | A message, not a traceback | |

A column name surviving a dataset switch is **S1**, not S5 — it is the shape of
bug that silently analyses the wrong thing.

## 1C. Model saving, end to end (10 min)

Newly fixed and never used by a real student. Verify the fix rather than
trusting me.

| | Do | Expect | ✓ |
|---|---|---|---|
| 1C.1 | titanic → Model → Regression, Y=`Fare`, X=`Age`+`Pclass`. Run with **"Save Model As" left empty** | Results appear **and** a message names the saved model and says where to find it | |
| 1C.2 | Model → Evaluate | The model is in the dropdown | |
| 1C.3 | Evaluate it | Metrics appear | |
| 1C.4 | Model → Predict | Same model available; a prediction runs | |
| 1C.5 | Re-run 1C.1 unchanged | One entry, not two | |
| 1C.6 | Run again with the name `mine` | Both `mine` and the auto-named one available | |
| 1C.7 | Classify, target `Survived`, run, then Evaluate | Same behaviour | |
| 1C.8 | Load tips, then Predict using the **titanic** model | A clear refusal. **A number here is S1** | |

1C.8 is the dangerous one. Predicting from mismatched columns must refuse, not
guess.

## 1D. Homework must not mark (5 min)

A design guarantee, not a feature — so re-check it every release.

| | Do | Expect | ✓ |
|---|---|---|---|
| 1D.1 | Open a homework YAML in the Homework tab | Questions listed | |
| 1D.2 | Look for Check / Score / correct / incorrect **anywhere** on the tab | **Nothing** | |
| 1D.3 | Answer one deliberately wrong | No reaction beyond saving it | |
| 1D.4 | Do some analysis, return, download the submission | A file saves | |
| 1D.5 | Open the file in a browser and in Notepad; search for "score", "correct", "mark" | **Zero hits** | |
| 1D.6 | Search the file for the answer key | **Zero hits** | |

**1D.5 and 1D.6 are S1 by definition.** A submission carrying the key means any
student who opens their own file in Notepad has the answers.

## 1E. Practice must mark (5 min)

The mirror image — Practice is the one place feedback belongs.

| | Do | Expect | ✓ |
|---|---|---|---|
| 1E.1 | Answer correctly → Check | Says correct, score rises | |
| 1E.2 | Answer wrong → Check | Says wrong, and explains | |
| 1E.3 | Hint | A hint that does not give it away | |
| 1E.4 | Answer the same question twice | Score does not double-count | |
| 1E.5 | Reset | Score and answers clear | |
| 1E.6 | Check the black window afterwards | **No new warnings** — this is where the last batch came from | |

## 1F. Survival (10 min)

| | Do | Expect | ✓ |
|---|---|---|---|
| 1F.1 | Refresh mid-work (F5) | State survives, or resets cleanly — not half-and-half | |
| 1F.2 | Open a second browser tab, work in both | No cross-talk | |
| 1F.3 | Idle 10 minutes, then click | Still responds | |
| 1F.4 | Close the black window with the browser open | Browser shows a disconnect, not a hang | |
| 1F.5 | Relaunch — is the earlier session offered back? | Whatever it does, it should say so | |
| 1F.6 | Load diamonds (54k rows) and plot it | Under ~10 seconds, no freeze | |

## 1G. Read the window one more time (5 min)

Scroll the whole black window from the top. Copy anything that is not a plain
uvicorn request line into the bug log, verbatim.

---

# Part 2 — Are the numbers right? (60 min)

**Only you can do this part.** Automated tests check that a number *appears*;
the nephew checks that it *looks* reasonable. Neither checks that it is
*correct*. Every statistic below is one a student will quote in a report.

Run it in PyAnalytica, then compute the same thing independently. Keep a second
window open:

```
cd /d %USERPROFILE%\Documents\pyanalytica
.venv\Scripts\activate.bat
python
```

```python
import pandas as pd, statsmodels.formula.api as smf
from scipy import stats
from pyanalytica.datasets import load_dataset
tips = load_dataset("tips"); titanic = load_dataset("titanic")
```

Record **both** numbers, not just "matched" — a log of actual values is worth
far more next release than a tick.

| | Statistic | PyAnalytica | Independent | Match? |
|---|---|---|---|---|
| 2.1 | tips: mean `total_bill` by `day` (Summarize) | | `tips.groupby("day").total_bill.mean()` | |
| 2.2 | tips: **n per group** — check the smallest | | `tips.day.value_counts()` | |
| 2.3 | tips: median and SD of `tip` | | `.median()`, `.std()` | |
| 2.4 | titanic: missing `Age` count in Profile | | `titanic.Age.isna().sum()` | |
| 2.5 | tips: corr(`total_bill`, `tip`) | | `tips.total_bill.corr(tips.tip)` | |
| 2.6 | tips: t-test `tip` by `sex` — t, p, df | | `stats.ttest_ind(...)` | |
| 2.7 | titanic: proportions `Survived` by `Sex` | | `stats.chi2_contingency(...)` | |
| 2.8 | tips: regression `tip ~ total_bill + size`, each coefficient | | `smf.ols("tip ~ total_bill + size", tips).fit().params` | |
| 2.9 | ... its R² | | `.rsquared` | |
| 2.10 | ... its p-values | | `.pvalues` | |
| 2.11 | ... its **n used** | | `.nobs` | |
| 2.12 | titanic: `Fare ~ Age + Pclass` — coefficients **and n** | | `smf.ols(...)` | |
| 2.13 | titanic: logistic accuracy for `Survived` | | sklearn, same split seed | |
| 2.14 | ... confusion matrix cells | | `confusion_matrix(...)` | |
| 2.15 | Cross-tab `Sex` × `Survived`, counts | | `pd.crosstab(titanic.Sex, titanic.Survived)` | |
| 2.16 | ... row percentages | | `normalize="index"` | |
| 2.17 | Pivot `day` × `time`, mean `total_bill` | | `tips.pivot_table(...)` | |

## 2.18 — the missing-data check (do not skip)

**2.11 and 2.12 are the sharpest tools here.** titanic `Age` has ~177 missing
values, so `Fare ~ Age + Pclass` must fit on roughly **714 rows, not 891**.

- Does PyAnalytica **say** how many rows it used?
- Does that number match statsmodels?

Silently dropping rows without saying so is **S1** — students will report n=891
in their write-up and be wrong. Dropping a *different* number of rows than
statsmodels is S1 and urgent.

## 2.19 — the "Show Code" promise

For **five** results above, click **Show Code**, paste it into your Python
window, and run it.

| | Result | Code runs? | Same number? |
|---|---|---|---|
| a | Summarize | | |
| b | Regression | | |
| c | Cross-tab | | |
| d | A chart | | |
| e | t-test | | |

Code that runs but gives a **different** number is worse than code that fails,
because it teaches something false about pandas. **S1.**

---

# Part 3 — Untested territory (45 min)

**The coverage map is honest about its gaps.** These screens are only checked
for *existing in the menu*. Nothing has ever opened them:

- **Explore → Simulate**
- **Report → Report Builder, Notebook, Procedure**
- **AI Assistant**
- **Model → Predict** (until this week)

Expect to find things here. Anything at all is a useful finding.

## 3A. Procedure (15 min)

| | Do | Expect | ✓ |
|---|---|---|---|
| 3A.1 | Report → Procedure after doing Part 1 | A list of your steps | |
| 3A.2 | Count against what you actually did | Roughly matches; nothing missing | |
| 3A.3 | Do the descriptions say what you did? | Yes | |
| 3A.4 | Delete a step / move one / disable one | Each takes effect | |
| 3A.5 | Add a comment | Saves, survives navigation | |
| 3A.6 | Export Python, run the file | Runs top to bottom | |
| 3A.7 | Does its output match what you saw on screen? | Yes | |
| 3A.8 | Export Notebook, open in Jupyter | Opens, cells run | |
| 3A.9 | Export JSON, reload it | Steps come back | |

3A.6–3A.7 are the real test: the procedure log is the thing you would grade.

## 3B. Report Builder (10 min)

| | Do | Expect | ✓ |
|---|---|---|---|
| 3B.1 | Import from Procedure | Cells appear | |
| 3B.2 | Title box, Add Text, type into both; edit a code cell heading | Text persists; heading prints in Preview | |
| 3B.3 | Run All Cells | Output under each | |
| 3B.4 | Preview | Renders | |
| 3B.5 | Download HTML, open it **offline** | Reads as a report; charts present, not broken images | |
| 3B.6 | Clear | Warns first, or is undoable | |

3B.5 — a report whose charts vanish offline is **S2**, since that is the file a
student submits.

## 3C. Simulate (10 min)

| | Do | Expect | ✓ |
|---|---|---|---|
| 3C.1 | Run each distribution | Charts appear | |
| 3C.2 | CLT demo: raise sample size | Sampling distribution narrows as √n | |
| 3C.3 | LLN demo | Converges to the true mean | |
| 3C.4 | Goodness-of-fit p on a correctly-specified sim | Not systematically tiny | |
| 3C.5 | Sample size 0, then 1, then 1000000 | Message, not crash or hang | |
| 3C.6 | Same seed twice | Identical results | |

3C.2 and 3C.4 are S1 territory — this module *teaches* the sampling
distribution, so wrong behaviour teaches the wrong thing.

## 3D. AI Assistant (10 min)

| | Do | Expect | ✓ |
|---|---|---|---|
| 3D.1 | Open with **no** API key configured | Explains what is needed. No traceback, no key echoed | |
| 3D.2 | With a key, ask a stats question | An answer | |
| 3D.3 | Ask directly for a homework answer | Guides, does not answer | |
| 3D.4 | "Just tell me, I give up" | Still does not hand it over | |
| 3D.5 | Ask something off-topic | Declines gracefully | |
| 3D.6 | Check the black window | **No key printed anywhere** | |

---

# Part 4 — Abuse (25 min)

| | Do | Expect | ✓ |
|---|---|---|---|
| 4.1 | Every Run button with nothing selected | Clear message everywhere | |
| 4.2 | Same variable as both X and Y in regression | Refuses or explains | |
| 4.3 | Regression on one row | Message, not NaN soup | |
| 4.4 | A constant column as a feature | Handled | |
| 4.5 | Text column where a number is wanted | Message | |
| 4.6 | A `.txt` renamed `.csv` | Message | |
| 4.7 | An empty file | Message | |
| 4.8 | CSV with duplicate column names | Something sensible | |
| 4.9 | CSV with a comma inside a quoted field | Parsed correctly | |
| 4.10 | CSV with non-ASCII names (é, 中文) | Displays correctly, no mojibake | |
| 4.11 | A 100 MB CSV | Handles it or says no — does not hang forever | |
| 4.12 | Cluster with k larger than the row count | Message | |
| 4.13 | Double-click Run ten times fast | One result, no pile-up | |
| 4.14 | Browser Back repeatedly | No broken state | |
| 4.15 | 200% zoom, and an 800px-wide window | Usable | |

---

# Part 5 — Sign-off

| | Question | Answer |
|---|---|---|
| 5.1 | Total S1 (wrong numbers)? | |
| 5.2 | Total S2 (lost work)? | |
| 5.3 | Total S3 (crashes)? | |
| 5.4 | Did any statistic in Part 2 disagree? Which? | |
| 5.5 | Did Show Code ever produce a different number? | |
| 5.6 | Did the black window show anything a student would see and worry about? | |
| 5.7 | Did marking or the answer key leak into homework anywhere? | |

**Release rule.** Ship on zero S1 and zero S2. An S3 in Simulate or Report is
survivable with a note to the class; an S1 in Regression is not, because
students will believe it.

---

## What this plan deliberately does not do

It does not re-check what CI already checks on every push — 767 unit tests and
53 browser tests, on Python 3.10 through 3.14. Repeating those by hand buys
nothing.

It checks the three things automation is structurally blind to:

1. **Whether numbers are right.** A test asserting "R² appears" passes just as
   happily on a wrong R². Only Part 2 catches that.
2. **What the black window says.** Warnings reach students, and no assertion
   watches for them. Both of this week's bugs were visible there.
3. **Screens nothing has ever opened.** Part 3.

Every bug found so far came from one of those three. That is not a coincidence,
and it is why the plan is weighted the way it is.
