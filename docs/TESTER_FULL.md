# PyAnalytica — Full Test Pass

**Time: about 4 hours.** Take breaks between sessions; there are ten, and each one says how long it should take.

## Read this first

You are testing a data-analysis tool built for university students. **You are not expected to know any statistics.** Every step tells you exactly what to click. Where a step involves a statistical idea, there's a one-line plain-English explanation — you don't need to understand the maths to test whether the software works.

Three things make a tester valuable, in order:

1. **Finding things that break.** Crashes, error messages, blank screens, spinning forever.
2. **Finding things that confuse you.** If you can't tell what a button does, or a word means nothing to you, write it down. Students will hit the same wall. "It worked but I didn't understand it" is a real finding.
3. **Doing what you're told, exactly.** If a step doesn't work, don't fix it yourself — that's the bug. Write down what happened and move on.

### The bug log

Keep this table going for the whole session. **This is the most important thing you produce.** Add a row whenever anything goes wrong or confuses you.

| # | Session | What I did | What I expected | What happened | How bad |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |

For "How bad", use:

- **Crash** — the app stopped, froze, or the page went blank
- **Wrong** — it worked, but the answer or picture looked wrong
- **Ugly** — it worked, but looked broken, cut off, or overlapping
- **Confusing** — it worked, but I didn't understand what to do or what I got

**Screenshot anything visual.** Name the files `bug01.png`, `bug02.png` to match your rows.

### Before you start

You need three files. They're in the `examples/tester_files` folder: **sales.csv**, **regions.csv**, **messy.csv**. Save them somewhere you can find, like your Desktop.

---

# Session 1 — Install (30 min)

Follow **INSTALL.md** exactly. Don't skip steps or fix problems yourself.

| | Question | Answer |
|---|---|---|
| 1.1 | How long did the install take, start to finish? | ____ min |
| 1.2 | Did `py --version` work first time, or did the Microsoft Store open? | Worked / Store |
| 1.3 | Did the `Set-ExecutionPolicy` step ask you to confirm? | Yes / No |
| 1.4 | Did any step show red text or fail? Which? | |
| 1.5 | Which step was hardest to follow, and why? | |
| 1.6 | Did the browser open by itself after `pyanalytica`? | Yes / No |
| 1.7 | Run `pyanalytica --version`. What does it print? | |

**1.8** Paste anything that looked like an error:

```
```

## The port test

A "port" is like a door number on your computer. The app uses door 8000. If it's taken, it should notice and use another instead of crashing.

**Leave the app running.** Open a *second* PowerShell window and run:

```powershell
cd $HOME\Documents\pyanalytica
.\.venv\Scripts\Activate.ps1
pyanalytica
```

| | Question | Answer |
|---|---|---|
| 1.9 | Did the second copy start, or crash? | Started / Crashed |
| 1.10 | Did it say "Port 8000 was busy"? Which port did it use? | |
| 1.11 | Did a second browser tab open and load properly? | Yes / No |

Now press **Ctrl+C** in the second window and run `pyanalytica --port 8000`.

| | Question | Answer |
|---|---|---|
| 1.12 | What message did you get? | |
| 1.13 | Did that message make sense to you? | Yes / No |

Close the second window. Keep the first running.

---

# Session 2 — Data (30 min)

## 2A. Bundled data

**Data → Load.** Load the bundled dataset **titanic**.

| | Question | Answer |
|---|---|---|
| 2.1 | Rows? Columns? | ____ / ____ |
| 2.2 | Was it obvious how to load, or did you hunt for it? | |

**Data → View.**

| | Question | Answer |
|---|---|---|
| 2.3 | Name in the first row? | |
| 2.4 | Can you sort by Age? How did you do it? | |
| 2.5 | Is there a way to see page 2 of the data? | Yes / No |
| 2.6 | Change "Decimals" to 0, then to 6. Does the table update both times? | Yes / No |

**Data → Profile.**

| | Question | Answer |
|---|---|---|
| 2.7 | Mean Age? | |
| 2.8 | How many missing values in Age? | |
| 2.9 | Click through every tab on this screen. Anything blank or broken? | |

## 2B. Your own file

**Data → Load**, and upload **sales.csv** from your Desktop.

| | Question | Answer |
|---|---|---|
| 2.10 | Rows? Columns? | ____ / ____ |
| 2.11 | Did uploading work first try? | Yes / No |
| 2.12 | In Profile, what does it say the `date` column's type is? | |

Now upload **messy.csv**. This file is deliberately awkward.

| | Question | Answer |
|---|---|---|
| 2.13 | Does Profile flag the missing values in `score`? How many? | |
| 2.14 | `mostly_missing` has only 3 real values out of 60. Does Profile make that obvious? | Yes / No |
| 2.15 | `constant` has the same value in every row. Does Profile point that out? | Yes / No |
| 2.16 | What type does it give `comment` (long sentences, all different)? Does that seem right to you? | |
| 2.17 | What type does it give `number_as_text` (numbers saved as text)? | |

## 2C. Transform

Still on **messy**, go to **Data → Transform**. Try each action in the dropdown, one at a time:

| | Action | Worked? | Notes |
|---|---|---|---|
| 2.18 | Rename a column | | |
| 2.19 | Add a computed column | | |
| 2.20 | Filter rows | | |
| 2.21 | Fill missing values in `score` | | |
| 2.22 | Change a column's type | | |
| 2.23 | Drop a column | | |
| 2.24 | Take a sample of rows | | |

| | Question | Answer |
|---|---|---|
| 2.25 | Did the row count change when you expected it to? | Yes / No |
| 2.26 | Could you undo anything you did? | Yes / No |
| 2.27 | Convert `number_as_text` to a number. Did it work? | Yes / No |

## 2D. Combine and export

Upload **regions.csv** too. Go to **Data → Combine** and join **sales** with **regions** — they share a `region` column.

| | Question | Answer |
|---|---|---|
| 2.28 | Did the join work? How many rows came out? | |
| 2.29 | Did the `manager` column appear in the result? | Yes / No |
| 2.30 | Try joining **titanic** with **regions** (they share nothing). What happened? | |

**Data → Export.** Download the combined data as CSV.

| | Question | Answer |
|---|---|---|
| 2.31 | Did the file download? | Yes / No |
| 2.32 | Open it in Excel or Notepad. Does it look right? | Yes / No |

---

# Session 3 — Explore (30 min)

Switch back to **titanic**.

## 3A. Summarize

**Explore → Group By / Summarize.** Group by **Sex**, summarize **Survived** with **mean**.

| | Question | Answer |
|---|---|---|
| 3.1 | Number for female? For male? | ____ / ____ |
| 3.2 | In your own words, what do those numbers say? | |
| 3.3 | Now group by **Pclass** as well (two grouping columns). Did it work? | Yes / No |
| 3.4 | Try summarizing with **count**, **sum**, **min**, **max**. All work? | |
| 3.5 | Click **Show Code**. Did code appear? Paste the first line. | |

## 3B. Pivot

**Explore → Pivot.** Rows = **Sex**, Columns = **Pclass**, Values = **Survived**, mean.

| | Question | Answer |
|---|---|---|
| 3.6 | Did a table appear with numbers in a grid? | Yes / No |
| 3.7 | Now remove the Columns choice, leaving it blank. Still work, or error? | |
| 3.8 | Set Rows and Values to the **same** column. What happened? | |

*(3.7 and 3.8 were both crashes once. They should work now.)*

## 3C. Cross-tab

**Explore → Cross-tab.** Row = **Sex**, Column = **Survived**.

| | Question | Answer |
|---|---|---|
| 3.9 | Did you get a table of counts? | Yes / No |
| 3.10 | Is there a "chi-squared" result? What p-value? | |
| 3.11 | Leave the Column choice blank. Does it break? | |

## 3D. Simulate

**Explore → Simulate.** This makes up random data to demonstrate statistical ideas.

Set **Simulation = Distributions**, then work through every distribution:

| | Distribution | Chart appeared? | Notes |
|---|---|---|---|
| 3.12 | Normal | | |
| 3.13 | Binomial | | |
| 3.14 | Poisson | | |
| 3.15 | Uniform | | |
| 3.16 | Exponential | | |

| | Question | Answer |
|---|---|---|
| 3.17 | Set **Seed** to 42, run twice. Identical results both times? | Yes / No |
| 3.18 | Change Seed to 1. Different from 42's result? | Yes / No |
| 3.19 | Try the **Probability Calculator** options (P(X ≤ x), P(X ≥ x), between, quantile). All work? | |
| 3.20 | Switch Simulation to **Central Limit Theorem** and run. Chart? | Yes / No |
| 3.21 | Switch to **Law of Large Numbers** and run. Chart? | Yes / No |
| 3.22 | Set Sample Size to **1**, then to **0**, then to a huge number like 9999999. What happens each time? | |

*(3.22 is a deliberate attempt to break it. Note whether it explains itself or just dies.)*

---

# Session 4 — Charts (40 min)

Use **titanic** unless told otherwise.

## 4A. Distribute

**Visualize → Distribute.** Column = **Age**.

| | Chart type | Appeared? | Notes |
|---|---|---|---|
| 4.1 | histogram | | |
| 4.2 | boxplot | | |
| 4.3 | violin | | |
| 4.4 | bar (use column **Pclass**) | | |

| | Question | Answer |
|---|---|---|
| 4.5 | On histogram, drag the **Bins** slider to its lowest, then highest. Does the chart change both times? | Yes / No |
| 4.6 | Tick **Show KDE**. Does a curve appear? | Yes / No |
| 4.7 | Set **Group By** to Sex. Does the chart split into groups? | Yes / No |
| 4.8 | Set **Facet Column** to Pclass. Do you get several small charts? | Yes / No |
| 4.9 | Set Facet Row as well. Still readable, or squashed? | |
| 4.10 | Is the text on the charts readable, or too small / overlapping? | |

**Now break it:** set the column to **Name** (text, not numbers) and plot a histogram.

| | Question | Answer |
|---|---|---|
| 4.11 | What happened? | |
| 4.12 | Did it explain the problem in words you understood? | Yes / No |
| 4.13 | Did the app still work afterwards? | Yes / No |

## 4B. Relate

**Visualize → Relate.** X = **Age**, Y = **Fare**.

| | Question | Answer |
|---|---|---|
| 4.14 | Did a scatter plot appear? | Yes / No |
| 4.15 | Turn on a trend line if there's an option. Did it appear? | Yes / No |
| 4.16 | Colour the points by **Survived**. Did it work? | Yes / No |
| 4.17 | Is there a legend, and does it make sense? | |

## 4C. Compare

**Visualize → Compare.** Compare **Fare** across **Pclass**.

| | Question | Answer |
|---|---|---|
| 4.18 | Did a chart appear? | Yes / No |
| 4.19 | Try every chart type in the dropdown. Any fail? | |

## 4D. Correlate

**Visualize → Correlate.**

| | Question | Answer |
|---|---|---|
| 4.20 | Did a coloured grid appear? | Yes / No |
| 4.21 | Are the numbers in the boxes readable? | Yes / No |
| 4.22 | Switch the method (Pearson / Spearman). Do numbers change? | Yes / No |
| 4.23 | Select only **one** column. What happens? | |

## 4E. Timeline

**Switch to the sales dataset** (this one has dates; titanic doesn't).

**Visualize → Timeline.** Date = **date**, Value = **units**.

| | Question | Answer |
|---|---|---|
| 4.24 | Did a line chart appear? | Yes / No |
| 4.25 | Change **Aggregation** to daily, weekly, monthly. Does the chart change each time? | Yes / No |
| 4.26 | Set **Group By** to region. Do you get four lines? | Yes / No |
| 4.27 | Try chart types line / area / bar. All work? | |
| 4.28 | Drag the **Rolling Window** slider. Does the line get smoother? | Yes / No |
| 4.29 | Now switch to **titanic** and try Timeline. It has no date column — what happens? | |

*(4.29 matters. Nothing bundled has dates, so this is a path students will hit.)*

---

# Session 5 — Analyze (30 min)

Back to **titanic**. These are statistical tests. **You don't need to understand them** — just check they produce a result and don't crash.

## 5A. Means

**Analyze → Means.** Work through every option in the **Test** dropdown:

| | Test | Result appeared? | Notes |
|---|---|---|---|
| 5.1 | One-sample t-test (Age) | | |
| 5.2 | Two-sample t-test (Age by Sex) | | |
| 5.3 | One-way ANOVA (Age by Pclass) | | |
| 5.4 | Mann-Whitney U (Age by Sex) | | |
| 5.5 | Kruskal-Wallis H (Age by Pclass) | | |

| | Question | Answer |
|---|---|---|
| 5.6 | Do the results include a "p-value"? | Yes / No |
| 5.7 | Is there a sentence explaining what the result means, or only numbers? | |
| 5.8 | Change **Alternative** (two-sided / less / greater). Do numbers change? | Yes / No |
| 5.9 | Try a test using **Name** as the numeric column. What happens? | |

## 5B. Proportions

**Analyze → Proportions.** Try each **Test** option:

| | Test | Worked? | Notes |
|---|---|---|---|
| 5.10 | One-sample proportion | | |
| 5.11 | Two-sample proportion | | |
| 5.12 | Test of independence (Sex vs Survived) | | |
| 5.13 | Goodness of fit | | |

| | Question | Answer |
|---|---|---|
| 5.14 | On "Test of independence", do you get observed *and* expected tables? | Yes / No |

## 5C. Correlation

**Analyze → Correlation.** X = **Age**, Y = **Fare**.

| | Question | Answer |
|---|---|---|
| 5.15 | Did you get a correlation number? What was it? | |
| 5.16 | Switch Pearson / Spearman. Does it change? | Yes / No |
| 5.17 | Use **messy.csv** and correlate `constant` (same value every row) with `score`. What happens? | |

---

# Session 6 — Model (40 min)

Machine-learning tools. Again — you don't need to understand them, only check they work.

## 6A. Regression

**Model → Regression.** Target (Y) = **Fare**, Features (X) = **Age** and **Pclass**.

| | Question | Answer |
|---|---|---|
| 6.1 | Did results appear? | Yes / No |
| 6.2 | Is there a number called R² (r-squared)? What is it? | |
| 6.3 | Are there charts as well as tables? | Yes / No |
| 6.4 | Run it again with the same settings. Identical results? | Yes / No |
| 6.5 | Add **Sex** (text, not a number) as a feature. Does it cope? | |
| 6.6 | Select **no** features and run. What happens? | |

## 6B. Classify

**Model → Classify.** Target = **Survived**, Features = **Age**, **Fare**, **Pclass**.

| | Model type | Ran? | Notes |
|---|---|---|---|
| 6.7 | Logistic Regression | | |
| 6.8 | K-Nearest Neighbours | | |
| 6.9 | Decision Tree | | |
| 6.10 | Random Forest | | |
| 6.11 | Support Vector Machine | | |

| | Question | Answer |
|---|---|---|
| 6.12 | Is there an "accuracy" number? Roughly what? | |
| 6.13 | Is there a confusion matrix (a small grid of counts)? | Yes / No |
| 6.14 | How long did the slowest model take? | ____ sec |
| 6.15 | Use **Name** as the target. What happens? | |

## 6C. Cluster and Reduce

**Model → Cluster.** Method = K-Means, Features = **Age** and **Fare**.

| | Question | Answer |
|---|---|---|
| 6.16 | Did it produce clusters and a chart? | Yes / No |
| 6.17 | Drag **Number of Clusters** to 2, then 15. Does it update both times? | Yes / No |
| 6.18 | Switch to **Hierarchical**. Does it work? | Yes / No |

**Model → Reduce.** Features = **Age**, **Fare**, **Pclass**, **SibSp**.

| | Question | Answer |
|---|---|---|
| 6.19 | Did you get results and a chart? | Yes / No |
| 6.20 | Is there something called a "scree plot"? | Yes / No |

## 6D. Evaluate and Predict

These use a model you saved earlier. Go back to **Classify**, run a model, and save it if there's a save option.

| | Question | Answer |
|---|---|---|
| 6.21 | Could you save a model? How? | |
| 6.22 | **Model → Evaluate**: does your saved model appear in the dropdown? | Yes / No |
| 6.23 | Evaluate it. Did you get metrics? | Yes / No |
| 6.24 | Drag the **Classification Threshold** slider. Do numbers change? | Yes / No |
| 6.25 | Switch "Evaluate On" between Test Set and Training Set. Does it change? | Yes / No |
| 6.26 | **Model → Predict**: is your model there? Can you run a prediction? | Yes / No |
| 6.27 | Try predicting using a dataset with the wrong columns (e.g. **sales**). What happens? | |
| 6.28 | If you go to Evaluate with **no** saved models, what does it show? | |

*(6.21–6.28 have never been tested by anyone. Be thorough and expect problems.)*

---

# Session 7 — Report (30 min)

## 7A. Procedure

**Report → Procedure.** This should list everything you've done so far.

| | Question | Answer |
|---|---|---|
| 7.1 | Is there a list of your earlier steps? Roughly how many? | |
| 7.2 | Do the descriptions match what you actually did? | Yes / No |
| 7.3 | Delete a step. Did it disappear? | Yes / No |
| 7.4 | Move a step up or down. Did it move? | Yes / No |
| 7.5 | Turn a step off (disable it). What changed? | |
| 7.6 | Add a comment to a step. Did it save? | Yes / No |
| 7.7 | Export as JSON / Python / Notebook. Do the files download? | |
| 7.8 | Open the Python file in Notepad. Does it look like code? | Yes / No |

## 7B. Report Builder

**Report → Report Builder.**

| | Question | Answer |
|---|---|---|
| 7.9 | Click **Import from Procedure**. Did anything appear? | Yes / No |
| 7.10 | Type a **Title** in the box at the top, then **Add Text** and type into it. Does both show in Preview? | Yes / No |
| 7.11 | Click **Run All Cells**. What happened? | |
| 7.12 | Click **Preview**. Does a preview appear? | Yes / No |
| 7.13 | Download **HTML**. Open it in your browser — does it look like a report? | Yes / No |
| 7.14 | Download **Jupyter** and **JSON**. Both download? | Yes / No |
| 7.15 | Click **Clear**. Does it warn you first, or just delete everything? | |

## 7C. Notebook

**Report → Notebook.**

| | Question | Answer |
|---|---|---|
| 7.16 | What's on this screen? Is it obvious what it's for? | |
| 7.17 | Anything broken or empty? | |

---

# Session 8 — Practice and Homework (30 min)

These are two separate tabs that work in opposite ways. Checking that they
behave differently is most of what this session is for.

## 8A. Practice (marks your answers straight away)

Open the **Practice** tab.

| | Question | Answer |
|---|---|---|
| 8.1 | Which drills are in the dropdown? | |
| 8.2 | Pick "Tips: getting your bearings". Does it tell you which dataset to load? | Yes / No |
| 8.3 | Load **tips** from Data > Load. Does that message change? | Yes / No |
| 8.4 | Answer the first question correctly (244) and click Check. What happens? | |
| 8.5 | Answer one deliberately wrong. Does it say so? | Yes / No |
| 8.6 | Does the wrong answer come with a hint? | Yes / No |
| 8.7 | Click **Hint** on any question. Does a hint appear? | Yes / No |
| 8.8 | Answer a few. Does the "X of 6 correct" counter update? | Yes / No |
| 8.9 | Click **Start over**. Does the counter reset? | Yes / No |
| 8.10 | Try the titanic drill. Does it work the same way? | Yes / No |
| 8.11 | Type letters into a numeric answer box and Check. Crash, or handled? | |

## 8B. Homework (does NOT mark anything)

Open the **Homework** tab and load `hw1_tips.yaml` from the data folder.

| | Question | Answer |
|---|---|---|
| 8.12 | Did the assignment load? How many questions? | |
| 8.13 | Does it explain how the work will be marked? What does it say? | |
| 8.14 | Is there a **Check** button anywhere on this tab? | Yes / No |
| 8.15 | Answer a question. Does anything tell you right or wrong? | Yes / No |
| 8.16 | Deliberately answer one wrong. Does anything tell you? | Yes / No |
| 8.17 | Does the sidebar show how many you have answered? | Yes / No |

**8.14, 8.15 and 8.16 are the important ones.** Homework must **never** tell
you whether an answer is right — that is done by the instructor after you hand
it in. If anything on this tab marks your answer, log it as **Wrong**.

## 8C. The work record

Before downloading, go and do some analysis: load tips, make a chart, run a
summarize. Then come back to Homework.

| | Question | Answer |
|---|---|---|
| 8.18 | Does the page say how many steps of work it recorded? | Yes / No |
| 8.19 | Roughly how many steps? Does that match what you did? | |
| 8.20 | Type your name, then click **Download submission**. Did a file save? | Yes / No |
| 8.21 | What is the file called, and what type is it? | |

## 8D. Check your submission

Open the downloaded file in your **web browser** (double-click it).

| | Question | Answer |
|---|---|---|
| 8.22 | Does it open as a readable page? | Yes / No |
| 8.23 | Can you see the questions and your answers? | Yes / No |
| 8.24 | Is there a "Work" table listing what you did? | Yes / No |
| 8.25 | Does the work table show computer code for the steps? | Yes / No |
| 8.26 | Does it show any score, mark, or right/wrong anywhere? | Yes / No |
| 8.27 | Is your name on it? | Yes / No |

**8.26 matters.** A submission should contain your answers and your work, and
no scores at all. If you can see a score anywhere, log it.

# Session 9 — Try to break it (25 min)

Deliberate abuse. For each, note whether you get a **clear explanation**, an **ugly error**, or a **crash**.

| | Do this | Result |
|---|---|---|
| 9.1 | Click a "Run"/"Plot" button before choosing any columns | |
| 9.2 | Click a "Run" button 10 times fast | |
| 9.3 | Type letters into a box that wants a number | |
| 9.4 | Type a negative number where it makes no sense (e.g. sample size −5) | |
| 9.5 | Type a huge number (99999999) into any numeric box | |
| 9.6 | Upload a file that isn't data — rename any `.txt` to `.csv` and upload it | |
| 9.7 | Upload an empty file (make a blank `.txt`, rename to `.csv`) | |
| 9.8 | Load a dataset, then remove it while looking at a chart | |
| 9.9 | Open the app in **two browser tabs** and use both | |
| 9.10 | Press the browser **Back** button a few times | |
| 9.11 | **Refresh** the page (F5). Is your work still there? | |
| 9.12 | Make the browser window very narrow (drag it thin). Does the layout survive? | |
| 9.13 | Zoom the browser to 200% (Ctrl and +). Still usable? | |
| 9.14 | Leave it open and untouched for 10 minutes, then click something | |

---

# Session 10 — Overall (15 min)

| | Question | Answer |
|---|---|---|
| 10.1 | Total bugs logged? How many were crashes? | ____ / ____ |
| 10.2 | Worst thing you found | |
| 10.3 | Most confusing screen | |
| 10.4 | Most confusing word or label | |
| 10.5 | Anything you expected to exist but couldn't find? | |
| 10.6 | Which part felt slowest? | |
| 10.7 | Did anything look visually broken — cut off, overlapping, unreadable? | |
| 10.8 | Could a student use this without someone sitting next to them? | Yes / No |
| 10.9 | Score /10 for "a beginner could use this" | ____ |
| 10.10 | Score /10 for "it feels finished and reliable" | ____ |

**10.11** Free comments — anything at all:

```
```

---

# Answer key

**Don't read until you've finished Session 8.** If any of yours differ, that's a finding — log it.

| Question | Should be |
|---|---|
| 1.7 version | pyanalytica 0.5.1 |
| 2.1 titanic | 891 rows, 12 columns |
| 2.3 first name | Gray, Countess Anna |
| 2.7 mean Age | about 29.46 |
| 2.8 missing Age | 178 |
| 2.10 sales.csv | 1460 rows, 4 columns |
| 2.13 missing score | 8 |
| 2.28 join result | 1460 rows (each sales row keeps its region's manager) |
| 3.1 survived by sex | female about 0.696, male about 0.373 |
| 5.15 Age vs Fare | a small number between −1 and 1 |
| 6.12 accuracy | somewhere around 0.6–0.9 |

**Expected behaviour, not numbers:**

- **1.9–1.11** second copy starts on a different port and works
- **1.12** `--port 8000` refuses clearly
- **3.7, 3.8** both work (they used to crash)
- **4.11–4.13** clear explanation, no crash, app keeps working
- **4.29** Timeline on titanic should explain there's no date column, not crash
- **8.4-8.9** Practice marks answers immediately: that is what it is for
- **8.14-8.16** Homework must **never** mark an answer
- **8.26** a submission must contain no scores at all
- **Session 9** everything should give a clear message or ignore you — nothing should crash the app
