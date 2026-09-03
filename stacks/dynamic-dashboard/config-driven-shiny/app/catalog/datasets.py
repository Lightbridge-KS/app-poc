"""The two datasets the catalog knows, and the fixed clean step for each.

Mirrors `genui-controlled-nextjs/src/catalog/datasets.ts` field for field. The column
tuples below become the `Literal` types in `schema.py`, so an unknown column is a
validation error, never a runtime guess. Pure polars; nothing here knows about Shiny.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import polars as pl

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class DatasetDef:
    file: str
    label: str
    numeric: tuple[str, ...]
    categorical: tuple[str, ...]
    row_label: str | None

    @property
    def columns(self) -> tuple[str, ...]:
        return self.numeric + self.categorical


DATASETS: dict[str, DatasetDef] = {
    "penguins": DatasetDef(
        file="penguins.csv",
        label="Palmer Penguins — 344 penguins, 3 species, 3 islands (2007–2009)",
        numeric=("bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g", "year"),
        categorical=("species", "island", "sex"),
        row_label=None,
    ),
    "mtcars": DatasetDef(
        file="mtcars.csv",
        label="Motor Trend cars (1974) — 32 cars, fuel economy and design",
        numeric=("mpg", "disp", "hp", "drat", "wt", "qsec"),
        categorical=("cyl", "vs", "am", "gear", "carb"),
        row_label="model",
    ),
}


@cache
def load_clean(dataset: str) -> pl.DataFrame:
    """CleanedData: numeric columns as Float64, categorical as String, NA → null."""
    d = DATASETS[dataset]
    raw_df = pl.read_csv(DATA_DIR / d.file, null_values=["NA", ""], infer_schema_length=0)
    keep = list(d.numeric) + list(d.categorical) + ([d.row_label] if d.row_label else [])
    return raw_df.select(
        *[pl.col(c).cast(pl.Float64, strict=False).alias(c) for c in d.numeric],
        *[pl.col(c).cast(pl.String).alias(c) for c in keep if c not in d.numeric],
    )
