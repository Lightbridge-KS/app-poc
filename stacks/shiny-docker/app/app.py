"""Palmer Penguins EDA dashboard.

This file is the only one that knows Shiny exists: it wires the sidebar inputs to
the data verbs in `penguins.py` and the plot builders in `plots.py`, and lays the
results out. All reshaping happens in polars; the single hop to pandas lives in
`filtered_pd()`, because plotnine cannot read a polars frame.
"""

from __future__ import annotations

import penguins as pg
import plots
from shiny import App, reactive, render, req, ui

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_checkbox_group("species", "Species", pg.SPECIES, selected=pg.SPECIES),
        ui.input_checkbox_group("islands", "Island", pg.ISLANDS, selected=pg.ISLANDS),
        ui.input_slider(
            "mass",
            "Body mass (g)",
            min=pg.MASS_RANGE[0],
            max=pg.MASS_RANGE[1],
            value=pg.MASS_RANGE,
            step=50,
        ),
        ui.hr(),
        ui.input_switch("drop_incomplete", "Drop rows with missing values", False),
        ui.input_switch("smoother", "Add linear fit to scatter", False),
        ui.input_slider("bins", "Histogram bins", min=5, max=60, value=25),
        title="Filters",
        width=280,
    ),
    ui.output_ui("empty_notice"),
    ui.layout_columns(
        ui.value_box("Penguins", ui.output_text("n_penguins")),
        ui.value_box("Species", ui.output_text("n_species")),
        ui.value_box("Mean body mass", ui.output_text("mean_mass")),
        col_widths=(4, 4, 4),
    ),
    ui.layout_columns(
        ui.card(ui.card_header("Bill dimensions"), ui.output_plot("bill_scatter")),
        ui.card(ui.card_header("Body mass"), ui.output_plot("mass_hist")),
        col_widths=(6, 6),
    ),
    ui.card(ui.card_header("Flipper length"), ui.output_plot("flipper_box")),
    ui.card(
        ui.card_header("Summary by species"),
        ui.output_data_frame("summary_table"),
    ),
    ui.card(
        ui.card_header("Filtered observations"),
        ui.output_data_frame("rows_table"),
    ),
    title="Palmer Penguins — EDA",
)


def server(input, output, session):
    @reactive.calc
    def filtered():
        """The sidebar selection, in polars. Feeds the value boxes and both tables."""
        return pg.filter_penguins(
            pg.PENGUINS,
            species=input.species(),
            islands=input.islands(),
            mass_range=input.mass(),
            drop_incomplete=input.drop_incomplete(),
        )

    @reactive.calc
    def filtered_pd():
        """The one polars→pandas conversion in the app. Feeds all three plots."""
        return pg.to_pandas(filtered())

    # ── Empty state ───────────────────────────────────────────────────────────
    # Deselecting every species yields an empty frame, which plotnine raises on.
    # One banner explains it; each output below then blanks via req() instead of
    # rendering a traceback into the card.

    @render.ui
    def empty_notice():
        if filtered().is_empty():
            return ui.div(
                ui.strong("No penguins match these filters."),
                " Widen the mass range or select more species/islands.",
                class_="alert alert-warning",
            )
        return None

    # ── Value boxes ───────────────────────────────────────────────────────────

    @render.text
    def n_penguins():
        return f"{filtered().height:,}"

    @render.text
    def n_species():
        return str(filtered()["species"].n_unique())

    @render.text
    def mean_mass():
        mean = filtered()["body_mass_g"].mean()
        return "—" if mean is None else f"{mean:,.0f} g"

    # ── Plots ─────────────────────────────────────────────────────────────────

    @render.plot
    def bill_scatter():
        req(not filtered().is_empty())
        return plots.plot_bill_scatter(filtered_pd(), smoother=input.smoother())

    @render.plot
    def mass_hist():
        req(not filtered().is_empty())
        return plots.plot_mass_distribution(filtered_pd(), bins=input.bins())

    @render.plot
    def flipper_box():
        req(not filtered().is_empty())
        return plots.plot_flipper_box(filtered_pd())

    # ── Tables ────────────────────────────────────────────────────────────────

    @render.data_frame
    def summary_table():
        req(not filtered().is_empty())
        return render.DataGrid(pg.summarise_by_species(filtered()), width="100%")

    @render.data_frame
    def rows_table():
        req(not filtered().is_empty())
        return render.DataGrid(
            filtered(), width="100%", height="360px", filters=True
        )


app = App(app_ui, server)
