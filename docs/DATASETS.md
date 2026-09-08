# The bundled datasets

`titanic`, `tips` and `diamonds` are the real datasets, as of 0.9.0.

| | Rows | A figure you can check |
|---|---|---|
| `titanic` | 891 | 342 survived (38.4%); 177 passengers have no recorded age |
| `tips` | 244 | mean bill 19.79, mean tip 3.00 |
| `diamonds` | 53,940 | mean price 3932.80, mean carat 0.7979 |

Each dataset directory carries a `SOURCE.md` saying where the file came from
and listing figures to check it against.

## What changed, and why it mattered

Until 0.9.0 all three were **simulated**. `datasets/generate.py` built them from
distributions chosen to give the right shape — the right number of rows, the
right columns, plausible-looking values — and wrote them to files named after
the well-known originals. Nothing anywhere said they were generated.

The numbers were wrong in ways a student would meet:

| | Shipped | Actual |
|---|---|---|
| Titanic survivors | 438 (49.2%) | 342 (38.4%) |
| Female survival rate | 69.6% | 74.2% |
| Mean tip | 3.98 | 3.00 |
| Mean diamond price | 2361.73 | 3932.80 |

The Titanic is the sharpest case, because it is the one dataset in the set that
everybody already knows something about. A student who remembered the story,
looked up the survival rate, or brought their own copy of the file got a
different answer from the tool with no explanation available anywhere. Any
coursework quoting a published figure could not be reconciled. And the failure
is silent: the tool's arithmetic was right the whole time, on data that was not
what it claimed to be.

That is the same shape as the defects the QA sweep kept finding — a confident,
correct-looking answer to a question the student did not realise they were
asking — except that this one sat underneath every panel at once.

## Consequences of the change

- **`generate.py` no longer produces these three files.** It is kept because CI
  and the install docs invoke it, but a generator left in place would put the
  simulated data back on the next run.
- **The bundled Practice drills were re-answered.** Their expected answers had
  been computed from the simulated data, so every one that depended on a value
  rather than a shape was wrong: 178 missing ages became 177, 438 survivors
  became 342, and so on. Their explanations quoted the old numbers too, and are
  corrected.
- **Missing values are part of the record now.** 177 Titanic passengers have no
  age, and `Cabin` is mostly empty. That is a property of the real data and is
  left alone: it is what makes the dataset worth teaching with.
