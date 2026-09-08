"""Clustering — K-means and hierarchical with profiling."""

from __future__ import annotations

from dataclasses import dataclass, field

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from pyanalytica.core.codegen import CodeSnippet
from pyanalytica.model._validate import require_numeric_features

Figure = matplotlib.figure.Figure


@dataclass
class ClusterResult:
    """Result of a clustering analysis."""
    labels: pd.Series
    n_clusters: int
    elbow_plot: Figure | None = None
    silhouette_scores: list[float] = field(default_factory=list)
    cluster_profiles: pd.DataFrame = field(default_factory=pd.DataFrame)
    scatter_plot: Figure | None = None
    code: CodeSnippet = field(default_factory=lambda: CodeSnippet(code=""))


def kmeans_cluster(
    df: pd.DataFrame,
    features: list[str],
    k_range: range = range(2, 11),
    chosen_k: int | None = None,
    diagnostics: bool = True,
) -> ClusterResult:
    """K-means clustering with elbow plot and silhouette analysis.

    Set *diagnostics* to False to skip the figures and, with them, the sweep
    behind the elbow plot: a k-means fit and a silhouette score at every k in
    *k_range*. Silhouette is O(n^2), so on a large frame that sweep is the
    whole cost of the panel. It is only needed to draw the elbow, or to choose
    k when *chosen_k* is None.
    """
    require_numeric_features(df, features, "K-means clustering")
    clean = df[features].dropna()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(clean)

    # The sweep exists to draw the elbow and, failing an explicit k, to pick
    # one. Skip it when neither is wanted.
    inertias: list[float] = []
    sil_scores: list[float] = []
    sweep = diagnostics or chosen_k is None
    for k in (k_range if sweep else []):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)
        if k >= 2:
            sil_scores.append(round(silhouette_score(X_scaled, km.labels_), 4))
        else:
            sil_scores.append(0.0)

    fig_elbow = None
    if diagnostics:
        fig_elbow, ax = plt.subplots(figsize=(8, 5))
        ax.plot(list(k_range), inertias, "bo-", linewidth=2)
        ax.set_xlabel("Number of Clusters (k)")
        ax.set_ylabel("Inertia (Within-cluster Sum of Squares)")
        ax.set_title("Elbow Plot")
        fig_elbow.set_layout_engine("tight")

    # Choose k
    if chosen_k is None:
        chosen_k = list(k_range)[np.argmax(sil_scores)]

    # Final model
    km_final = KMeans(n_clusters=chosen_k, random_state=42, n_init=10)
    labels = pd.Series(km_final.fit_predict(X_scaled), index=clean.index, name="cluster")

    # Cluster profiles
    profile_df = clean.copy()
    profile_df["cluster"] = labels
    profiles = profile_df.groupby("cluster").mean().round(4)

    # Scatter plot (first 2 features)
    fig_scatter = None
    if diagnostics and len(features) >= 2:
        fig_scatter, ax2 = plt.subplots(figsize=(8, 6))
        scatter = ax2.scatter(
            X_scaled[:, 0], X_scaled[:, 1],
            c=labels, cmap="viridis", alpha=0.6
        )
        ax2.set_xlabel(f"{features[0]} (scaled)")
        ax2.set_ylabel(f"{features[1]} (scaled)")
        ax2.set_title(f"K-Means Clusters (k={chosen_k})")
        plt.colorbar(scatter, ax=ax2, label="Cluster")
        fig_scatter.set_layout_engine("tight")

    feats_str = repr(features)
    code = (
        f'from sklearn.cluster import KMeans\n'
        f'from sklearn.preprocessing import StandardScaler\n\n'
        f'X = df[{feats_str}].dropna()\n'
        f'X_scaled = StandardScaler().fit_transform(X)\n'
        f'km = KMeans(n_clusters={chosen_k}, random_state=42, n_init=10)\n'
        f'df["cluster"] = km.fit_predict(X_scaled)\n'
        f'print(df.groupby("cluster")[{feats_str}].mean())'
    )

    return ClusterResult(
        labels=labels,
        n_clusters=chosen_k,
        elbow_plot=fig_elbow,
        silhouette_scores=sil_scores,
        cluster_profiles=profiles,
        scatter_plot=fig_scatter,
        code=CodeSnippet(code=code, imports=[
            "from sklearn.cluster import KMeans",
            "from sklearn.preprocessing import StandardScaler",
        ]),
    )


def hierarchical_cluster(
    df: pd.DataFrame,
    features: list[str],
    n_clusters: int = 3,
) -> ClusterResult:
    """Hierarchical (agglomerative) clustering."""
    require_numeric_features(df, features, "Hierarchical clustering")
    clean = df[features].dropna()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(clean)

    model = AgglomerativeClustering(n_clusters=n_clusters)
    labels = pd.Series(model.fit_predict(X_scaled), index=clean.index, name="cluster")

    sil = round(silhouette_score(X_scaled, labels), 4) if n_clusters >= 2 else 0.0

    profile_df = clean.copy()
    profile_df["cluster"] = labels
    profiles = profile_df.groupby("cluster").mean().round(4)

    # Scatter plot
    fig_scatter = None
    if len(features) >= 2:
        fig_scatter, ax = plt.subplots(figsize=(8, 6))
        scatter = ax.scatter(X_scaled[:, 0], X_scaled[:, 1], c=labels, cmap="viridis", alpha=0.6)
        ax.set_xlabel(f"{features[0]} (scaled)")
        ax.set_ylabel(f"{features[1]} (scaled)")
        ax.set_title(f"Hierarchical Clusters (n={n_clusters})")
        plt.colorbar(scatter, ax=ax, label="Cluster")
        fig_scatter.set_layout_engine("tight")

    feats_str = repr(features)
    code = (
        f'from sklearn.cluster import AgglomerativeClustering\n'
        f'from sklearn.preprocessing import StandardScaler\n\n'
        f'X = df[{feats_str}].dropna()\n'
        f'X_scaled = StandardScaler().fit_transform(X)\n'
        f'model = AgglomerativeClustering(n_clusters={n_clusters})\n'
        f'df["cluster"] = model.fit_predict(X_scaled)\n'
        f'print(df.groupby("cluster")[{feats_str}].mean())'
    )

    return ClusterResult(
        labels=labels,
        n_clusters=n_clusters,
        silhouette_scores=[sil],
        cluster_profiles=profiles,
        scatter_plot=fig_scatter,
        code=CodeSnippet(code=code, imports=[
            "from sklearn.cluster import AgglomerativeClustering",
            "from sklearn.preprocessing import StandardScaler",
        ]),
    )
