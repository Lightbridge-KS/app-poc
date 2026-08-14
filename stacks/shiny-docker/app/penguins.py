"""Palmer Penguins data access and the verbs that reshape it.

Pure polars: this module knows nothing about Shiny, reactivity, or plotting.
Every verb takes a frame and returns a new one — nothing mutates in place.
"""

from __future__ import annotations

import importlib.resources as resources
from collections.abc import Sequence

import polars as pl

#: Numeric columns an EDA view can meaningfully summarise.
MEASUREMENTS = ("bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g")


def load_penguins() -> pl.DataFrame:
    """Read the 344-row Palmer Penguins dataset bundled with ``palmerpenguins``.

    Reads the packaged CSV straight into polars rather than going through
    ``palmerpenguins.load_penguins()``. That loader returns pandas, and pandas 3
    hands back Arrow-backed string columns — converting those into polars would
    require pyarrow, a ~100 MB dependency bought for a 344-row table.

    The CSV ships inside the installed package, so this never touches the
    network — which is what makes it safe inside a container.
    """
    csv = resources.files("palmerpenguins").joinpath("data/penguins.csv")
    with resources.as_file(csv) as path:
        return pl.read_csv(path, null_values=["NA", ""])


#: Loaded once at import — the packaged CSV cannot change while the app runs.
PENGUINS = load_penguins()

SPECIES: list[str] = PENGUINS["species"].unique().sort().to_list()
ISLANDS: list[str] = PENGUINS["island"].unique().sort().to_list()
MASS_RANGE: tuple[int, int] = (
    PENGUINS["body_mass_g"].min(),
    PENGUINS["body_mass_g"].max(),
)


def filter_penguins(
    df: pl.DataFrame,
    *,
    species: Sequence[str],
    islands: Sequence[str],
    mass_range: tuple[float, float],
    drop_incomplete: bool = False,
) -> pl.DataFrame:
    """Narrow the dataset to the sidebar's current selection.

    Note that the mass filter drops the two rows whose ``body_mass_g`` is null:
    a row with no recorded mass cannot be inside a mass range. ``drop_incomplete``
    therefore acts on what is left — chiefly the 11 rows with unrecorded ``sex``.
    """
    lo, hi = mass_range
    out = df.filter(
        pl.col("species").is_in(list(species)),
        pl.col("island").is_in(list(islands)),
        pl.col("body_mass_g").is_between(lo, hi),
    )
    return out.drop_nulls() if drop_incomplete else out


def summarise_by_species(df: pl.DataFrame) -> pl.DataFrame:
    """Per-species counts and means, with display-ready column names.

    This is the summary *table* — presentation is its whole purpose, so the
    renaming lives here rather than leaking into the app's render functions.
    """
    return (
        df.group_by("species")
        .agg(
            pl.len().alias("n"),
            pl.col("bill_length_mm").mean().round(1).alias("Bill length (mm)"),
            pl.col("bill_depth_mm").mean().round(1).alias("Bill depth (mm)"),
            pl.col("flipper_length_mm").mean().round(1).alias("Flipper (mm)"),
            pl.col("body_mass_g").mean().round(0).alias("Body mass (g)"),
            pl.col("body_mass_g").std().round(0).alias("Mass SD (g)"),
        )
        .sort("species")
        .rename({"species": "Species"})
    )


def to_pandas(df: pl.DataFrame):
    """Hand a polars frame to plotnine, which is pandas-only.

    Goes via a plain dict of columns rather than ``DataFrame.to_pandas()``,
    which would pull in pyarrow. At 344 rows the copy is free, and it keeps the
    polars→pandas seam in exactly one place.
    """
    import pandas as pd

    return pd.DataFrame(df.to_dict(as_series=False))
