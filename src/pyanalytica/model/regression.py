"""Linear regression with interpretation and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

from pyanalytica.core.codegen import CodeSnippet
from pyanalytica.model._validate import require_numeric_features

Figure = matplotlib.figure.Figure


@dataclass
class RegressionResult:
    """Result of a linear regression."""
    coefficients: pd.DataFrame
    r_squared: float
    adj_r_squared: float
    f_stat: float
    f_pvalue: float
    vif: pd.DataFrame
    residual_plot: Figure | None = None
    qq_plot: Figure | None = None
    interpretation: str = ""
    predictions: pd.Series | None = None
    code: CodeSnippet = field(default_factory=lambda: CodeSnippet(code=""))
    model: object | None = None
    feature_names: list[str] = field(default_factory=list)
    X_train: pd.DataFrame | None = None
    X_test: pd.DataFrame | None = None
    y_train: pd.Series | None = None
    y_test: pd.Series | None = None
    #: R2 on the held-out rows, None when no split was asked for. The
    #: training figure alone is exactly what a Test Split was set to avoid.
    test_r_squared: float | None = None


def linear_regression(
    df: pd.DataFrame,
    target: str,
    features: list[str],
    test_size: float | None = None,
    random_state: int = 42,
) -> RegressionResult:
    """Fit a linear regression and return comprehensive results."""
    require_numeric_features(df, features, "Linear regression")
    clean = df[[target] + features].dropna()
    X = clean[features]
    y = clean[target]

    predictions = None
    X_test_out = None
    y_test_out = None
    if test_size and test_size > 0:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        X_test_out = X_test
        y_test_out = y_test
        model = LinearRegression()
        model.fit(X_train, y_train)
        predictions = pd.Series(model.predict(X_test), index=X_test.index)
        y_pred_all = model.predict(X)
    else:
        X_train, y_train = X, y
        model = LinearRegression()
        model.fit(X, y)
        y_pred_all = model.predict(X)

    # Out-of-sample R2. Without it the panel answers a Test Split of 0.3
    # with the *training* R2 -- the number the split exists to avoid. On 25
    # columns of pure noise that reads 0.489 where the honest figure is
    # -1.50, and the student who split the data specifically to check is
    # the one most misled by it.
    test_r_sq = None
    if X_test_out is not None and len(X_test_out) > 1:
        test_r_sq = round(float(model.score(X_test_out, y_test_out)), 4)

    n = len(X_train)
    p = len(features)

    # R-squared
    ss_res = np.sum((y_train - model.predict(X_train)) ** 2)
    ss_tot = np.sum((y_train - y_train.mean()) ** 2)
    r_sq = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    adj_r_sq = 1 - (1 - r_sq) * (n - 1) / (n - p - 1) if n > p + 1 else 0

    # F-statistic
    ms_reg = (ss_tot - ss_res) / p if p > 0 else 0
    ms_res = ss_res / (n - p - 1) if n > p + 1 else 1
    f_stat = ms_reg / ms_res if ms_res > 0 else 0
    f_pvalue = 1 - stats.f.cdf(f_stat, p, n - p - 1) if n > p + 1 else 1.0

    # Coefficient table
    coefs = np.concatenate([[model.intercept_], model.coef_])
    names = ["(Intercept)"] + features

    # Standard errors (OLS formula)
    X_with_const = np.column_stack([np.ones(len(X_train)), X_train.values])
    try:
        var_coef = ms_res * np.linalg.inv(X_with_const.T @ X_with_const)
        se = np.sqrt(np.diag(var_coef))
    except np.linalg.LinAlgError:
        se = np.full(len(coefs), np.nan)

    t_vals = coefs / se
    p_vals = 2 * (1 - stats.t.cdf(np.abs(t_vals), n - p - 1))
    ci_lower = coefs - 1.96 * se
    ci_upper = coefs + 1.96 * se

    coef_df = pd.DataFrame({
        "variable": names,
        "coefficient": np.round(coefs, 4),
        "std_error": np.round(se, 4),
        "t_value": np.round(t_vals, 4),
        "p_value": np.round(p_vals, 6),
        "ci_lower": np.round(ci_lower, 4),
        "ci_upper": np.round(ci_upper, 4),
    })

    # VIF
    vif_data = []
    if len(features) > 1:
        from sklearn.linear_model import LinearRegression as LR
        for i, feat in enumerate(features):
            other_feats = [f for j, f in enumerate(features) if j != i]
            r2_i = LR().fit(X_train[other_feats], X_train[feat]).score(X_train[other_feats], X_train[feat])
            vif_val = 1 / (1 - r2_i) if r2_i < 1 else float("inf")
            vif_data.append({"variable": feat, "VIF": round(vif_val, 2)})
    else:
        vif_data = [{"variable": features[0], "VIF": 1.0}]
    vif_df = pd.DataFrame(vif_data)

    # Residual plot
    residuals = y - y_pred_all
    fig_resid, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(y_pred_all, residuals, alpha=0.5)
    ax.axhline(y=0, color="red", linestyle="--")
    ax.set_xlabel("Fitted Values")
    ax.set_ylabel("Residuals")
    ax.set_title("Residuals vs Fitted")
    fig_resid.tight_layout()

    # QQ plot
    fig_qq, ax_qq = plt.subplots(figsize=(8, 5))
    stats.probplot(residuals, dist="norm", plot=ax_qq)
    ax_qq.set_title("Normal Q-Q Plot")
    fig_qq.tight_layout()

    # Interpretation
    if test_r_sq is None:
        interp_parts = [
            f"R\u00b2 = {r_sq:.3f} (Adjusted R\u00b2 = {adj_r_sq:.3f}), "
            f"measured on the same rows the model was fitted to."
        ]
    else:
        interp_parts = [
            f"R\u00b2 = {test_r_sq:.3f} on the {len(X_test_out):,} held-out rows "
            f"({r_sq:.3f} on the {n:,} rows it was trained on). The held-out "
            f"figure is the one that says whether the model generalises."
        ]
    sig_features = coef_df[(coef_df["p_value"] < 0.05) & (coef_df["variable"] != "(Intercept)")]
    for _, row in sig_features.iterrows():
        direction = "increase" if row["coefficient"] > 0 else "decrease"
        interp_parts.append(
            f"A one-unit increase in {row['variable']} is associated with a "
            f"{abs(row['coefficient']):.2f} {direction} in {target}."
        )

    feats_str = repr(features)
    code = (
        f'from sklearn.linear_model import LinearRegression\n'
        f'from sklearn.model_selection import train_test_split\n\n'
        f'X = df[{feats_str}].dropna()\n'
        f'y = df["{target}"].loc[X.index]\n'
    )
    if test_size:
        code += f'X_train, X_test, y_train, y_test = train_test_split(X, y, test_size={test_size}, random_state={random_state})\n'
        code += f'model = LinearRegression().fit(X_train, y_train)\n'
        code += f'print(f"R² = {{model.score(X_test, y_test):.3f}}")'
    else:
        code += f'model = LinearRegression().fit(X, y)\n'
        code += f'print(f"R² = {{model.score(X, y):.3f}}")\n'
        code += f'print("Coefficients:", dict(zip({feats_str}, model.coef_.round(4))))'

    return RegressionResult(
        coefficients=coef_df,
        r_squared=round(r_sq, 4),
        test_r_squared=test_r_sq,
        adj_r_squared=round(adj_r_sq, 4),
        f_stat=round(f_stat, 4),
        f_pvalue=round(f_pvalue, 6),
        vif=vif_df,
        residual_plot=fig_resid,
        qq_plot=fig_qq,
        interpretation=" ".join(interp_parts),
        predictions=predictions,
        code=CodeSnippet(
            code=code,
            imports=[
                "from sklearn.linear_model import LinearRegression",
                "from sklearn.model_selection import train_test_split",
            ],
        ),
        model=model,
        feature_names=features,
        X_train=X_train,
        X_test=X_test_out,
        y_train=y_train,
        y_test=y_test_out,
    )
