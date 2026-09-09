# Validation spec

This is a brief for someone who has never seen PyAnalytica's source, and must
not read it. Work from this document, the datasets, and a statistics reference.

## Why it is written this way

The point of these notebooks is to be an oracle *outside* the code. If you look
at how the tool computes something and then compute it the same way, both can be
wrong together and the comparison passes green. That has already happened here:
a test asserted that pivot rows summed to 100 and passed for two months because
it summed the margin column into the row — 50 + 50 also comes to 100.

So this spec asks **questions**, not methods. Where a question has more than one
defensible answer — which variance assumption, which denominator, which
correction — the spec says so and asks you to choose, state your choice, and say
why. It does not tell you what the tool chose. If your answer differs from the
tool's, that difference is the finding, and it is worth more than agreement.

Do not open `src/`. Do not read the tool's generated code snippets.

## The datasets

Three, bundled with the package and readable straight from the repo:

| Name | Path | Rows |
|---|---|---|
| `titanic` | `src/pyanalytica/datasets/titanic/titanic.csv` | 891 |
| `tips` | `src/pyanalytica/datasets/tips/tips.csv` | 244 |
| `diamonds` | `src/pyanalytica/datasets/diamonds/diamonds.csv` | 53,940 |

These are the real published datasets, not simulations. Figures to check you
have the right file: 342 Titanic survivors; mean tip 2.9983; mean diamond price
3932.80. `titanic.Age` has 177 missing values, and how you handle them is one of
the choices to state.

## What to produce

One notebook per section below, in `validation/notebooks/`. Each notebook:

1. Computes the quantities asked for, using whatever library you consider
   correct — scipy, statsmodels, pingouin, or by hand.
2. Records each result under the exact key given, via the helper described in
   "Recording results".
3. States, in prose next to each result, any choice that could have gone
   another way, and why you made it.

Nothing else is required. Charts are welcome if they help you check yourself,
but nothing is compared on them.

## Recording results

```python
from validation.record import record, save

record("means.titanic_age_by_sex.t", 3.1234)
record("means.titanic_age_by_sex.df", 712)        # or 712.34, if you use Welch
record("means.titanic_age_by_sex.p", 0.0019)
save("means")                                      # writes validation/expected/means.json
```

Keys are `section.case.quantity`. The comparison harness looks up each key,
computes the tool's value for it, and reports differences. A key the harness
does not recognise is reported too — that usually means the tool does not
expose the quantity at all, which is itself worth knowing.

Tolerances default to 1e-6 relative. If a quantity is only meaningful to fewer
places — a p-value from a permutation test, say — pass `tol=`.

## Sections

### 1. `describe` — summary statistics

For `titanic.Age`, `tips.total_bill`, `diamonds.price`: n, mean, median,
standard deviation, variance, min, max, the three quartiles, skewness, kurtosis.

**Choices to state.** Standard deviation and variance have a divisor of n or
n−1. Quartiles have at least nine defensible definitions. Skewness and kurtosis
each have a bias-corrected and an uncorrected form, and kurtosis may or may not
have 3 subtracted. Say which you used for each.

### 2. `crosstab` — contingency tables

`titanic`: Pclass × Survived, and Sex × Survived.

For each: the counts, the row percentages, the column percentages, the
percentages of the whole table, the chi-square statistic, its degrees of
freedom, its p-value, Cramér's V, and the expected counts under independence.

**Choices to state.** Whether a continuity correction applies to the 2×2 case.
Whether row percentages are taken over the row alone or the row including its
total. Which denominator Cramér's V uses.

### 3. `groupby` — aggregation

`tips`: mean, median, count and standard deviation of `total_bill`, grouped by
`day`; then by `day` and `time` together.

`titanic`: mean `Age` and survival rate by `Pclass`.

**Choices to state.** How missing values are treated in each aggregate — 177
Titanic ages are missing, and a mean over 714 values is not a mean over 891.

### 4. `means` — comparing centres

`titanic`: is mean `Age` different from 30? Is mean `Age` different between the
sexes? Does mean `Age` differ across `Pclass`? Repeat the two-group comparison
without assuming normality.

`tips`: is mean `total_bill` different between smoking and non-smoking tables?

For each: the test statistic, degrees of freedom, the p-value, and an effect
size, naming which effect size you used.

**Choices to state.** Equal or unequal variances, and what decided it. One- or
two-sided. Which effect size and its denominator. For the ANOVA, whether you
corrected for unequal group variances, and what you did about it if you did not.

### 5. `proportions` — comparing shares

`titanic`: what share survived, and is it different from 0.5? Does the survival
share differ between the sexes? Are `Pclass` and `Survived` independent? Is
`Embarked` uniformly distributed?

For each: the statistic, the p-value, and a confidence interval where one
applies.

**Choices to state.** Which level you counted as the success, and why — the
answer changes sign with it. Which interval method (Wald, Wilson, exact). Pooled
or unpooled standard error for the two-sample test.

### 6. `correlation`

`tips`: `total_bill` with `tip`. `titanic`: `Age` with `Fare`. `diamonds`:
`carat` with `price`.

Pearson and Spearman for each, with p-values and confidence intervals for
Pearson.

**Choices to state.** How missing values are handled — pairwise or listwise.

### 7. `normality`

For `titanic.Age`, `tips.tip`, and `diamonds.price`: test whether each is
normally distributed.

**Choices to state.** Which test, and why. `diamonds.price` has 53,940 values;
say what you did about that and what it means for the result. Note explicitly
how many observations each statistic was computed on.

### 8. `regression`

`titanic`: `Age` explained by `Fare` and `Pclass`.
`diamonds`: `price` explained by `carat`, `depth` and `table`.

For each: the coefficients, their standard errors, t-statistics, p-values and
95% intervals; R-squared and adjusted R-squared; the F statistic and its
p-value; and the variance inflation factor for each predictor.

Then split `titanic` 70/30 with seed 42 and report R-squared on **both** the
rows fitted and the rows held out.

**Choices to state.** Whether an intercept is included. How rows with missing
values are handled. Whether predictors are standardised. Which VIF definition.

### 9. `classification`

`titanic`: `Survived` explained by `Pclass`, `Age` and `Fare`, split 70/30 with
seed 42.

Report: accuracy on the held-out rows, the confusion matrix, precision, recall,
F1, and the area under the ROC curve. Then report the accuracy of always
predicting the most common class.

**Choices to state.** How missing ages are handled. Whether features are
scaled. Which class counts as positive. What probability threshold turns a
prediction into a class.

### 10. `leakage`

The case the coursework is built on. Using `titanic`, `Survived` explained by
`Pclass`, `Age`, `Fare`, split 70/30 seed 42 — then again with a column added
that could only be known after the outcome. Construct such a column yourself and
say what you constructed.

Report the area under the curve for both, and the difference.

### 11. `clustering` and `pca`

`titanic`, using `Age` and `Fare`: k-means with k=3, seed 42. Report the size of
each cluster and the mean of each variable within it. Report the silhouette
score.

`titanic`, using `Age`, `Fare` and `Pclass`: principal components. Report the
proportion of variance each explains, the cumulative proportion, and the
loadings.

**Choices to state.** Whether variables are standardised first, and what happens
to the answer if they are not. The sign of a component is arbitrary — say how
you fixed it.

### 12. `simulation`

Draw 10,000 values from a normal with mean 100 and standard deviation 15, seed
42. Report the sample mean, standard deviation, skewness, kurtosis, and
P(X ≤ 100) both empirically and from the distribution.

Take 1,000 samples of size 30 from an exponential with mean 2, seed 42. Report
the mean and standard error of the sample means, and what theory predicts each
should be.

## Textbook anchors

Twelve results printed in a book, so at least part of this has no circularity at
all. These belong in `validation/notebooks/anchors.ipynb` with the citation
beside each. Sources should be ones a reader can check: ISLR, Wooldridge, Agresti,
or the documentation of a well-known implementation.

Suggested, but choose your own if you have better ones to hand: a t-test, a
one-way ANOVA table, a chi-square test of independence, a simple regression's
slope and intercept, a multiple regression's coefficient table, a logistic
regression's odds ratios, Pearson and Spearman on a small published dataset, a
2×2 proportion comparison, a PCA on a standard example, and a k-means result.

For each: the published value, your computation of it, and the citation.

## What happens next

`tests/test_validation.py` reads every `validation/expected/*.json`, computes
the tool's value for each key, and compares. Differences are reported as
findings, not as failures of your work: the notebook is the reference.

Please do not resolve a difference by changing the notebook to match the tool.
Raise it.

---

## Appendix: keys the harness already understands

The comparison is by exact key, so these are a contract. Anything you record
outside this list is still reported — as a quantity the tool does not expose,
which is a finding worth having — so record what the section asks for and use
these names where they fit.

| Key | Quantity |
|---|---|
| `means.titanic_age_vs_30.{t,p,effect_size}` | one-sample, Age against 30 |
| `means.titanic_age_by_sex.{t,p,effect_size,test_name}` | two-sample, Age by Sex |
| `means.titanic_age_by_pclass.{f,p,effect_size}` | Age across Pclass |
| `crosstab.titanic_pclass_survived.{chi2,p,dof,cramers_v}` | Pclass × Survived |
| `proportions.titanic_survival_by_sex.{z,p,difference}` | survival share by sex |
| `correlation.tips_bill_tip.{r,p}` | total_bill with tip |
| `regression.titanic_age.{intercept,coef_Fare,coef_Pclass,r_squared,adj_r_squared,f,f_p}` | Age on Fare and Pclass |
| `regression.titanic_age_split.{r_squared_train,r_squared_test}` | the same, 70/30 seed 42 |
| `classification.titanic_survived.{accuracy,precision,recall,f1,auc,test_accuracy}` | Survived on Pclass, Age, Fare |
| `clustering.titanic_age_fare.{sizes,n_clusters}` | k-means k=3, `sizes` sorted ascending |
| `pca.titanic.explained_variance` | proportions, in order |
| `normality.diamonds_price.{statistic,p,n,n_tested}` | `n` is the column's length, `n_tested` how many the statistic used |

`test_name` and any other text value is compared as a string, so record it only
where the section asks which test you chose.

Two of these exist because of arguments the tool has already had with itself,
and they are the ones most worth an independent answer:

- `regression.titanic_age_split` asks for R-squared on both the fitted and the
  held-out rows. Report both, and label them, whatever you think of the practice.
- `normality.diamonds_price` asks for `n` and `n_tested` separately. If your
  method uses every row, they are equal; say so.
