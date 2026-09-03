"""ScatterOutput → Plotly figure. Pure; the card just renders what this returns."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from .theme import PALETTE, base_layout


def scatter_figure(out: dict[str, Any], title: str | None = None) -> go.Figure:
    spec, points = out["spec"], out["points"]
    groups: dict[str, list[dict[str, Any]]] = {}
    for p in points:
        groups.setdefault(p["color"] or "all", []).append(p)
    has_label = bool(points) and points[0]["label"] is not None
    fig = go.Figure()
    for i, (name, pts) in enumerate(groups.items()):
        fig.add_trace(
            go.Scatter(
                mode="markers",
                name=name,
                x=[p["x"] for p in pts],
                y=[p["y"] for p in pts],
                text=[p["label"] or "" for p in pts],
                hovertemplate=(
                    f"{spec['x']}=%{{x}}<br>{spec['y']}=%{{y}}{'<br>%{text}' if has_label else ''}<extra>{name}</extra>"
                ),
                marker={"color": PALETTE[i % len(PALETTE)], "size": 8, "opacity": 0.8},
            )
        )
    fig.update_layout(
        **base_layout(title or f"{spec['y']} vs {spec['x']}"),
        xaxis={"title": {"text": spec["x"]}, "zeroline": False},
        yaxis={"title": {"text": spec["y"]}, "zeroline": False},
        showlegend=spec.get("color") is not None,
    )
    return fig
