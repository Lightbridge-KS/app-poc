"""Errors teach: a bad card names the field and the legal values, and never blanks the others."""

from pathlib import Path

from app.catalog.config import ErrorCard, load_dashboard

BAD = Path(__file__).parent.parent / "fixtures" / "bad-cards.yaml"


def test_bad_cards_are_isolated() -> None:
    dash = load_dashboard(BAD)
    assert len(dash.cards) == 5
    assert [isinstance(c, ErrorCard) for c in dash.cards] == [True, True, True, True, False]
    assert dash.ok[0].kind == "scatter"  # type: ignore[attr-defined]


def test_unknown_column_lists_legal_values() -> None:
    err = load_dashboard(BAD).errors[0]
    msg = " ".join(err.messages)
    assert msg.startswith("x:")
    assert "'weight'" in msg
    for col in ("mpg", "disp", "hp", "drat", "wt", "qsec"):
        assert f"'{col}'" in msg


def test_unknown_kind_lists_supported_tags() -> None:
    msg = " ".join(load_dashboard(BAD).errors[1].messages)
    assert "pie" in msg
    assert "scatter:penguins" in msg and "bar:mtcars" in msg


def test_numeric_column_rejected_for_by() -> None:
    msg = " ".join(load_dashboard(BAD).errors[2].messages)
    assert msg.startswith("by:")
    assert "'species'" in msg and "'island'" in msg and "'sex'" in msg


def test_too_many_filters() -> None:
    msg = " ".join(load_dashboard(BAD).errors[3].messages)
    assert msg.startswith("filter:")
    assert "3" in msg
