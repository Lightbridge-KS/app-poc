# Palmer Penguins EDA dashboard, in Docker Compose — interactive

A Plotly Dash EDA dashboard over the Palmer Penguins dataset — sidebar filters, three interactive plots, two tables, three summary value boxes — running in a container under Docker Compose.

This repo started as a narrower question: *can a Plotly Dash app run under Docker Compose at all?* That answer was yes, and the dashboard replaced the starter app. The containerization lessons from that first pass are kept at the bottom, because they are the part worth stealing.

The plots are **genuinely interactive**: hover, zoom, legend toggle — and box-drag on the scatter **cross-filters** everything below it.

Verified 2026-08-14 on macOS / Apple Silicon, Docker 29.1.3, Compose v5, Dash 4.4.1.

---

## Quick start

```bash
just build     # build the image
just up        # start on :8050, block until healthy
just smoke     # / , /_dash-layout and the vendored CSS all 200
just prove     # drive the sidebar callback, read back what the container computed
just brush     # cross-filtering, proved over HTTP with no browser
just workers   # 20 concurrent brushed requests across 4 gunicorn workers
just preview   # render the 3 figures to a standalone HTML file you can open
just dev       # hot-reload service on :8051 (source bind-mounted)
just down      # stop everything
```

Without `just`: `docker compose up -d`, `docker compose --profile dev up -d dev`, `docker compose --profile dev down`.

---

## The dashboard

**Sidebar:** species checkboxes · island checkboxes · body-mass range slider (2700–6300 g) · drop-missing-values switch · linear-fit switch · histogram bin count · **clear selection**.

**Body:** three value boxes (count / species / mean mass) → bill-dimension scatter and body-mass histogram side by side → flipper-length box plot → per-species summary table → sortable, filterable, paged grid of the filtered rows.

Every output responds to every filter — and to the brush.

### Interactivity

| Gesture | Effect |
|---|---|
| Hover a scatter point | that penguin's island, bill dimensions, mass, sex |
| **Drag a box on the scatter** | **cross-filters** value boxes, histogram, box plot and both tables to the selected penguins |
| Click a legend entry | isolate / restore a species |
| Zoom, pan, mode bar, PNG download | standard Plotly, on every figure |
| Sort / filter / page the rows table | native `dash_table` |

### Dataflow

```
                  penguins.py (polars)                plots.py (plotly)
                  ───────────────────                 ─────────────────
vendored CSV ──► PENGUINS ──► filter_penguins() ──► filtered
                 (+ row_id)                            │
                                          ┌────────────┴──────────────┐
                                          ▼                           ▼
                             [A] bill_scatter figure          (brush: row ids)
                                 customdata = row_id                  │
                                                                      ▼
                                                    select_rows(filtered, ids)
                                                                      │
                                                                  selected
                                                                      │
                              ┌────────────┬──────────────┬───────────┴────┬──────────┐
                              ▼            ▼              ▼                ▼          ▼
                        value boxes   mass_histogram  flipper_box   summarise_   rows table
                                                                    by_species
```

### Module split

| File | Responsibility |
|---|---|
| `app/penguins.py` | Data + the `filter_` / `select_` / `summarise_` verbs. Pure polars — no Dash, no plotting. |
| `app/plots.py` | Three figure builders. Pure `plotly.graph_objects` — takes a polars frame, returns a `go.Figure`. |
| `app/app.py` | Layout + callbacks. The only file that imports Dash. |
| `app/data/penguins.csv` | The 344-row dataset, vendored. |
| `app/assets/bootstrap.min.css` | Bootstrap 5.3.8, vendored. Dash serves `assets/` itself. |

`penguins.py` and `plots.py` can both be exercised from a plain script, which is how the evidence below was produced.

### Three deliberate choices

**Cross-filtering keys on row ids, not point positions.** Each scatter point carries its dataset `row_id` as `customdata[0]`. Mapping a selection by `curveNumber`/`pointNumber` — or by position in the filtered frame — silently points at the *wrong penguins* the moment a filter changes underneath a live brush. With ids, a selection is a set that gets intersected with whatever is currently filtered, so a stale selection shrinks instead of lying. Proved below.

**Two callbacks, and the scatter is not one of the things the brush filters.** The scatter keeps showing the whole filtered set with unselected points dimmed to 12% opacity; everything else narrows. Filtering the scatter by its own selection would erase the context you selected against, with no way back.

**No pandas, no numpy, anywhere.** Plotly serialises plain Python lists, so columns go out as `.to_list()` and the polars→pandas bridge the Shiny sibling needs simply does not exist here. The linear fit is four lines of arithmetic in `penguins.fit_line()` rather than `plotly.express`'s `trendline="ols"`, which would pull in statsmodels + pandas + numpy. Result: **500 MB vs the sibling's 863 MB**, and one fewer conversion seam.

---

## Evidence

### Dataset facts (measured in the container, not recalled)

```
rows           : 344
complete cases : 333
mass range     : (2700, 6300)
species        : ['Adelie', 'Chinstrap', 'Gentoo']
islands        : ['Biscoe', 'Dream', 'Torgersen']
filtered(all)  : 342          # the 2 null-mass rows cannot be inside a mass range
```

Identical to the sibling repo's measured numbers — same dataset, different loader, so any drift would mean the vendored CSV is wrong.

### The container computing the dashboard

```
$ just prove
{ "penguins": "342", "species": "3", "mean_mass": "4,202 g",
  "summary": [ {"Species":"Adelie","n":151},
               {"Species":"Chinstrap","n":68},
               {"Species":"Gentoo","n":123} ],
  "rows_in_table": 342 }
```

Driven by POSTing `/_dash-update-component`. The payload is not hand-written — it is built from what the app publishes at `/_dash-dependencies` (`just deps`).

### Cross-filtering, proved without a browser

Brushing 15 known `row_id`s — 10 Adelie + 5 Gentoo — out of the 342:

```
$ just brush
{ "penguins": "15", "species": "2",
  "badge": "Brush active — 15 of 342 penguins selected",
  "summary":     [ {"Species":"Adelie","n":10}, {"Species":"Gentoo","n":5} ],
  "rows_in_table": 15,
  "hist_traces": [ {"name":"Adelie","n":10}, {"name":"Gentoo","n":5} ],
  "box_traces":  [ {"name":"Adelie","n":10}, {"name":"Gentoo","n":5} ] }
```

Chinstrap disappears entirely, and both remaining plots narrow to exactly the brushed points. This is the thing a static plotnine dashboard cannot do.

**Stale-brush degradation** — the same 15 Adelie/Gentoo ids, with the sidebar switched to Chinstrap only:

```
{ "penguins": "0", "species": "0", "summary": [], "rows": 0 }
```

Zero, not fifteen of the wrong penguins. That is the row-id design doing its job. (In the UI this is unreachable anyway — callback A clears the brush whenever a filter changes.)

### Figures

```
scatter traces        : 3 ['Adelie', 'Chinstrap', 'Gentoo']
points per trace      : {'Adelie': 151, 'Chinstrap': 68, 'Gentoo': 123}
polars group counts   : {'Adelie': 151, 'Chinstrap': 68, 'Gentoo': 123}   ← match
customdata[0], pt 0   : [0, 'Torgersen', 'male', 3750]   (row_id, island, sex, mass)
dragmode              : select        unselected opacity : 0.12
with smoother         : 6 traces (+3 fit lines)
histogram             : 3 traces, barmode=overlay, nbinsx=25
box plot              : 3 traces, boxpoints=all, jitter=0.4
empty frame           : 0 traces, no exception
```

**Simpson's paradox, measured rather than asserted** — `penguins.fit_line()` on bill length vs depth:

```
Adelie only : slope +0.1788
pooled      : slope -0.0850     ← sign flips
```

Positive within a species, negative across all three. Toggle the smoother to see it.

### Stateless across 4 gunicorn workers

```
$ just workers
workers that served the 20 concurrent brushed requests:
   9 pid 7
   3 pid 8
   2 pid 9
   6 pid 16
distinct answers (must be exactly one — the brush selects 15 of 342):
  20 15 penguins / 2 species
```

All four workers, one identical answer. The brush makes the point sharper than the old starter app could: the *selection* also rides in the request body, so no worker has to remember anything about the client. `--workers N` scales this with no sticky sessions.

### Assets served locally, no CDN

```
GET /                         -> 200
GET /_dash-layout             -> 200
GET /assets/bootstrap.min.css -> 200 (232111 bytes, no CDN)
```

The page styles fully on an air-gapped machine. All 18 component ids (`species` … `worker_note`) are present in the container-served layout.

### Dev hot reload

Edited the page title on the host — no rebuild, no restart:

```
dev picked up the edit after ~4s
:8051 (dev, bind-mounted, NO rebuild) -> HOT RELOAD PROOF
:8050 (app, baked into image)         -> Palmer Penguins — EDA   ← correctly unaffected
```

### ⚠️ Not verified: the dashboard driven in a real browser

The browser automation extension was disconnected for this pass, so **nobody has clicked this UI**. What is proven is that every callback returns correct data over HTTP — including the full cross-filter path — that all 18 components are wired into the served layout, and that the figures carry the right traces, `customdata`, and drag mode.

What that does *not* cover: how it actually looks and feels — Bootstrap layout at real viewport widths, whether the box-drag gesture feels right, mode-bar placement, console errors.

`just preview` renders the three figures to a standalone HTML file you can open directly; that exercises the Plotly interactivity (hover, brush, legend, zoom) outside Dash. To close the gap properly: `just up`, open `localhost:8050`, drag a box over the Gentoo cluster, and confirm the value boxes, both tables and the other two plots follow.

---

## Container lessons worth stealing

1. **`--bind 0.0.0.0`.** Dash defaults to `127.0.0.1`, which inside a container means the container's own loopback — unreachable from the host no matter how you publish the port. The single most common "works locally, dead in Docker" cause.

2. **`app.run` is not a production server** — Dash's own docs say so. Production is `gunicorn app:server`, which needs the module-level `server = app.server` to exist at all. The dev and prod services therefore run **different commands**: gunicorn has no reloader, so you cannot have both from one.

3. **`plotly.express` silently needs `numpy` *and* `pandas`.** Neither is a dependency of `plotly`, so `import plotly.express` in a lean image builds green and then **crashes every gunicorn worker on boot** — `HaltServer: Worker failed to boot`, real cause buried above the visible traceback. Hit during the first pass. `plotly.graph_objects` has no such requirement, which is why this dashboard is built on it.

4. **`--chdir /app/app`** in the `CMD`: `app/` has no `__init__.py`, so `app.app:server` is ambiguous. Chdir in and import plainly as `app:server`. (This is also why `docker compose exec` snippets here pass `-w /app/app`.)

5. **Health-check the framework, not the port.** `/` is served by Flask and returns 200 even if Dash failed to initialize; `/_dash-layout` only answers if Dash is really up.

6. **Budget the health check for the import, not the app.** Importing polars and building the initial figures is far slower than importing bare Dash — `start_period` went from 10s to 30s.

7. **Builder and runtime stages share the same base image.** A venv records an absolute interpreter path, so building on a different Python and copying the venv into `python:3.12-slim` yields a venv that cannot start.

8. **Vendor small assets instead of depending on them.** `palmerpenguins` depends on pandas + numpy to ship a 15 KB CSV; the CSV is now committed. Bootstrap comes from `assets/` rather than a CDN so the page is not internet-dependent at render time.

### On recomputing instead of caching

Callback B re-runs `filter_penguins()` rather than receiving a frame from callback A. Dash has no `reactive.calc`, and at 344 rows recomputing is free, while a `dcc.Store` would mean serialising the frame to the browser and back on every interaction. **That trade flips on a large dataset** — at which point the answer is a server-side cache keyed on the filter inputs, not a bigger `Store`.

## Not covered

Reverse proxy / TLS, CI, tests, authentication, and **background (long) callbacks** — those reintroduce shared state via a Celery/Redis or DiskCache manager, and would break the "just add workers" story proved above.

## Data

Palmer Penguins — Horst AM, Hill AP, Gorman KB (2020), `palmerpenguins` R package. Data collected by Dr. Kristen Gorman at Palmer Station, Antarctica LTER. Released under CC0, which is what makes vendoring the CSV here fine.
