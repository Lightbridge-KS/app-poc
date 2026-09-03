"""Fixed look: same palette and layout values as `theme.ts` in the nextjs stack."""

from __future__ import annotations

from typing import Any

# Colour-blind-safe categorical palette (Okabe–Ito). The config author has no say in colours.
PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#999999"]


def base_layout(title: str) -> dict[str, Any]:
    return {
        "title": {"text": title, "font": {"size": 14}, "x": 0.02},
        "margin": {"l": 56, "r": 16, "t": 44, "b": 72},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "ui-sans-serif, system-ui, sans-serif", "size": 12},
        "legend": {"orientation": "h", "y": -0.32, "yanchor": "top"},
        "hovermode": "closest",
    }
