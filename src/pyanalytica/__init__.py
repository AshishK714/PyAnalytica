"""PyAnalytica — A Python analytics workbench for teaching data science.

PyAnalytica is a package-first analytics workbench designed for business
school education. It works both as a Shiny web app and as a Python library
in Jupyter notebooks.

Quick start (web app)::

    pyanalytica          # CLI command
    # or
    python -m pyanalytica

Quick start (library)::

    from pyanalytica import load_bundled, profile_dataframe, histogram

    df, code = load_bundled("tips")
    profile = profile_dataframe(df)
    fig, code = histogram(df, "total_bill")
"""

__version__ = "0.8.0"

# Core types
from pyanalytica.core.codegen import CodeSnippet
from pyanalytica.core.types import ColumnType, classify_column, classify_columns

# Data loading and profiling
from pyanalytica.data.load import load_bundled, load_csv, load_excel, load_from_bytes, load_url
from pyanalytica.data.profile import DataProfile, profile_column, profile_dataframe

# Exploration
from pyanalytica.explore.summarize import group_summarize
from pyanalytica.explore.pivot import create_pivot_table
from pyanalytica.explore.crosstab import create_crosstab

# Visualization
from pyanalytica.visualize.distribute import bar_chart, boxplot, histogram, violin
from pyanalytica.visualize.relate import hexbin, scatter
from pyanalytica.visualize.correlate import correlation_matrix, pair_plot

# Statistical analysis
from pyanalytica.analyze.correlation import correlation_test
from pyanalytica.analyze.means import (
    kruskal_wallis_test, mann_whitney_test, one_sample_ttest, one_way_anova, two_sample_ttest,
)
from pyanalytica.analyze.normality import NormalityResult, shapiro_wilk_test
from pyanalytica.analyze.proportions import chi_square_test

# Modeling
from pyanalytica.model.regression import linear_regression
from pyanalytica.model.classify import decision_tree, logistic_regression, random_forest
from pyanalytica.model.cluster import kmeans_cluster
from pyanalytica.model.cross_validate import CrossValidationResult, cross_validate_model
from pyanalytica.model.reduce import pca_analysis

__all__ = [
    # Core
    "CodeSnippet", "ColumnType", "classify_column", "classify_columns",
    # Data
    "load_csv", "load_excel", "load_url", "load_bundled", "load_from_bytes",
    "profile_dataframe", "profile_column", "DataProfile",
    # Explore
    "group_summarize", "create_pivot_table", "create_crosstab",
    # Visualize
    "histogram", "boxplot", "violin", "bar_chart",
    "scatter", "hexbin", "correlation_matrix", "pair_plot",
    # Analyze
    "correlation_test", "one_sample_ttest", "two_sample_ttest",
    "one_way_anova", "mann_whitney_test", "kruskal_wallis_test",
    "shapiro_wilk_test", "NormalityResult", "chi_square_test",
    # Model
    "linear_regression", "logistic_regression", "decision_tree",
    "random_forest", "cross_validate_model", "CrossValidationResult",
    "kmeans_cluster", "pca_analysis",
]
