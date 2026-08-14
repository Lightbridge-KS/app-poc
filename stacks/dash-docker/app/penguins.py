"""Palmer Penguins data access and the verbs that reshape it.

Pure polars: this module knows nothing about Dash, callbacks, or plotting.
Every verb takes a frame and returns a new one — nothing mutates in place.

Ported from the Shiny sibling repo essentially unchanged, which was the point of
keeping it framework-agnostic there. The two differences: the dataset is read
from a vendored CSV rather than out of the ``palmerpenguins`` package (which
depends on pandas + numpy), and there is no ``to_pandas()`` — Plotly takes plain
Python lists, so pandas never enters this repo at all.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import polars as pl

#: Numeric columns an EDA view can meaningfully summarise.
MEASUREMENTS = ("bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g")

#: Resolved from this file, not the working directory: gunicorn runs with
#: ``--chdir /app/app`` while the dev server runs from ``/app``, and the data
#: must load identically either way.
DATA_CSV = Path(__file__).parent / "data" / "penguins.csv"


def load_penguins() -> pl.DataFrame:
    """Read the vendored 344-row Palmer Penguins dataset.

    The CSV sits next to this module, so loading never touches the network —
    which is what makes it safe inside a container.

    A stable ``row_id`` is attached here and never recomputed. Cross-filtering
    keys on it: a brush selection is a set of row ids, so it keeps pointing at
    the same penguins no matter how the sidebar filters change underneath it.
    """
    return (
        pl.read_csv(DATA_CSV, null_values=["NA", ""])
        .with_row_index("row_id")
        .with_columns(pl.col("row_id").cast(pl.Int64))
    )


#: Loaded once at import — the vendored CSV cannot change while the app runs.
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


def select_rows(df: pl.DataFrame, row_ids: Iterable[int] | None) -> pl.DataFrame:
    """Intersect a frame with a brush selection.

    Returns ``df`` untouched when nothing is selected, which is what makes an
    empty selection mean "show everything" rather than "show nothing". Ids that
    the sidebar has since filtered away simply fail to match, so a stale
    selection degrades to a smaller one instead of pointing at the wrong rows.
    """
    ids = list(row_ids or [])
    return df if not ids else df.filter(pl.col("row_id").is_in(ids))


def summarise_by_species(df: pl.DataFrame) -> pl.DataFrame:
    """Per-species counts and means, with display-ready column names.

    This is the summary *table* — presentation is its whole purpose, so the
    renaming lives here rather than leaking into the app's callbacks.
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


def fit_line(df: pl.DataFrame, x: str, y: str) -> tuple[float, float] | None:
    """Ordinary least squares for one pair of columns: ``(slope, intercept)``.

    Two lines of arithmetic instead of a dependency. ``plotly.express`` offers
    ``trendline="ols"``, but that route pulls in statsmodels, pandas and numpy —
    the exact weight this repo is built to avoid. Returns ``None`` when there is
    nothing to fit (fewer than two points, or no spread in ``x``).
    """
    pairs = df.select(x, y).drop_nulls()
    if pairs.height < 2:
        return None

    xs, ys = pairs[x].to_list(), pairs[y].to_list()
    x_bar, y_bar = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((v - x_bar) ** 2 for v in xs)
    if sxx == 0:
        return None

    slope = sum((a - x_bar) * (b - y_bar) for a, b in zip(xs, ys)) / sxx
    return slope, y_bar - slope * x_bar
