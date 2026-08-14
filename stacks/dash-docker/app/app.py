"""Palmer Penguins EDA dashboard — sidebar filters plus brushable cross-filtering.

The only module that imports Dash. It wires the sidebar inputs to the data verbs
in ``penguins.py`` and the figure builders in ``plots.py``, and lays the results
out; no reshaping or plotting logic lives here.

Two callbacks rather than one, because they answer to different things:

    sidebar ─────────────► [A] bill scatter figure  (+ resets the brush)
                                     │
                            selectedData (row ids)
                                     ▼
    sidebar ────────────► [B] value boxes · histogram · box plot · both tables

The scatter deliberately keeps showing the *whole* filtered set while everything
else narrows to the brush — otherwise selecting would erase the context you
selected against, and there would be no way back.
"""

from __future__ import annotations

import os

import dash_bootstrap_components as dbc
import polars as pl
from dash import Dash, Input, Output, callback, dash_table, dcc, html

import penguins as pg
import plots

# Bootstrap is vendored in assets/, which Dash serves itself — no external
# stylesheet, so the page renders fully styled on an offline machine.
app = Dash(__name__, title="Palmer Penguins — EDA")

#: The Flask (WSGI) object gunicorn binds to. See the Dockerfile CMD.
server = app.server


# ── Layout ────────────────────────────────────────────────────────────────────


def _value_box(label: str, box_id: str) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(label, className="text-muted small text-uppercase"),
                html.Div(id=box_id, className="fs-3 fw-semibold"),
            ]
        ),
        className="h-100",
    )


def _plot_card(title: str, graph: dcc.Graph) -> dbc.Card:
    return dbc.Card([dbc.CardHeader(title), dbc.CardBody(graph)], className="h-100")


_GRAPH_CONFIG = {"displaylogo": False, "displayModeBar": True}

sidebar = dbc.Card(
    dbc.CardBody(
        [
            html.H5("Filters", className="card-title"),
            html.Label("Species", className="fw-semibold mt-3"),
            dcc.Checklist(
                pg.SPECIES,
                pg.SPECIES,
                id="species",
                inputClassName="form-check-input me-2",
                labelClassName="form-check-label d-block",
            ),
            html.Label("Island", className="fw-semibold mt-3"),
            dcc.Checklist(
                pg.ISLANDS,
                pg.ISLANDS,
                id="islands",
                inputClassName="form-check-input me-2",
                labelClassName="form-check-label d-block",
            ),
            html.Label("Body mass (g)", className="fw-semibold mt-3"),
            dcc.RangeSlider(
                min=pg.MASS_RANGE[0],
                max=pg.MASS_RANGE[1],
                step=50,
                value=list(pg.MASS_RANGE),
                id="mass",
                tooltip={"placement": "bottom", "always_visible": True},
            ),
            html.Hr(),
            dbc.Switch(id="drop_incomplete", label="Drop rows with missing values", value=False),
            dbc.Switch(id="smoother", label="Add linear fit to scatter", value=False),
            html.Label("Histogram bins", className="fw-semibold mt-3"),
            dcc.Slider(min=5, max=60, step=1, value=25, id="bins"),
            html.Hr(),
            dbc.Button(
                "Clear selection",
                id="clear",
                color="secondary",
                outline=True,
                size="sm",
                className="w-100",
            ),
            html.Div(
                "Drag a box on the scatter to cross-filter everything below it.",
                className="text-muted small mt-2",
            ),
        ]
    ),
)

main = [
    html.Div(id="empty_notice"),
    html.Div(id="selection_note", className="mb-2"),
    dbc.Row(
        [
            dbc.Col(_value_box("Penguins", "n_penguins"), md=4),
            dbc.Col(_value_box("Species", "n_species"), md=4),
            dbc.Col(_value_box("Mean body mass", "mean_mass"), md=4),
        ],
        className="g-3",
    ),
    dbc.Row(
        [
            dbc.Col(
                _plot_card(
                    "Bill dimensions — drag to select",
                    dcc.Graph(id="bill_scatter", config=_GRAPH_CONFIG),
                ),
                lg=6,
            ),
            dbc.Col(
                _plot_card("Body mass", dcc.Graph(id="mass_hist", config=_GRAPH_CONFIG)),
                lg=6,
            ),
        ],
        className="g-3 mt-1",
    ),
    dbc.Row(
        dbc.Col(
            _plot_card("Flipper length", dcc.Graph(id="flipper_box", config=_GRAPH_CONFIG))
        ),
        className="g-3 mt-1",
    ),
    dbc.Card(
        [
            dbc.CardHeader("Summary by species"),
            dbc.CardBody(
                dash_table.DataTable(
                    id="summary_table",
                    style_table={"overflowX": "auto"},
                    style_cell={"fontFamily": "system-ui", "padding": "8px"},
                    style_header={"fontWeight": "600"},
                )
            ),
        ],
        className="mt-3",
    ),
    dbc.Card(
        [
            dbc.CardHeader("Filtered observations"),
            dbc.CardBody(
                dash_table.DataTable(
                    id="rows_table",
                    sort_action="native",
                    filter_action="native",
                    page_action="native",
                    page_size=10,
                    style_table={"overflowX": "auto"},
                    style_cell={"fontFamily": "system-ui", "padding": "6px"},
                    style_header={"fontWeight": "600"},
                )
            ),
        ],
        className="mt-3 mb-4",
    ),
    # Which gunicorn worker computed this response. Unobtrusive in the UI, but
    # it is what makes `just workers` able to prove requests spread across all
    # four workers with no sticky sessions.
    html.Div(id="worker_note", className="text-muted small mb-4"),
]

app.layout = dbc.Container(
    [
        html.H2("Palmer Penguins — EDA", className="mt-3 mb-3"),
        dbc.Row(
            [dbc.Col(sidebar, lg=3, className="mb-3"), dbc.Col(main, lg=9)],
            className="g-3",
        ),
    ],
    fluid=True,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _selected_ids(selected_data) -> list[int] | None:
    """Pull row ids out of a Plotly selection event.

    ``customdata[0]`` is the row id — see ``plots.bill_scatter``. Reading ids
    rather than ``pointNumber`` is what keeps a selection meaningful after the
    sidebar changes the frame underneath it.
    """
    points = (selected_data or {}).get("points") or []
    return [p["customdata"][0] for p in points if p.get("customdata")] or None


def _table(df: pl.DataFrame, *, drop: tuple[str, ...] = ()) -> tuple[list, list]:
    """Adapt a polars frame to DataTable's ``(data, columns)`` pair."""
    shown = df.drop(*drop) if drop else df
    return shown.to_dicts(), [{"name": c, "id": c} for c in shown.columns]


# ── Callbacks ─────────────────────────────────────────────────────────────────

_FILTER_INPUTS = (
    Input("species", "value"),
    Input("islands", "value"),
    Input("mass", "value"),
    Input("drop_incomplete", "value"),
)


@callback(
    Output("bill_scatter", "figure"),
    Output("bill_scatter", "selectedData"),
    *_FILTER_INPUTS,
    Input("smoother", "value"),
    Input("clear", "n_clicks"),
)
def update_scatter(species, islands, mass, drop_incomplete, smoother, _clear):
    """[A] Rebuild the brushable scatter, and drop any brush that was on it.

    Clearing the selection here is a UX call, not a correctness one: a stale
    selection would still resolve to the right penguins (ids, not positions),
    it would just be confusing to leave a box drawn over a changed plot.
    """
    filtered = pg.filter_penguins(
        pg.PENGUINS,
        species=species,
        islands=islands,
        mass_range=mass,
        drop_incomplete=drop_incomplete,
    )
    return plots.bill_scatter(filtered, smoother=smoother), None


@callback(
    Output("n_penguins", "children"),
    Output("n_species", "children"),
    Output("mean_mass", "children"),
    Output("selection_note", "children"),
    Output("mass_hist", "figure"),
    Output("flipper_box", "figure"),
    Output("summary_table", "data"),
    Output("summary_table", "columns"),
    Output("rows_table", "data"),
    Output("rows_table", "columns"),
    Output("empty_notice", "children"),
    Output("worker_note", "children"),
    *_FILTER_INPUTS,
    Input("bins", "value"),
    Input("bill_scatter", "selectedData"),
)
def update_views(species, islands, mass, drop_incomplete, bins, selected_data):
    """[B] Everything downstream of the brush.

    Re-runs ``filter_penguins`` instead of receiving a frame from callback A.
    Dash has no ``reactive.calc``, and at 344 rows recomputing costs nothing
    while a ``dcc.Store`` would mean serialising the frame to the browser and
    back on every interaction. That trade flips on a large dataset.
    """
    filtered = pg.filter_penguins(
        pg.PENGUINS,
        species=species,
        islands=islands,
        mass_range=mass,
        drop_incomplete=drop_incomplete,
    )
    ids = _selected_ids(selected_data)
    selected = pg.select_rows(filtered, ids)

    notice = (
        dbc.Alert(
            [
                html.Strong("No penguins match these filters."),
                " Widen the mass range or select more species/islands.",
            ],
            color="warning",
        )
        if filtered.is_empty()
        else None
    )

    note = (
        dbc.Badge(
            f"Brush active — {selected.height} of {filtered.height} penguins selected",
            color="info",
            className="p-2",
        )
        if ids
        else None
    )

    mean = selected["body_mass_g"].mean()
    summary_data, summary_cols = _table(pg.summarise_by_species(selected))
    rows_data, rows_cols = _table(selected, drop=("row_id",))

    return (
        f"{selected.height:,}",
        str(selected["species"].n_unique()),
        "—" if mean is None else f"{mean:,.0f} g",
        note,
        plots.mass_histogram(selected, bins=bins),
        plots.flipper_box(selected),
        summary_data,
        summary_cols,
        rows_data,
        rows_cols,
        notice,
        f"served by worker pid {os.getpid()}",
    )


if __name__ == "__main__":
    # Dev path only — gunicorn imports `server` above and never runs this block.
    # host=0.0.0.0 because Dash defaults to 127.0.0.1, which inside a container
    # means the container's own loopback and is unreachable from the host.
    app.run(host="0.0.0.0", port=8050, debug=True)
