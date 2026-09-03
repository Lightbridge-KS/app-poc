"""The dashboard: a chat pane that appends cards to a grid seeded from cards.yaml.

Two fillers, one surface. File cards come from `load_dashboard(cards.yaml)` at session
start; chat cards come from the tools in `agent.py` as the model calls them. Each card
wears a badge saying which. This is the only Shiny-aware file.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import plotly
from shiny import App, reactive, render, ui

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from chatlas import Chat  # noqa: E402

from app.agent import Card, make_chat  # noqa: E402
from app.builders.bar import bar_figure  # noqa: E402
from app.builders.scatter import scatter_figure  # noqa: E402
from app.catalog.build import build, describe  # noqa: E402
from app.catalog.config import ErrorCard, load_dashboard  # noqa: E402

CARDS_YAML = Path(os.environ.get("CARDS_YAML", ROOT / "cards.yaml"))
PLOTLY_JS_DIR = Path(plotly.__file__).parent / "package_data"

GREETING = (
    "Ask for a **scatter** or **bar** plot over **penguins** or **mtcars**. "
    "Try: *median body mass by species split by sex*."
)

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.chat_ui("chat"),
        width=380,
        title="Controlled generative UI",
    ),
    ui.head_content(ui.tags.script(src="/plotly/plotly.min.js")),
    ui.output_ui("grid"),
    title="genui-controlled — dynamic dashboard PoC",
)


def server(input, output, session):  # noqa: ARG001
    seed = load_dashboard(CARDS_YAML)
    file_cards = [Card(build(c), source="file", title=c.title) for c in seed.ok]  # type: ignore[attr-defined]
    cards = reactive.Value[list[Card]](file_cards)
    errors = [c for c in seed.cards if isinstance(c, ErrorCard)]

    store: list[Card] = []  # the tools append here during a stream (plain list: no reactive reads in a task)
    llm: dict[str, Chat] = {}  # built on first use, so a missing key is a chat message, not a crash
    chat = ui.Chat(id="chat")

    @reactive.effect
    async def _greet():
        await chat.append_message(GREETING)

    @chat.on_user_submit
    async def _on_submit(user_input: str):
        if "chat" not in llm:
            try:
                llm["chat"] = make_chat(store)
            except Exception as e:  # e.g. openai.OpenAIError: Missing credentials
                await chat.append_message(
                    f"⚠️ Cannot start the model: {e}\n\nPaste `OPENAI_API_KEY` into `.env` and restart `just dev`."
                )
                return
        stream = await llm["chat"].stream_async(user_input, content="all")
        await chat.append_message_stream(stream)

    @reactive.effect
    def _sync_cards():
        # The stream runs as an extended task; when it finishes, move what the tools
        # stored into the reactive card list. This is the only place `cards` is written.
        if chat.latest_message_stream.status() == "success" and store:
            with reactive.isolate():
                cards.set(cards() + store[:])
            store.clear()

    @render.ui
    def grid():
        current = cards()
        n_file = sum(c.source == "file" for c in current)
        n_chat = len(current) - n_file
        return ui.TagList(
            ui.div(
                ui.h3(seed.title, class_="mb-0"),
                ui.tags.small(f"{n_file} from {CARDS_YAML.name} · {n_chat} from chat", class_="text-muted"),
                class_="mb-3",
            ),
            *[ui.div("; ".join(e.messages), class_="alert alert-danger") for e in errors],
            ui.layout_columns(*[_card_ui(i, c) for i, c in enumerate(current)], col_widths=6),
        )


def _card_ui(i: int, card: Card) -> ui.Tag:
    out = card.output
    fig = scatter_figure(out, card.title) if out["kind"] == "scatter" else bar_figure(out, card.title)
    html = fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        div_id=f"plot-{i}",
        default_height=320,
        config={"displayModeBar": False, "responsive": True},
    )
    badge_class = "text-bg-primary" if card.source == "chat" else "text-bg-secondary"
    return ui.card(
        ui.card_header(
            ui.span(card.source, class_=f"badge {badge_class} me-2"),
            ui.tags.code(describe(out), class_="small"),
        ),
        ui.HTML(html),
        ui.tags.details(
            ui.tags.summary("spec", class_="small text-muted"),
            ui.tags.pre(json.dumps(out["spec"], indent=2), class_="small mb-0"),
        ),
        **{"data-card": out["kind"], "data-source": card.source},
    )


app = App(app_ui, server, static_assets={"/plotly": PLOTLY_JS_DIR})
