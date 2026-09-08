"""Dimensionality reduction — PCA with scree plot and biplot."""

from __future__ import annotations

from dataclasses import dataclass, field

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from pyanalytica.core.codegen import CodeSnippet
from pyanalytica.model._validate import require_numeric_features

Figure = matplotlib.figure.Figure


@dataclass
class PCAResult:
    """Result of a PCA analysis."""
    components: pd.DataFrame
    explained_variance: list[float]
    cumulative_variance: list[float]
    loadings: pd.DataFrame
    scree_plot: Figure | None = None
    biplot: Figure | None = None
    recommended_n: int = 2
    code: CodeSnippet = field(default_factory=lambda: CodeSnippet(code=""))


def pca_analysis(
    df: pd.DataFrame,
    features: list[str],
    n_components: int | None = None,
) -> PCAResult:
    """Perform PCA and return comprehensive results."""
    require_numeric_features(df, features, "PCA")
    clean = df[features].dropna()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(clean)

    max_comp = min(len(features), len(clean))
    if n_components is None:
        n_components = max_comp

    pca = PCA(n_components=n_components)
    components = pca.fit_transform(X_scaled)

    explained = [round(v, 4) for v in pca.explained_variance_ratio_]
    cumulative = [round(sum(explained[:i+1]), 4) for i in range(len(explained))]

    # Recommended n (>= 80% variance)
    recommended_n = 1
    for i, cv in enumerate(cumulative):
        if cv >= 0.80:
            recommended_n = i + 1
            break
    else:
        recommended_n = len(cumulative)

    # Components DataFrame
    comp_names = [f"PC{i+1}" for i in range(n_components)]
    comp_df = pd.DataFrame(components, index=clean.index, columns=comp_names)

    # Loadings
    loadings_df = pd.DataFrame(
        pca.components_.T,
        index=features,
        columns=comp_names,
    ).round(4)

    # Scree plot
    fig_scree, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    ax1.bar(range(1, len(explained) + 1), [v * 100 for v in explained], alpha=0.7)
    ax1.set_xlabel("Principal Component")
    ax1.set_ylabel("Variance Explained (%)")
    ax1.set_title("Scree Plot")

    ax2.plot(range(1, len(cumulative) + 1), [v * 100 for v in cumulative], "bo-", linewidth=2)
    ax2.axhline(y=80, color="red", linestyle="--", label="80% threshold")
    ax2.set_xlabel("Number of Components")
    ax2.set_ylabel("Cumulative Variance Explained (%)")
    ax2.set_title("Cumulative Variance")
    ax2.legend()
    fig_scree.set_layout_engine("tight")

    # Biplot (PC1 vs PC2)
    fig_biplot = None
    if n_components >= 2:
        fig_biplot, ax = plt.subplots(figsize=(10, 8))
        # Scatter points
        ax.scatter(components[:, 0], components[:, 1], alpha=0.3, s=10)
        # Loading vectors
        scale = max(abs(components[:, 0]).max(), abs(components[:, 1]).max())
        for i, feat in enumerate(features):
            ax.arrow(0, 0,
                     pca.components_[0, i] * scale * 0.8,
                     pca.components_[1, i] * scale * 0.8,
                     head_width=scale * 0.02, head_length=scale * 0.02,
                     fc="red", ec="red", alpha=0.7)
            ax.text(pca.components_[0, i] * scale * 0.9,
                    pca.components_[1, i] * scale * 0.9,
                    feat, fontsize=9, color="red")
        ax.set_xlabel(f"PC1 ({explained[0]*100:.1f}%)")
        ax.set_ylabel(f"PC2 ({explained[1]*100:.1f}%)")
        ax.set_title("PCA Biplot")
        ax.axhline(y=0, color="gray", linestyle="--", alpha=0.3)
        ax.axvline(x=0, color="gray", linestyle="--", alpha=0.3)
        fig_biplot.set_layout_engine("tight")

    feats_str = repr(features)
    n_str = f", n_components={n_components}" if n_components != max_comp else ""
    code = (
        f'from sklearn.decomposition import PCA\n'
        f'from sklearn.preprocessing import StandardScaler\n\n'
        f'X = df[{feats_str}].dropna()\n'
        f'X_scaled = StandardScaler().fit_transform(X)\n'
        f'pca = PCA({n_str.lstrip(", ")})\n'
        f'components = pca.fit_transform(X_scaled)\n'
        f'print("Explained variance ratio:", pca.explained_variance_ratio_.round(3))\n'
        f'print("Cumulative:", pca.explained_variance_ratio_.cumsum().round(3))'
    )

    return PCAResult(
        components=comp_df,
        explained_variance=explained,
        cumulative_variance=cumulative,
        loadings=loadings_df,
        scree_plot=fig_scree,
        biplot=fig_biplot,
        recommended_n=recommended_n,
        code=CodeSnippet(code=code, imports=[
            "from sklearn.decomposition import PCA",
            "from sklearn.preprocessing import StandardScaler",
        ]),
    )
