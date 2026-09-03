"""Hermetic checks on the tool layer: the schema the model receives, and what the tools do with arguments."""

import json
from pathlib import Path

from app.agent import SYSTEM_PROMPT, make_tools
from app.catalog.contract import vocabulary

FIXTURES = Path(__file__).parent.parent / "fixtures"
NEXTJS = {t["name"]: t["inputSchema"] for t in json.loads((FIXTURES / "nextjs-catalog.json").read_text())}


def _tools():
    store = []
    return store, {t.name: t for t in make_tools(store)}


def test_tool_schema_vocabulary_equals_nextjs_catalog() -> None:
    _, tools = _tools()
    for name in ("scatter_plot", "bar_plot"):
        params = tools[name].schema["function"]["parameters"]
        assert vocabulary(params) == vocabulary(NEXTJS[name]), name


def test_tool_descriptions_match_nextjs() -> None:
    _, tools = _tools()
    for name in ("scatter_plot", "bar_plot"):
        assert tools[name].schema["function"]["description"] == next(
            t["description"] for t in json.loads((FIXTURES / "nextjs-catalog.json").read_text()) if t["name"] == name
        )


def test_valid_arguments_build_a_card_and_return_only_the_summary() -> None:
    store, tools = _tools()
    reply = tools["bar_plot"].func(dataset="mtcars", by="cyl", measure={"op": "mean", "column": "mpg"})
    assert reply == "Rendered bar of mtcars: mean mpg by cyl, 3 bars from 32/32 rows."
    assert len(store) == 1 and store[0].source == "chat"
    assert [round(b["value"], 2) for b in store[0].output["bars"]] == [26.66, 19.74, 15.1]


def test_unknown_column_is_rejected_before_building() -> None:
    store, tools = _tools()
    reply = tools["scatter_plot"].func(dataset="mtcars", x="weight", y="hp")
    assert reply.startswith("Rejected:")
    assert store == []


def test_system_prompt_names_both_tools_and_datasets() -> None:
    for word in ("scatter_plot", "bar_plot", "penguins", "mtcars", "refuse"):
        assert word in SYSTEM_PROMPT
