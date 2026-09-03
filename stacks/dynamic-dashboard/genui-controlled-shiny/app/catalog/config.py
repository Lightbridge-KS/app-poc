"""cards.yaml → a dashboard whose cards each validated on their own.

One bad card must not blank the dashboard: it becomes an `ErrorCard` in its slot with a
message that names the field and lists the legal values, and every other card renders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from .schema import CardAdapter, DashboardHeader


@dataclass(frozen=True)
class ErrorCard:
    index: int
    raw: dict[str, Any]
    messages: list[str]


@dataclass(frozen=True)
class Dashboard:
    title: str
    columns: int
    cards: list[BaseModel | ErrorCard]
    header_errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> list[BaseModel]:
        return [c for c in self.cards if not isinstance(c, ErrorCard)]

    @property
    def errors(self) -> list[ErrorCard]:
        return [c for c in self.cards if isinstance(c, ErrorCard)]


def format_errors(err: ValidationError) -> list[str]:
    """`x: Input should be 'mpg', 'disp', … (got 'weight')` — the field, the rule, the legal values."""
    out = []
    for e in err.errors(include_url=False):
        # Drop the union tag pydantic prepends ("bar:penguins.by" → "by"); the field is the teaching part.
        parts = [str(p) for p in e["loc"] if not (isinstance(p, str) and ":" in p)]
        loc = ".".join(parts) or "card"
        got = e.get("input")
        got_r = repr(got)
        got_s = f" (got {got_r if len(got_r) <= 60 else got_r[:57] + '…'})" if not isinstance(got, dict) else ""
        out.append(f"{loc}: {e['msg']}{got_s}")
    return out


def parse_dashboard(text: str) -> Dashboard:
    try:
        raw = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        return Dashboard(title="Dashboard", columns=2, cards=[], header_errors=[f"YAML: {e}"])
    if not isinstance(raw, dict):
        return Dashboard(title="Dashboard", columns=2, cards=[], header_errors=["top level must be a mapping"])
    try:
        header = DashboardHeader.model_validate(raw)
    except ValidationError as e:
        return Dashboard(title=str(raw.get("title", "Dashboard")), columns=2, cards=[], header_errors=format_errors(e))
    cards: list[BaseModel | ErrorCard] = []
    for i, raw_card in enumerate(header.cards):
        try:
            cards.append(CardAdapter.validate_python(raw_card))
        except ValidationError as e:
            cards.append(ErrorCard(index=i, raw=raw_card, messages=format_errors(e)))
    return Dashboard(title=header.title, columns=header.columns, cards=cards)


def load_dashboard(path: Path) -> Dashboard:
    return parse_dashboard(path.read_text(encoding="utf-8"))
