"""The dashboard's three views of the penguins data.

Pure ``plotly.graph_objects``: each builder takes a polars frame and returns a
``go.Figure``. Knows nothing about Dash or callbacks, so any of these can be
built and eyeballed from a plain script or a notebook.

Columns are pulled out with ``.to_list()`` — Plotly serialises plain Python
lists straight to JSON, so neither pandas nor numpy is needed anywhere.

One trace **per species** rather than one trace coloured by species: that is what
makes the legend a species toggle and keeps each species' colour stable as the
sidebar filters change.
"""

from __future__ import annotations

import plotly.graph_objects as go
import polars as pl

import penguins as pg

#: The palette Allison Horst uses for the original palmerpenguins artwork.
SPECIES_COLORS = {"Adelie": "#FF8C00", "Chinstrap": "#A034F0", "Gentoo": "#159090"}

_MARGIN = dict(l=60, r=20, t=50, b=50)


def _present(df: pl.DataFrame) -> list[str]:
    """Species actually in ``df``, in the canonical order.

    Iterating this rather than every known species keeps the legend honest: a
    species filtered out of the frame does not linger as an empty legend entry.
    """
    here = set(df["species"].unique().to_list())
    return [s for s in pg.SPECIES if s in here]


def _base(fig: go.Figure, *, title: str, height: int) -> go.Figure:
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=height,
        margin=_MARGIN,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hovermode="closest",
    )
    return fig


def bill_scatter(df: pl.DataFrame, *, smoother: bool = False) -> go.Figure:
    """Bill length against depth, by species — the brushable plot.

    The reason this is the canonical penguins plot: pooled across species the
    two measurements correlate negatively, but within every species the
    correlation is positive — Simpson's paradox, visible at a glance. Turn the
    smoother on to see the per-species fits.

    Every point carries its ``row_id`` as ``customdata[0]``. That is what the
    cross-filter callback reads back out of ``selectedData``: selections are
    expressed as row ids, never as positions in this frame.
    """
    fig = go.Figure()

    for species in _present(df):
        sub = df.filter(pl.col("species") == species)
        fig.add_trace(
            go.Scatter(
                x=sub["bill_length_mm"].to_list(),
                y=sub["bill_depth_mm"].to_list(),
                mode="markers",
                name=species,
                marker=dict(size=9, color=SPECIES_COLORS[species], opacity=0.85),
                # Dimming rather than hiding: the unselected points stay on
                # screen as context for whatever was brushed.
                selected=dict(marker=dict(opacity=1.0)),
                unselected=dict(marker=dict(opacity=0.12)),
                customdata=list(
                    zip(
                        sub["row_id"].to_list(),
                        sub["island"].to_list(),
                        sub["sex"].fill_null("unknown").to_list(),
                        sub["body_mass_g"].to_list(),
                    )
                ),
                hovertemplate=(
                    "<b>%{fullData.name}</b> · %{customdata[1]}<br>"
                    "Bill %{x:.1f} × %{y:.1f} mm<br>"
                    "Mass %{customdata[3]:,} g · %{customdata[2]}"
                    "<extra></extra>"
                ),
            )
        )

    if smoother:
        for species in _present(df):
            sub = df.filter(pl.col("species") == species)
            fit = pg.fit_line(sub, "bill_length_mm", "bill_depth_mm")
            if fit is None:
                continue
            slope, intercept = fit
            lo, hi = sub["bill_length_mm"].min(), sub["bill_length_mm"].max()
            fig.add_trace(
                go.Scatter(
                    x=[lo, hi],
                    y=[slope * lo + intercept, slope * hi + intercept],
                    mode="lines",
                    line=dict(color=SPECIES_COLORS[species], width=2, dash="dash"),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    fig.update_xaxes(title_text="Bill length (mm)")
    fig.update_yaxes(title_text="Bill depth (mm)")
    # Box-select as the default drag tool: cross-filtering is undiscoverable if
    # the user has to find it in the mode bar first.
    fig.update_layout(dragmode="select")
    return _base(fig, title="Bill dimensions by species", height=420)


def mass_histogram(df: pl.DataFrame, *, bins: int = 25) -> go.Figure:
    """Overlaid body-mass histograms — shows how far Gentoo sit from the others."""
    fig = go.Figure()

    for species in _present(df):
        sub = df.filter(pl.col("species") == species)
        fig.add_trace(
            go.Histogram(
                x=sub["body_mass_g"].to_list(),
                name=species,
                nbinsx=bins,
                marker=dict(color=SPECIES_COLORS[species], line=dict(color="white", width=1)),
                opacity=0.7,
                hovertemplate="<b>%{fullData.name}</b><br>%{x} g<br>%{y} penguins<extra></extra>",
            )
        )

    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title_text="Body mass (g)")
    fig.update_yaxes(title_text="Count")
    return _base(fig, title="Body mass distribution", height=420)


def flipper_box(df: pl.DataFrame) -> go.Figure:
    """Flipper length per species, with the raw points jittered over the boxes.

    The jitter is deliberate: a box plot alone hides how many observations are
    behind each summary, which matters once the sidebar filters bite. Plotly's
    built-in ``boxpoints``/``jitter`` replaces the sibling's separate jitter layer.
    """
    fig = go.Figure()

    for species in _present(df):
        sub = df.filter(pl.col("species") == species)
        fig.add_trace(
            go.Box(
                y=sub["flipper_length_mm"].to_list(),
                name=species,
                marker=dict(color=SPECIES_COLORS[species]),
                boxpoints="all",
                jitter=0.4,
                pointpos=0,
                opacity=0.75,
                showlegend=False,
            )
        )

    fig.update_xaxes(title_text="Species")
    fig.update_yaxes(title_text="Flipper length (mm)")
    return _base(fig, title="Flipper length by species", height=380)
