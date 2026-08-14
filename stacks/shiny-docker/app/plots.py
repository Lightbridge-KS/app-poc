"""The dashboard's three views of the penguins data.

Pure plotnine: each builder takes a pandas frame and returns a ``ggplot``.
Knows nothing about Shiny or reactivity, so each one can be rendered and eyeballed
from a plain script or a notebook.
"""

from __future__ import annotations

from plotnine import (
    aes,
    geom_boxplot,
    geom_histogram,
    geom_jitter,
    geom_point,
    ggplot,
    labs,
    scale_color_manual,
    scale_fill_manual,
    stat_smooth,
    theme,
    theme_minimal,
)

#: The palette Allison Horst uses for the original palmerpenguins artwork.
SPECIES_COLORS = {"Adelie": "#FF8C00", "Chinstrap": "#A034F0", "Gentoo": "#159090"}

_BASE = theme_minimal() + theme(figure_size=(7, 4.5))


def plot_bill_scatter(df, *, smoother: bool) -> ggplot:
    """Bill length against depth, by species.

    The reason this is the canonical penguins plot: pooled across species the
    two measurements correlate negatively, but within every species the
    correlation is positive — Simpson's paradox, visible at a glance. Turn the
    smoother on to see both fits at once.
    """
    p = (
        ggplot(df, aes("bill_length_mm", "bill_depth_mm", color="species"))
        + geom_point(size=2, alpha=0.8)
        + scale_color_manual(values=SPECIES_COLORS)
        + labs(
            x="Bill length (mm)",
            y="Bill depth (mm)",
            color="Species",
            title="Bill dimensions by species",
        )
        + _BASE
    )
    if smoother:
        p = p + stat_smooth(method="lm", alpha=0.15)
    return p


def plot_mass_distribution(df, *, bins: int) -> ggplot:
    """Overlaid body-mass histograms — shows how far Gentoo sit from the others."""
    return (
        ggplot(df, aes("body_mass_g", fill="species"))
        + geom_histogram(bins=bins, alpha=0.7, position="identity", color="white")
        + scale_fill_manual(values=SPECIES_COLORS)
        + labs(
            x="Body mass (g)",
            y="Count",
            fill="Species",
            title="Body mass distribution",
        )
        + _BASE
    )


def plot_flipper_box(df) -> ggplot:
    """Flipper length per species, with the raw points jittered over the boxes.

    The jitter is deliberate: a box plot alone hides how many observations are
    behind each summary, which matters once the sidebar filters bite.
    """
    return (
        ggplot(df, aes("species", "flipper_length_mm", fill="species"))
        + geom_boxplot(alpha=0.7, outlier_alpha=0)
        + geom_jitter(width=0.18, alpha=0.4, size=1.5)
        + scale_fill_manual(values=SPECIES_COLORS)
        + labs(x="Species", y="Flipper length (mm)", title="Flipper length by species")
        + _BASE
        + theme(legend_position="none")
    )
