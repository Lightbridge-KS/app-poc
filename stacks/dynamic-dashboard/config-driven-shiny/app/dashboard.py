"""The dashboard. This is the only file that knows Shiny exists.

`cards.yaml` is read by a `reactive.file_reader`, validated card by card, built with
the catalog, and laid out. Edit the file while the app runs and the page follows within
a second. Plotly's JS is served from the installed `plotly` package — no CDN.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import plotly
from shiny import App, reactive, render, ui

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.builders.bar import bar_figure  # noqa: E402
from app.builders.scatter import scatter_figure  # noqa: E402
from app.catalog.build import build, describe  # noqa: E402
from app.catalog.config import ErrorCard, load_dashboard  # noqa: E402

CARDS_YAML = Path(os.environ.get("CARDS_YAML", ROOT / "cards.yaml"))
PLOTLY_JS_DIR = Path(plotly.__file__).parent / "package_data"

app_ui = ui.page_fluid(
    ui.head_content(ui.tags.script(src="/plotly/plotly.min.js")),
    ui.output_ui("dashboard"),
    title="config-driven — dynamic dashboard PoC",
    class_="py-3",
)


def server(input, output, session):  # noqa: ARG001
    @reactive.file_reader(CARDS_YAML, interval_secs=1)
    def config():
        return load_dashboard(CARDS_YAML)

    @render.ui
    def dashboard():
        dash = config()
        cards = [_card_ui(i, c) for i, c in enumerate(dash.cards)]
        return ui.TagList(
            ui.div(
                ui.h3(dash.title, class_="mb-0"),
                ui.tags.small(
                    f"{CARDS_YAML.name} · {len(dash.ok)} cards · {len(dash.errors)} errors", class_="text-muted"
                ),
                class_="mb-3",
            ),
            *[ui.div(m, class_="alert alert-danger") for m in dash.header_errors],
            ui.layout_columns(*cards, col_widths=12 // dash.columns)
            if cards
            else ui.p("No cards in the file.", class_="text-muted"),
        )


def _card_ui(i: int, card) -> ui.Tag:
    if isinstance(card, ErrorCard):
        return ui.card(
            ui.card_header(ui.tags.code(f"✗ card {i}: not rendered"), class_="bg-danger-subtle"),
            ui.tags.pre("\n".join(card.messages), class_="small mb-0"),
            **{"data-card": "error"},
        )
    out = build(card)
    fig = scatter_figure(out, card.title) if out["kind"] == "scatter" else bar_figure(out, card.title)
    html = fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        div_id=f"plot-{i}",
        default_height=320,
        config={"displayModeBar": False, "responsive": True},
    )
    return ui.card(
        ui.card_header(ui.tags.code(describe(out), class_="small")),
        ui.HTML(html),
        **{"data-card": out["kind"]},
    )


app = App(app_ui, server, static_assets={"/plotly": PLOTLY_JS_DIR})
