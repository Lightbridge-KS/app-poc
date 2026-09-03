"""BarOutput → Plotly figure. Grouped bars when the spec has a `color` split."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from .theme import PALETTE, base_layout


def bar_figure(out: dict[str, Any], title: str | None = None) -> go.Figure:
    spec, bars = out["spec"], out["bars"]
    m = spec["measure"]
    measure_label = "count" if m["op"] == "count" else f"{m['op']}({m['column']})"
    groups: dict[str, list[dict[str, Any]]] = {}
    for b in bars:
        groups.setdefault(b["group"] or "all", []).append(b)
    fig = go.Figure()
    for i, (name, rows) in enumerate(groups.items()):
        fig.add_trace(
            go.Bar(
                name=name,
                x=[b["category"] for b in rows],
                y=[b["value"] for b in rows],
                customdata=[b["n"] for b in rows],
                hovertemplate=f"{spec['by']}=%{{x}}<br>{measure_label}=%{{y:.2f}}<br>n=%{{customdata}}<extra>{name}</extra>",
                marker={"color": PALETTE[i % len(PALETTE)]},
            )
        )
    fig.update_layout(
        **base_layout(title or f"{measure_label} by {spec['by']}"),
        barmode="group",
        xaxis={"title": {"text": spec["by"]}, "type": "category"},
        yaxis={"title": {"text": measure_label}, "zeroline": True},
        showlegend=spec.get("color") is not None,
    )
    return fig
