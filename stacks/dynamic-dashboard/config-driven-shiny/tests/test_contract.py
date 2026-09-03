"""Two languages, one contract: every enum in the Pydantic PlotSpec equals its Zod twin.

`fixtures/nextjs-catalog.json` is `just catalog` from the sibling stack, vendored.
"""

import json
from pathlib import Path

from app.catalog.contract import vocabulary
from app.catalog.schema import BarSpecAdapter, ScatterSpecAdapter

FIXTURES = Path(__file__).parent.parent / "fixtures"
NEXTJS = {t["name"]: t["inputSchema"] for t in json.loads((FIXTURES / "nextjs-catalog.json").read_text())}


def test_scatter_vocabulary_matches() -> None:
    assert vocabulary(ScatterSpecAdapter.json_schema()) == vocabulary(NEXTJS["scatter_plot"])


def test_bar_vocabulary_matches() -> None:
    assert vocabulary(BarSpecAdapter.json_schema()) == vocabulary(NEXTJS["bar_plot"])


def test_vocabulary_is_nontrivial() -> None:
    v = vocabulary(NEXTJS["scatter_plot"])
    assert set(v) == {"penguins", "mtcars"}
    assert "flipper_length_mm" in v["penguins"]["x"]
    assert v["mtcars"]["op"] == sorted(["==", "!=", ">", ">=", "<", "<=", "in"])
    assert vocabulary(NEXTJS["bar_plot"])["penguins"]["by"] == ["island", "sex", "species"]
