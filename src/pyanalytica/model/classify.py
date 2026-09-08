"""Classification models — logistic regression, decision tree, random forest."""

from __future__ import annotations

from dataclasses import dataclass, field

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier

from pyanalytica.core.codegen import CodeSnippet
from pyanalytica.model._validate import require_numeric_features


@dataclass
class ClassificationResult:
    """Result of a classification model."""
    model_type: str
    coefficients: pd.DataFrame | None = None
    feature_importance: pd.DataFrame | None = None
    train_accuracy: float = 0.0
    test_accuracy: float | None = None
    predictions: pd.Series = field(default_factory=pd.Series)
    probabilities: pd.Series = field(default_factory=pd.Series)
    classes: list = field(default_factory=list)
    code: CodeSnippet = field(default_factory=lambda: CodeSnippet(code=""))
    model: object | None = None
    label_encoder: object | None = None
    feature_names: list[str] = field(default_factory=list)
    X_train: pd.DataFrame | None = None
    X_test: pd.DataFrame | None = None
    y_train: pd.Series | None = None
    y_test: pd.Series | None = None


def logistic_regression(
    df: pd.DataFrame,
    target: str,
    features: list[str],
    test_size: float = 0.3,
    random_state: int = 42,
) -> ClassificationResult:
    """Fit logistic regression."""
    require_numeric_features(df, features, "Logistic regression")
    clean = df[[target] + features].dropna()
    X = clean[features]
    y = clean[target]

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    classes = le.classes_.tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=test_size, random_state=random_state
    )

    model = LogisticRegression(max_iter=1000, random_state=random_state)
    model.fit(X_train, y_train)

    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)

    predictions = pd.Series(le.inverse_transform(model.predict(X_test)), index=X_test.index)

    proba = model.predict_proba(X_test)
    if proba.shape[1] == 2:
        probabilities = pd.Series(proba[:, 1], index=X_test.index)
    else:
        probabilities = pd.Series(proba.max(axis=1), index=X_test.index)

    # Coefficients
    if len(classes) == 2:
        coef_df = pd.DataFrame({
            "variable": features,
            "coefficient": np.round(model.coef_[0], 4),
            "odds_ratio": np.round(np.exp(model.coef_[0]), 4),
        })
    else:
        rows = []
        for i, cls in enumerate(classes):
            for j, feat in enumerate(features):
                rows.append({
                    "class": cls,
                    "variable": feat,
                    "coefficient": round(model.coef_[i][j], 4),
                })
        coef_df = pd.DataFrame(rows)

    feats_str = repr(features)
    code = (
        f'from sklearn.linear_model import LogisticRegression\n'
        f'from sklearn.model_selection import train_test_split\n'
        f'from sklearn.preprocessing import LabelEncoder\n\n'
        f'X = df[{feats_str}].dropna()\n'
        f'y = LabelEncoder().fit_transform(df["{target}"].loc[X.index])\n'
        f'X_train, X_test, y_train, y_test = train_test_split(X, y, test_size={test_size}, random_state={random_state})\n'
        f'model = LogisticRegression(max_iter=1000, random_state={random_state}).fit(X_train, y_train)\n'
        f'print(f"Train accuracy: {{model.score(X_train, y_train):.3f}}")\n'
        f'print(f"Test accuracy: {{model.score(X_test, y_test):.3f}}")'
    )

    return ClassificationResult(
        model_type="Logistic Regression",
        coefficients=coef_df,
        train_accuracy=round(train_acc, 4),
        test_accuracy=round(test_acc, 4),
        predictions=predictions,
        probabilities=probabilities,
        classes=classes,
        code=CodeSnippet(
            code=code,
            imports=[
                "from sklearn.linear_model import LogisticRegression",
                "from sklearn.model_selection import train_test_split",
                "from sklearn.preprocessing import LabelEncoder",
            ],
        ),
        model=model,
        label_encoder=le,
        feature_names=features,
        X_train=X_train,
        X_test=X_test,
        y_train=pd.Series(y_train, name=target),
        y_test=pd.Series(y_test, name=target),
    )


def decision_tree(
    df: pd.DataFrame,
    target: str,
    features: list[str],
    test_size: float = 0.3,
    max_depth: int = 5,
    random_state: int = 42,
) -> ClassificationResult:
    """Fit a decision tree classifier."""
    require_numeric_features(df, features, "A decision tree")
    clean = df[[target] + features].dropna()
    X = clean[features]
    y = clean[target]

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    classes = le.classes_.tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=test_size, random_state=random_state
    )

    model = DecisionTreeClassifier(max_depth=max_depth, random_state=random_state)
    model.fit(X_train, y_train)

    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)

    predictions = pd.Series(le.inverse_transform(model.predict(X_test)), index=X_test.index)

    proba = model.predict_proba(X_test)
    if proba.shape[1] == 2:
        probabilities = pd.Series(proba[:, 1], index=X_test.index)
    else:
        probabilities = pd.Series(proba.max(axis=1), index=X_test.index)

    importance_df = pd.DataFrame({
        "variable": features,
        "importance": np.round(model.feature_importances_, 4),
    }).sort_values("importance", ascending=False)

    feats_str = repr(features)
    code = (
        f'from sklearn.tree import DecisionTreeClassifier\n'
        f'from sklearn.model_selection import train_test_split\n'
        f'from sklearn.preprocessing import LabelEncoder\n\n'
        f'X = df[{feats_str}].dropna()\n'
        f'y = LabelEncoder().fit_transform(df["{target}"].loc[X.index])\n'
        f'X_train, X_test, y_train, y_test = train_test_split(X, y, test_size={test_size}, random_state={random_state})\n'
        f'model = DecisionTreeClassifier(max_depth={max_depth}, random_state={random_state}).fit(X_train, y_train)\n'
        f'print(f"Train accuracy: {{model.score(X_train, y_train):.3f}}")\n'
        f'print(f"Test accuracy: {{model.score(X_test, y_test):.3f}}")'
    )

    return ClassificationResult(
        model_type="Decision Tree",
        feature_importance=importance_df,
        train_accuracy=round(train_acc, 4),
        test_accuracy=round(test_acc, 4),
        predictions=predictions,
        probabilities=probabilities,
        classes=classes,
        code=CodeSnippet(
            code=code,
            imports=[
                "from sklearn.tree import DecisionTreeClassifier",
                "from sklearn.model_selection import train_test_split",
                "from sklearn.preprocessing import LabelEncoder",
            ],
        ),
        model=model,
        label_encoder=le,
        feature_names=features,
        X_train=X_train,
        X_test=X_test,
        y_train=pd.Series(y_train, name=target),
        y_test=pd.Series(y_test, name=target),
    )


def random_forest(
    df: pd.DataFrame,
    target: str,
    features: list[str],
    test_size: float = 0.3,
    n_estimators: int = 100,
    max_depth: int | None = None,
    random_state: int = 42,
) -> ClassificationResult:
    """Fit a random forest classifier."""
    require_numeric_features(df, features, "A random forest")
    clean = df[[target] + features].dropna()
    X = clean[features]
    y = clean[target]

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    classes = le.classes_.tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=test_size, random_state=random_state
    )

    model = RandomForestClassifier(
        n_estimators=n_estimators, max_depth=max_depth, random_state=random_state
    )
    model.fit(X_train, y_train)

    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)

    predictions = pd.Series(le.inverse_transform(model.predict(X_test)), index=X_test.index)

    proba = model.predict_proba(X_test)
    if proba.shape[1] == 2:
        probabilities = pd.Series(proba[:, 1], index=X_test.index)
    else:
        probabilities = pd.Series(proba.max(axis=1), index=X_test.index)

    importance_df = pd.DataFrame({
        "variable": features,
        "importance": np.round(model.feature_importances_, 4),
    }).sort_values("importance", ascending=False)

    feats_str = repr(features)
    depth_str = f", max_depth={max_depth}" if max_depth is not None else ""
    code = (
        f'from sklearn.ensemble import RandomForestClassifier\n'
        f'from sklearn.model_selection import train_test_split\n'
        f'from sklearn.preprocessing import LabelEncoder\n\n'
        f'X = df[{feats_str}].dropna()\n'
        f'y = LabelEncoder().fit_transform(df["{target}"].loc[X.index])\n'
        f'X_train, X_test, y_train, y_test = train_test_split(X, y, test_size={test_size}, random_state={random_state})\n'
        f'model = RandomForestClassifier(n_estimators={n_estimators}{depth_str}, random_state={random_state}).fit(X_train, y_train)\n'
        f'print(f"Train accuracy: {{model.score(X_train, y_train):.3f}}")\n'
        f'print(f"Test accuracy: {{model.score(X_test, y_test):.3f}}")'
    )

    return ClassificationResult(
        model_type="Random Forest",
        feature_importance=importance_df,
        train_accuracy=round(train_acc, 4),
        test_accuracy=round(test_acc, 4),
        predictions=predictions,
        probabilities=probabilities,
        classes=classes,
        code=CodeSnippet(
            code=code,
            imports=[
                "from sklearn.ensemble import RandomForestClassifier",
                "from sklearn.model_selection import train_test_split",
                "from sklearn.preprocessing import LabelEncoder",
            ],
        ),
        model=model,
        label_encoder=le,
        feature_names=features,
        X_train=X_train,
        X_test=X_test,
        y_train=pd.Series(y_train, name=target),
        y_test=pd.Series(y_test, name=target),
    )
