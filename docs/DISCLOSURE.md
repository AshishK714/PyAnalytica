# Progressive disclosure

## The problem

Every panel shows everything it can compute. Across 30 panels there are 103
outputs and 18 plots, and **8 uses of a collapsible container in the whole
app** — all of them "Expand" buttons on charts, none of them disclosure. Ten
panels put two or more plots on screen at once.

The result is that the answer to the question you asked shares the screen with
three things you did not ask for, each of them competing for the same vertical
space. Model > Regression answers "what are the coefficients" and then, without
being asked, renders VIF, residuals-vs-fitted and a Q-Q plot. On a laptop the
coefficients are the only part above the fold that anyone reads.

Three specific harms, in order of how much they matter:

1. **The important thing is not visually more important.** A student cannot tell
   from the layout which part is the answer and which is supporting material.
2. **Plots are drawn in a letterbox.** Every plot output is pinned to 350 or
   400 pixels. The figures are built at 8×5 inches and Shiny re-renders them
   into that box, so titles clip — the space is too small for what is in it.
3. **Everything is computed whether or not it is looked at.** `linear_regression()`
   builds two matplotlib figures during the fit. `simulate` runs every
   goodness-of-fit test. Nothing consults whether the result will be shown.

## The rule

Three tiers, the same in every panel.

| Tier | What belongs here | Behaviour |
|---|---|---|
| **1. The answer** | The result sentence, and the one table that answers the question that was asked | Always visible |
| **2. Supporting evidence** | The numbers behind the answer: VIF, assumption checks, expected counts, cluster profiles | One click, opens in place |
| **3. Diagnostics** | Plots that check the model rather than state the result | Opt-in, and given real space when opened |

Two rules that go with it:

- **A heading belongs to its section, never above it.** Static headings sit in
  the layout whether or not the thing they name exists — which is why a failed
  evaluation left "Confusion Matrix" over an empty page. If the section does not
  render, its heading must not either.
- **Nothing in tier 3 is computed while it is closed.** Hiding an output stops
  it being drawn but not being built; the saving that matters is upstream.

## Per-panel tiering

Proposed, and the part that needs the instructor's judgment rather than an
engineer's. Current contents are as they stand today, in render order.

### Model > Regression
| Now | Tier |
|---|---|
| `model_summary` (interpretation, R²) | 1 |
| `coef_table` | 1 |
| "VIF (Multicollinearity)" + `vif_table` | 2 |
| `resid_plot` | 3 |
| `qq_plot` | 3 |

### Model > Cluster
| Now | Tier |
|---|---|
| `guidance`, `cluster_summary` | 1 |
| "Cluster Profiles" + `profiles` | 1 — the profiles *are* the answer |
| `scatter_plot` | 2 |
| `elbow_plot` | 3 — it justifies the choice of k, which is a separate question |

### Model > Reduce (PCA)
| Now | Tier |
|---|---|
| `guidance`, `pca_summary` | 1 |
| "Loadings" + `loadings` | 2 |
| `scree_plot` | 2 — how many components to keep is the usual next question |
| `biplot` | 3 |

### Model > Evaluate
| Now | Tier |
|---|---|
| `metrics_summary` | 1 |
| "Confusion Matrix" + `cm_table` | 1 |
| `roc_plot` | 2 |

### Explore > Simulate
| Now | Tier |
|---|---|
| `sim_interpretation`, `chart_or_message` | 1 |
| `stats_table` | 1 |
| "Goodness-of-Fit Tests" + `fit_table` | 3 — most people simulating a
  distribution are not asking whether the sample passes a formal test |

### Analyze > Means and Proportions
| Now | Tier |
|---|---|
| `test_result` | 1 |
| `group_stats` / first result table | 1 |
| `assumptions`, remaining tables | 2 |

## Mechanism

A single component, so every panel discloses the same way:

```python
disclosure("diagnostics", "Diagnostic plots", ...content..., open=False)
```

Built on `ui.accordion(open=False)`. Shiny suspends outputs that are not
visible, so tier 2 and 3 outputs are not rendered or serialised while closed —
that part is free.

**Computation is not free, and needs an argument.** The library functions build
their figures eagerly. Rather than reshape the result dataclasses — they are
used by the report builder and the notebook export as well as the panels — each
takes a flag:

```python
def linear_regression(df, target, features, *, test_size=None,
                      random_state=42, diagnostics=True) -> RegressionResult:
```

The panel passes `diagnostics=input.show_diagnostics()`, so opening the section
re-runs the fit *with* the plots and closing it stops paying for them. Explicit,
local, and it leaves every existing caller working.

**Opened means room.** A disclosed plot renders at 520px inside a card with
`full_screen=True`, not the current 350px letterbox. This is the same change as
the clipped-title fix: figures need `fig.set_layout_engine("constrained")` so
layout is recomputed when Shiny resizes them, instead of a one-shot
`tight_layout()` whose margins were computed for a different size. There are 41
one-shot calls to convert.

## Keeping it

`tests/test_ui/test_progressive_disclosure.py`, in the same style as
`test_no_dead_controls.py`: a panel's main area may hold at most three
unconditional outputs, and any plot beyond the first must sit inside a
disclosure container. Existing exceptions are listed explicitly and are meant to
shrink, not grow.

## Order of work

1. The shared `disclosure` component and the lint, with one panel converted
   (Regression) as the worked example.
2. The layout engine across all 41 figures — independent, and it makes every
   disclosed plot legible.
3. The remaining nine heavy panels.
4. The `diagnostics=` flag through the four library functions that build
   figures eagerly.

Steps 1–3 are layout and are individually verifiable in the browser. Step 4
touches the statistics library and wants its own review.
