"""The PlotSpec, in Pydantic — the same contract the nextjs stack states in Zod.

Every field is a decision the config author may make; every absent field is one they
may not. The PlotSpec models carry no free text. The *Card* models wrap a PlotSpec with
`kind` (the tool name, explicit because there is no tool call) and an optional human
`title` — copy a person writes is allowed, copy a model writes was not.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag, TypeAdapter, create_model

from .datasets import DATASETS

FILTER_OPS = ("==", "!=", ">", ">=", "<", "<=", "in")
FilterOp = Literal[FILTER_OPS]  # type: ignore[valid-type]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CountMeasure(_Strict):
    op: Literal["count"]


def _spec_models(dataset: str) -> tuple[type[BaseModel], type[BaseModel]]:
    """Build the scatter and bar PlotSpec models for one dataset from its column catalog."""
    d = DATASETS[dataset]
    numeric = Literal[d.numeric]  # type: ignore[valid-type]
    categorical = Literal[d.categorical]  # type: ignore[valid-type]
    any_col = Literal[d.columns]  # type: ignore[valid-type]

    filter_model = create_model(
        f"{dataset.title()}Filter",
        __base__=_Strict,
        column=(any_col, ...),
        op=(FilterOp, Field(description="'in' takes a list value; the rest take a scalar")),
        value=(int | float | str | list[str], Field(..., description="scalar, or a list of 1–10 strings for 'in'")),
    )
    agg_model = create_model(
        f"{dataset.title()}AggMeasure",
        __base__=_Strict,
        op=(Literal["mean", "median"], ...),
        column=(numeric, ...),
    )
    measure = Annotated[CountMeasure | agg_model, Field(discriminator="op")]
    filters = (list[filter_model] | None, Field(None, max_length=3))  # type: ignore[valid-type]

    scatter = create_model(
        f"{dataset.title()}Scatter",
        __base__=_Strict,
        dataset=(Literal[dataset], Field(..., description=d.label)),
        x=(numeric, ...),
        y=(numeric, ...),
        color=(categorical | None, Field(None, description="Colour points by this category")),
        filter=filters,
    )
    bar = create_model(
        f"{dataset.title()}Bar",
        __base__=_Strict,
        dataset=(Literal[dataset], Field(..., description=d.label)),
        by=(categorical, Field(..., description="One bar per level of this column")),
        measure=(measure, Field(..., description="Bar height: row count, or mean/median of a numeric column")),
        color=(categorical | None, Field(None, description="Split each bar by this category (grouped bars)")),
        filter=filters,
    )
    return scatter, bar


PenguinsScatter, PenguinsBar = _spec_models("penguins")
MtcarsScatter, MtcarsBar = _spec_models("mtcars")

ScatterSpec = Annotated[PenguinsScatter | MtcarsScatter, Field(discriminator="dataset")]
BarSpec = Annotated[PenguinsBar | MtcarsBar, Field(discriminator="dataset")]

ScatterSpecAdapter: TypeAdapter[Any] = TypeAdapter(ScatterSpec)
BarSpecAdapter: TypeAdapter[Any] = TypeAdapter(BarSpec)

# ── Cards: PlotSpec + kind + optional human title, flat in the YAML ──────────────────


def _card_model(kind: str, spec_model: type[BaseModel]) -> type[BaseModel]:
    return create_model(
        f"{spec_model.__name__}Card",
        __base__=spec_model,
        kind=(Literal[kind], ...),
        title=(str | None, Field(None, max_length=60, description="Optional human-written card title")),
    )


PenguinsScatterCard = _card_model("scatter", PenguinsScatter)
MtcarsScatterCard = _card_model("scatter", MtcarsScatter)
PenguinsBarCard = _card_model("bar", PenguinsBar)
MtcarsBarCard = _card_model("bar", MtcarsBar)


def _card_tag(v: Any) -> str | None:
    if isinstance(v, dict):
        return f"{v.get('kind')}:{v.get('dataset')}"
    return f"{getattr(v, 'kind', None)}:{getattr(v, 'dataset', None)}"


Card = Annotated[
    Annotated[PenguinsScatterCard, Tag("scatter:penguins")]
    | Annotated[MtcarsScatterCard, Tag("scatter:mtcars")]
    | Annotated[PenguinsBarCard, Tag("bar:penguins")]
    | Annotated[MtcarsBarCard, Tag("bar:mtcars")],
    Discriminator(_card_tag),
]
CardAdapter: TypeAdapter[Any] = TypeAdapter(Card)


def spec_of(card: BaseModel) -> dict[str, Any]:
    """The PlotSpec inside a card: what the LLM would have emitted, nothing more."""
    return card.model_dump(exclude={"kind", "title"}, exclude_none=True)


class DashboardHeader(_Strict):
    """The dashboard-level knobs. `cards` stays raw here so each card validates on its own."""

    title: str = Field("Dashboard", max_length=80)
    columns: Literal[1, 2] = 2
    cards: list[dict[str, Any]] = Field(default_factory=list)
