# PyAnalytica — Round 2

**Time: about 2 hours.** Shorter than last time, and aimed at the parts nobody
has ever opened.

## Before you start

**Update to the current version first.** Open the Command Prompt (Windows) or
Terminal (Mac), then:

**Windows**

```
cd /d %USERPROFILE%\Documents\pyanalytica
.venv\Scripts\activate.bat
pip install --upgrade pyanalytica==0.6.4
pyanalytica --version
```

**Mac**

```bash
cd ~/Documents/pyanalytica
source .venv/bin/activate
pip install --upgrade pyanalytica==0.6.4
pyanalytica --version
```

It should print `pyanalytica 0.6.4`. Then start it as usual — double-click your
launcher if you made one.

## What changed since you last looked

Six things you found are fixed. **Please spend five minutes confirming these
before moving on**, because a fix that does not work is worse than the original
bug:

| Check | What should happen now |
|---|---|
| Load titanic, then load tips | The Active Dataset switches to whatever you just loaded |
| Explore → Pivot: rows `day`, columns `size`, values `total_bill`, mean | A table appears (this used to show an error message) |
| Explore → Cross-tab on titanic | `Survived` and `Pclass` now appear in the variable lists |
| Visualize → Correlate, select one column only | It explains that you need two, instead of doing nothing |
| Data → Combine: join sales with regions on `region` | Works, and no error mentioning a column from another dataset |
| Practice tab → answer a question → Check | Feedback appears under the question (it used to show nothing) |

Anything here that does **not** behave as described is a bigger deal than a new
bug. Say so first in your notes.

## Keep the bug log going

Same as before — open **BUG-LOG.csv** and add a row for anything that breaks or
confuses you. Screenshot anything visual, named `bug01.png` to match.

For "How bad": **Crash** / **Wrong** / **Ugly** / **Confusing**.

---

# Session A — Try to break it (30 min)

**Do this session first.** It needs no statistics knowledge at all and it finds
the most per minute. For each, note whether you get a **clear message**, an
**ugly error**, or a **crash**.

| | Do this | Result |
|---|---|---|
| A1 | Click a "Run" or "Plot" button before choosing any columns | |
| A2 | Click a "Run" button ten times quickly | |
| A3 | Type letters into a box that wants a number | |
| A4 | Type a negative number where it makes no sense (sample size −5) | |
| A5 | Type 99999999 into any numeric box | |
| A6 | Rename any `.txt` file to `.csv` and upload it | |
| A7 | Make an empty `.txt`, rename to `.csv`, upload it | |
| A8 | Load a dataset, then remove it while looking at a chart of it | |
| A9 | Open the app in two browser tabs and use both | |
| A10 | Press the browser Back button a few times | |
| A11 | Refresh the page (F5). Is your work still there? | |
| A12 | Drag the browser window very narrow | |
| A13 | Zoom the browser to 200% (Ctrl and +) | |
| A14 | Leave it untouched for 10 minutes, then click something | |
| A15 | Upload a CSV where one column is dates. Does Profile call it a date? | |

---

# Session B — Model tools (40 min)

**Nobody has ever used the last two of these.** Expect problems, and write down
exactly what you clicked.

Load **titanic** first.

## B1. Regression

**Model → Regression.** Target (Y) = `Fare`, Features (X) = `Age` and `Pclass`.

| | Question | Answer |
|---|---|---|
| B1.1 | Did results appear? | Yes / No |
| B1.2 | Is there a number called R² (r-squared)? What is it? | |
| B1.3 | Are there charts as well as tables? | Yes / No |
| B1.4 | Run it again with the same settings — identical results? | Yes / No |
| B1.5 | Add `Sex` (text, not a number) as a feature. Does it cope? | |
| B1.6 | Select **no** features and run. What happens? | |

## B2. Classify

**Model → Classify.** Target = `Survived`, Features = `Age`, `Fare`, `Pclass`.

| | Model | Ran? | Notes |
|---|---|---|---|
| B2.1 | Logistic Regression | | |
| B2.2 | K-Nearest Neighbours | | |
| B2.3 | Decision Tree | | |
| B2.4 | Random Forest | | |
| B2.5 | Support Vector Machine | | |

| | Question | Answer |
|---|---|---|
| B2.6 | Is there an "accuracy" number? Roughly what? | |
| B2.7 | Is there a confusion matrix (a small grid of counts)? | Yes / No |
| B2.8 | How long did the slowest model take? | ____ sec |
| B2.9 | Use `Name` as the target. What happens? | |

## B3. Cluster and Reduce

**Model → Cluster.** Method = K-Means, Features = `Age` and `Fare`.

| | Question | Answer |
|---|---|---|
| B3.1 | Clusters and a chart appeared? | Yes / No |
| B3.2 | Drag Number of Clusters to 2, then 15 — updates both times? | Yes / No |
| B3.3 | Switch to Hierarchical. Works? | Yes / No |

**Model → Reduce.** Features = `Age`, `Fare`, `Pclass`, `SibSp`.

| | Question | Answer |
|---|---|---|
| B3.4 | Results and a chart? | Yes / No |
| B3.5 | Is there something called a "scree plot"? | Yes / No |

## B4. Evaluate and Predict — never tested by anyone

Go back to **Classify**, run a model, and look for a way to save it.

| | Question | Answer |
|---|---|---|
| B4.1 | Could you save a model? How did you do it? | |
| B4.2 | **Model → Evaluate**: does your saved model appear in the dropdown? | Yes / No |
| B4.3 | Evaluate it. Did you get metrics? | Yes / No |
| B4.4 | Drag the Classification Threshold slider. Do the numbers change? | Yes / No |
| B4.5 | Switch "Evaluate On" between Test Set and Training Set — changes? | Yes / No |
| B4.6 | **Model → Predict**: is your model there? Can you run a prediction? | Yes / No |
| B4.7 | Predict using a dataset with the wrong columns (e.g. sales). What happens? | |
| B4.8 | Go to Evaluate with no saved models at all. What does it show? | |

---

# Session C — Report tools (30 min)

**No automated tests cover any of this, and no person has used it.**

## C1. Procedure

**Report → Procedure.** This should list everything you have done so far.

| | Question | Answer |
|---|---|---|
| C1.1 | Is there a list of your earlier steps? Roughly how many? | |
| C1.2 | Do the descriptions match what you actually did? | Yes / No |
| C1.3 | Delete a step. Did it disappear? | Yes / No |
| C1.4 | Move a step up or down. Did it move? | Yes / No |
| C1.5 | Turn a step off (disable it). What changed? | |
| C1.6 | Add a comment to a step. Did it save? | Yes / No |
| C1.7 | Export as JSON, Python, Notebook. Do all three download? | |
| C1.8 | Open the Python file in Notepad/TextEdit. Does it look like code? | Yes / No |

## C2. Report Builder

**Report → Report Builder.**

| | Question | Answer |
|---|---|---|
| C2.1 | Click **Import from Procedure**. Did anything appear? | Yes / No |
| C2.2 | Type a **Title** in the box at the top, then **Add Text** and type into it. Does both show in Preview? | Yes / No |
| C2.3 | Click **Run All Cells**. What happened? | |
| C2.4 | Click **Preview**. Does a preview appear? | Yes / No |
| C2.5 | Download **HTML**. Open it — does it look like a report? | Yes / No |
| C2.6 | Download **Jupyter** and **JSON**. Both download? | Yes / No |
| C2.7 | Click **Clear**. Does it warn you, or just delete everything? | |

## C3. Notebook

**Report → Notebook.**

| | Question | Answer |
|---|---|---|
| C3.1 | What is on this screen? Is it obvious what it is for? | |
| C3.2 | Anything broken or empty? | |
| C3.3 | Can you export from here? Does the file open? | Yes / No |

---

# Session D — Homework, end to end (20 min)

Ask for `hw1_tips.yaml` if you do not have it.

| | Question | Answer |
|---|---|---|
| D1 | Open it in the **Homework** tab. How many questions? | |
| D2 | Does it explain how the work will be marked? What does it say? | |
| D3 | Is there a **Check** button anywhere on this tab? | Yes / No |
| D4 | Answer a question — does anything tell you right or wrong? | Yes / No |
| D5 | Deliberately answer one wrong. Does anything tell you? | Yes / No |

**D3, D4 and D5 matter most.** Homework must **never** tell you whether an
answer is right — that is done after you hand it in. If anything on this tab
marks your answer, log it as **Wrong**.

Now go and do some analysis — load tips, make a chart, run a summarize — then
come back to Homework.

| | Question | Answer |
|---|---|---|
| D6 | Does the page say how many steps of work it recorded? | Yes / No |
| D7 | Roughly how many? Does that match what you did? | |
| D8 | Type your name and click **Download submission**. Did a file save? | Yes / No |
| D9 | What is the file called, and what type is it? | |
| D10 | Open it in your **browser**. Does it read as a page? | Yes / No |
| D11 | Can you see the questions and your answers? | Yes / No |
| D12 | Is there a "Work" table showing what you did, with code? | Yes / No |
| D13 | Does it show any score, mark, or right/wrong anywhere? | Yes / No |

**D13 matters.** A submission should contain your answers and your work and no
scores at all.

---

# Wrap up (10 min)

| | Question | Answer |
|---|---|---|
| E1 | Total bugs logged? How many were crashes? | ____ / ____ |
| E2 | Worst thing you found | |
| E3 | Which of the six "should be fixed" checks at the top failed, if any? | |
| E4 | Most confusing screen in Model or Report | |
| E5 | Did anything look visually broken — cut off, overlapping, unreadable? | |
| E6 | Score /10 for "a beginner could use the Model tab" | ____ |
| E7 | Score /10 for "a beginner could use the Report tab" | ____ |

**E8.** Anything else:

```
```

---

# Answer key — read only after finishing

| Question | Should be |
|---|---|
| B1.2 R² | a number between 0 and 1, probably small |
| B2.6 accuracy | roughly 0.6 to 0.9 |
| B3.5 scree plot | yes, PCA produces one |
| D1 questions | 4 |
| D13 scores in the file | none at all |

Expected behaviour, not numbers:

- **A1–A14** — every one should give a clear message or do nothing. Nothing
  should crash the app or make it stop responding.
- **A15** — a date column should be recognised as a date, not text.
- **B4** — this is the part nobody has tested. Anything at all is a useful
  finding, including "I could not work out how to save a model".
- **D3–D5** — no marking anywhere on the Homework tab.
