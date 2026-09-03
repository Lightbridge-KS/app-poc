"""cards.yaml seeds the grid: every card in the file, zero errors, the Run-2 four first."""

from pathlib import Path

from app.agent import Card
from app.catalog.build import build
from app.catalog.config import load_dashboard

ROOT = Path(__file__).parent.parent


def test_seed_yields_four_file_cards() -> None:
    dash = load_dashboard(ROOT / "cards.yaml")
    assert dash.errors == []
    cards = [Card(build(c), source="file", title=c.title) for c in dash.ok]  # type: ignore[attr-defined]
    assert len(cards) == len(dash.ok) >= 4
    assert [c.output["kind"] for c in cards][:4] == ["scatter", "bar", "bar", "scatter"]
    assert cards[1].title == "Fuel economy by cylinders"
