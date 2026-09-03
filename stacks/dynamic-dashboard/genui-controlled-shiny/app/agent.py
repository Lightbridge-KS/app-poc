"""The LLM side: two chatlas tools whose parameter schema *is* the Pydantic PlotSpec.

`make_chat(store)` builds a chatlas Chat whose tools validate the model's arguments
through the same TypeAdapters the config-driven stack uses, build the output with the
same polars pipeline, push a Card into `store`, and hand the model one sentence back.
The model never sees rows — only the schema, and the summary.

`turn(prompt)` is what `scripts/prove.py` calls: a fresh chat per prompt, no history,
exactly what the nextjs stack's `prove` sends.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chatlas import Chat, ChatOpenAI, ContentToolRequest, Tool
from dotenv import load_dotenv
from pydantic import ValidationError

from app.catalog.build import build_bar, build_scatter
from app.catalog.datasets import DATASETS
from app.catalog.schema import BarSpecAdapter, ScatterSpecAdapter

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-terra")


def _describe_dataset(name: str) -> str:
    d = DATASETS[name]
    return f"- {name}: {d.label}. numeric: {', '.join(d.numeric)}. categorical: {', '.join(d.categorical)}."


# Verbatim port of genui-controlled-nextjs/src/catalog/systemPrompt.ts, so the only
# variables between the two stacks are language, SDK and provider API path.
SYSTEM_PROMPT = f"""You are the plot builder for a small analytics dashboard. You can do exactly two things:
add a scatter plot card (scatter_plot) or a bar plot card (bar_plot). Two datasets exist:
{_describe_dataset("penguins")}
{_describe_dataset("mtcars")}

Rules:
- One requested plot = one tool call. Do not write prose when you call a tool; the card captions itself.
- Add filters only when the user asks for a subset. Use op "in" with a list for several category values.
- For "how many" / "count" use measure {{op:"count"}}; for "average"/"mean" or "median" name the column.
- If the request cannot be met with these two builders over these columns (another chart type, another dataset, a table, statistics, modelling or prediction, colours, layout), refuse in one or two plain sentences: say what you cannot do and what you can. Never approximate an unsupported request with a supported plot.
- Never invent columns. If the user names one that does not exist, say so and list the real ones."""

TOOL_DESCRIPTIONS = {
    "scatter_plot": (
        "Add a scatter plot card to the dashboard: one numeric column against another, "
        "optionally coloured by a category."
    ),
    "bar_plot": (
        "Add a bar plot card to the dashboard: one bar per category level, "
        "height = row count or mean/median of a numeric column."
    ),
}


@dataclass
class Card:
    output: dict[str, Any]
    source: str  # "file" | "chat"
    title: str | None = None


def to_openai_params(schema: dict[str, Any]) -> dict[str, Any]:
    """The PlotSpec JSON Schema, as OpenAI's function validator will take it.

    Pydantic says `oneOf` + `discriminator` for a discriminated union; OpenAI rejects `oneOf`
    at the root ("'oneOf' is not permitted"), accepts `anyOf`, and insists the root carries
    `type: "object"`. Optional fields stay optional (no required-or-null rewrite), so the
    model omits them the way it did through the AI SDK. Same vocabulary, different keywords;
    `strict` must be off for a union root at all."""

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            return {("anyOf" if k == "oneOf" else k): walk(v) for k, v in node.items() if k != "discriminator"}
        if isinstance(node, list):
            return [walk(x) for x in node]
        return node

    out = walk(schema)
    out.setdefault("type", "object")  # OpenAI: the root must say type object, even with anyOf branches
    return out


def make_tools(store: list[Card]) -> list[Tool]:
    """Two tools that append to `store` and return only the summary to the model."""

    def scatter_plot(**args: Any) -> str:
        try:
            spec = ScatterSpecAdapter.validate_python(args).model_dump(exclude_none=True)
        except ValidationError as e:  # a second line of defence after the provider's schema check
            return f"Rejected: {e.errors()[0]['msg']}"
        out = build_scatter(spec)
        store.append(Card(out, source="chat"))
        return out["summary"]

    def bar_plot(**args: Any) -> str:
        try:
            spec = BarSpecAdapter.validate_python(args).model_dump(exclude_none=True)
        except ValidationError as e:
            return f"Rejected: {e.errors()[0]['msg']}"
        out = build_bar(spec)
        store.append(Card(out, source="chat"))
        return out["summary"]

    return [
        Tool(
            func=scatter_plot,
            name="scatter_plot",
            description=TOOL_DESCRIPTIONS["scatter_plot"],
            parameters=to_openai_params(ScatterSpecAdapter.json_schema()),
            strict=False,  # chatlas defaults to strict; OpenAI strict mode forbids a union at the root
        ),
        Tool(
            func=bar_plot,
            name="bar_plot",
            description=TOOL_DESCRIPTIONS["bar_plot"],
            parameters=to_openai_params(BarSpecAdapter.json_schema()),
            strict=False,
        ),
    ]


def make_chat(store: list[Card]) -> Chat:
    key = os.environ.get("OPENAI_API_KEY") or None
    chat = ChatOpenAI(system_prompt=SYSTEM_PROMPT, model=MODEL, reasoning="low", api_key=key)
    # chatlas 0.22: register_tool(Tool) re-derives the schema from the function signature
    # (losing the union), and register_tool(func, model=RootModel) refuses a root field.
    # So the Tool is placed in the chat's table directly; nothing else is bypassed.
    for tool in make_tools(store):
        chat._tools[tool.name] = tool  # noqa: SLF001
    return chat


@dataclass
class Turn:
    tools: list[tuple[str, dict[str, Any]]]  # raw arguments as the model sent them
    specs: list[tuple[str, dict[str, Any]]]  # the same, validated through the PlotSpec (nulls dropped)
    text: str
    ms: int
    cards: list[Card]
    raw_nulls: bool  # did the model spell out `null` for optional fields?


_ADAPTERS = {"scatter_plot": ScatterSpecAdapter, "bar_plot": BarSpecAdapter}


def _validated(name: str, args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _ADAPTERS[name].validate_python(args).model_dump(exclude_none=True)
    except (KeyError, ValidationError):
        return args


def turn(prompt: str) -> Turn:
    """One prompt on a fresh chat: which tools were called with what, and what was said."""
    store: list[Card] = []
    chat = make_chat(store)
    t0 = time.perf_counter()
    response = chat.chat(prompt, echo="none", stream=False)
    ms = round((time.perf_counter() - t0) * 1000)
    calls: list[tuple[str, dict[str, Any]]] = []
    for t in chat.get_turns():
        if t.role != "assistant":
            continue
        for c in t.contents:
            if isinstance(c, ContentToolRequest):
                calls.append((c.name, dict(c.arguments) if isinstance(c.arguments, dict) else {"_": c.arguments}))
    text = getattr(response, "content", None) or str(response)
    specs = [(n, _validated(n, a)) for n, a in calls]
    raw_nulls = any(v is None for _, a in calls for v in a.values())
    return Turn(tools=calls, specs=specs, text=text.strip(), ms=ms, cards=store, raw_nulls=raw_nulls)
