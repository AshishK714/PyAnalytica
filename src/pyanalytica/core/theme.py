"""Color palettes and plot defaults for the workbench."""

from __future__ import annotations

from dataclasses import dataclass, field

import matplotlib as mpl
import matplotlib.pyplot as plt


@dataclass
class Theme:
    """A visual theme for the workbench."""
    name: str
    palette: list[str]                # Ordered color list for plots
    background: str = "#ffffff"
    font_family: str = "sans-serif"
    categorical_palette: list[str] = field(default_factory=list)
    sequential_palette: str = "YlOrRd"      # matplotlib colormap name
    diverging_palette: str = "RdBu_r"

    def __post_init__(self):
        if not self.categorical_palette:
            self.categorical_palette = self.palette


# IBM Design Library colorblind-safe palette, ordered for contrast. Most
# coloured charts in a course split by two groups (smoker or not, male or
# female), and in the library's own order the first two are blue and
# violet, which blend where bars overlap. Blue then orange is the most
# distinct pair in the set, for colour-blind readers too; magenta and
# yellow follow before the violet.
DEFAULT_THEME = Theme(
    name="default",
    palette=[
        "#648FFF", "#FE6100", "#DC267F", "#FFB000", "#785EF0",
        "#009E73", "#56B4E9", "#E69F00", "#0072B2", "#D55E00",
    ],
    background="#ffffff",
    font_family="sans-serif",
    sequential_palette="YlOrRd",
    diverging_palette="RdBu_r",
)

GIES_THEME = Theme(
    name="gies",
    palette=[
        "#13294B", "#E84A27", "#009FD4", "#7A003C", "#F5821F",
        "#6C757D", "#1D428A", "#C8102E", "#FFB81C", "#00843D",
    ],
    background="#ffffff",
    font_family="sans-serif",
    sequential_palette="Oranges",
    diverging_palette="RdBu_r",
)

MINIMAL_THEME = Theme(
    name="minimal",
    palette=[
        "#333333", "#666666", "#999999", "#BBBBBB", "#DDDDDD",
        "#444444", "#777777", "#AAAAAA", "#CCCCCC", "#EEEEEE",
    ],
    background="#ffffff",
    font_family="serif",
    sequential_palette="Greys",
    diverging_palette="Greys",
)

_THEMES: dict[str, Theme] = {
    "default": DEFAULT_THEME,
    "gies": GIES_THEME,
    "minimal": MINIMAL_THEME,
}

_current_theme: Theme = DEFAULT_THEME


def get_theme(name: str = "default") -> Theme:
    """Get a theme by name."""
    if name not in _THEMES:
        raise ValueError(f"Unknown theme '{name}'. Available: {list(_THEMES.keys())}")
    return _THEMES[name]


def register_theme(theme: Theme) -> None:
    """Register a custom theme."""
    _THEMES[theme.name] = theme


def apply_theme(theme: Theme | None = None) -> None:
    """Apply a theme to matplotlib rcParams."""
    global _current_theme
    if theme is None:
        theme = DEFAULT_THEME
    _current_theme = theme

    mpl.rcParams.update({
        "figure.facecolor": theme.background,
        "axes.facecolor": theme.background,
        "font.family": theme.font_family,
        "axes.prop_cycle": plt.cycler(color=theme.palette),
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 150,
        "savefig.dpi": 150,
    })


def current_theme() -> Theme:
    """Return the currently active theme."""
    return _current_theme


# Apply default theme at import time so DPI and style take effect automatically
apply_theme()
