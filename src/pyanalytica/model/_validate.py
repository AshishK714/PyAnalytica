"""Shared input checks for the Model tab.

Every estimator here goes through scikit-learn, which reports a text column as
``could not convert string to float: 'admin.'``. That names a *value*, not the
column it came from, says nothing about what to do, and reaches the student as a
raw traceback -- from the panel where picking `job` as a feature is the first
thing anyone tries.

Data > Transform already got this treatment in 0.7.0: say which column, what it
holds, and which screen fixes it. This is the same rule for Model.
"""

from __future__ import annotations

import pandas as pd


def require_numeric_features(df: pd.DataFrame, features: list[str], what: str) -> None:
    """Refuse text columns before scikit-learn does it less helpfully.

    *what* names the thing being fitted, e.g. "Logistic regression".
    """
    missing = [col for col in features if col not in df.columns]
    if missing:
        raise ValueError(
            f"{what} was given column(s) that are not in the dataset: "
            f"{', '.join(repr(c) for c in missing)}."
        )

    # is_numeric_dtype() counts booleans, which sklearn reads as 0/1 quite
    # happily, so they need no special case here.
    text_cols = [col for col in features if not pd.api.types.is_numeric_dtype(df[col])]
    if not text_cols:
        return

    listed = ", ".join(f"'{col}'" for col in text_cols)
    example = df[text_cols[0]].dropna().astype(str)
    sample = ", ".join(repr(v) for v in example.unique()[:3])
    verb = "hold" if len(text_cols) > 1 else "holds"
    raise ValueError(
        f"{what} needs numbers, but {listed} {verb} text ({sample}). "
        f"Turn a text column into numbers first with Data > Transform > "
        f"Dummy Encode (One-Hot), which makes one 0/1 column per category, or "
        f"Ordinal Encode where the categories have a genuine order. Then choose "
        f"the encoded columns as features."
    )
