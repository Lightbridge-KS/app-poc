# Palmer Penguins EDA dashboard, in Docker Compose

A Shiny for Python EDA dashboard over the Palmer Penguins dataset — sidebar filters, three plots, two tables, three summary value boxes — running in a container under Docker Compose.

This repo started as a narrower question: *can Shiny for Python run under Docker Compose at all?* That answer was yes, and the dashboard replaced the starter app. The containerization lessons from that first pass are kept at the bottom, because they are the part worth stealing.

Verified 2026-08-14 on macOS / Apple Silicon, Docker 29.1.3, Compose v5.

---

## Quick start

```bash
just build     # build the image
just up        # start on :8000, block until healthy
just smoke     # GET / -> 200
just dev       # hot-reload service on :8001 (source bind-mounted)
just down      # stop everything
```

Without `just`: `docker compose up -d`, `docker compose --profile dev up -d dev`, `docker compose --profile dev down`.

---

## The dashboard

**Sidebar:** species checkboxes · island checkboxes · body-mass range slider (2700–6300 g) · drop-missing-values switch · linear-fit switch · histogram bin count.

**Body:** three value boxes (count / species / mean mass) → bill-dimension scatter and body-mass histogram side by side → flipper-length box plot → per-species summary table → sortable, filterable grid of the filtered rows.

Every output responds to every filter.

### Dataflow

```
                  penguins.py (polars)              plots.py (plotnine)
                  ───────────────────               ───────────────────
packaged CSV ──► PENGUINS ──► filter_penguins() ──► filtered()  [polars]
                                                        │
                                    ┌───────────────────┤
                                    │                   │
                          summarise_by_species()   to_pandas()   ◄── the ONE conversion
                                    │                   │
                                    ▼                   ▼
                            value boxes,          3 plotnine
                            2 tables              plot builders
```

### Module split

| File | Responsibility |
|---|---|
| `app/penguins.py` | Data + the `filter_` / `summarise_` verbs. Pure polars — no Shiny, no plotting. |
| `app/plots.py` | Three plot builders. Pure plotnine — takes pandas, returns a `ggplot`. |
| `app/app.py` | UI tree + server wiring. The only file that imports Shiny. |

`penguins.py` and `plots.py` can both be exercised from a plain script, which is how the plots below were rendered.

### Two deliberate choices

**polars everywhere, pandas only at the plot edge.** plotnine hard-depends on pandas and has no narwhals support, so a conversion is unavoidable. It lives in exactly one place — `penguins.to_pandas()`, called from one reactive calc — instead of being scattered through the renderers.

**That bridge goes via a dict, not `polars.DataFrame.to_pandas()`.** The polars↔pandas converters both require pyarrow (~100 MB), and pandas 3 returns Arrow-backed strings so even the *read* path needs it. For a 344-row table the dict hop is free. The packaged CSV is likewise read straight into polars rather than through `palmerpenguins.load_penguins()`.

---

## Evidence

### Container

```
$ docker image ls shiny-docker-poc:latest --format '{{.Size}}'
863MB
$ just up
app: healthy          # ~7s to healthy
$ just smoke
GET / -> 200
```

All nine reactive outputs are present in the container-served HTML (`empty_notice`, `n_penguins`, `n_species`, `mean_mass`, `bill_scatter`, `mass_hist`, `flipper_box`, `summary_table`, `rows_table`), and `docker compose logs app` contains no errors, tracebacks, or warnings.

### The full data→plot path, executed inside the container

```
$ docker compose exec app python -c "...import penguins, plots; render..."
backend      : Agg
MPLCONFIGDIR : /home/appuser/.cache/matplotlib | writable: True
running as   : uid 10001
dataset      : (344, 8) ['Adelie', 'Chinstrap', 'Gentoo']
filtered     : (104, 8)          # species=Gentoo, island=Biscoe, mass 4500-6300, drop NA
summary      : {'Species': 'Gentoo', 'n': 104, 'Bill length (mm)': 48.0,
                'Bill depth (mm)': 15.1, 'Flipper (mm)': 218.2,
                'Body mass (g)': 5206.0, 'Mass SD (g)': 426.0}
scatter  rendered -> 48782 bytes
hist     rendered -> 17277 bytes
box      rendered -> 29841 bytes
```

The three PNGs were pulled back out and inspected: the scatter shows the expected Simpson's paradox (bill length and depth correlate negatively pooled, positively within each species), the histogram shows Gentoo sitting clearly apart in body mass, and the box plot separates all three species on flipper length. Unprivileged uid, headless `Agg` backend, writable config dir — all confirmed at runtime, not assumed.

### Dataset facts (measured, not recalled)

344 rows · 333 complete cases · body mass 2700–6300 g · nulls: 2 rows missing all four measurements, 11 more missing `sex`.

### Dev hot reload

Edited the page title on the host — no rebuild, no restart:

```
:8001 (dev, bind-mounted, NO rebuild) ->  HOT RELOAD PROOF        ← picked up the edit
:8000 (app, baked into image)         ->  Palmer Penguins — EDA   ← correctly unaffected
```

### ⚠️ Not yet verified: live browser reactivity

The browser automation extension was disconnected during this pass, so the **in-browser** check — click a filter, watch all nine outputs update over the WebSocket — has **not** been run against the dashboard. What is proven is that the page serves with every output wired, and that the data and plot pipeline executes correctly inside the container.

The WebSocket transport itself was proven in this same container setup during the earlier pass (`"WebSocket /websocket/" [accepted]`, client `readyState: 1`, a slider round-trip returning a server-computed value). That evidence is about the container, and still holds; it is not evidence about this dashboard's reactive graph.

To close the gap: start the app and open `localhost:8000`, toggle a species, and confirm the value boxes, both tables and all three plots move together.

---

## Container lessons worth stealing

1. **`--host 0.0.0.0`.** Shiny's default bind is `127.0.0.1`, which inside a container means the container's own loopback — unreachable from the host no matter how you publish the port. The single most common "works locally, dead in Docker" cause.

2. **The WebSocket must survive the whole path.** Publishing a port directly (what this does) is fine. Put nginx/Caddy/an ingress/an ALB in front and you must forward `Upgrade`/`Connection` and raise the proxy read timeout, or the page loads and then sits there inert — HTTP 200, zero reactivity.

3. **matplotlib needs three things in a container.** `MPLBACKEND=Agg` (there is no display; let it guess and it can fail), `MPLCONFIGDIR` pointing somewhere the non-root user can write (else every render logs a cache warning), and a font cache warmed at build time (else the first plot stalls for seconds).

4. **Builder and runtime stages share the same base image.** A venv records an absolute interpreter path, so building on `ghcr.io/astral-sh/uv:python3.12-*` (uv-managed standalone Python) and copying into `python:3.12-slim` yields a venv that cannot start.

5. **Budget the health check for the import, not the app.** Importing polars + plotnine + matplotlib + statsmodels is far slower than importing bare shiny; `start_period` went from 10s to 30s.

### On the image size

863 MB, up from 204 MB for the starter app. polars, pandas, numpy, matplotlib, scipy and statsmodels are most of that — plotnine drags in scipy and statsmodels for `stat_smooth`. Dropping plotnine for `seaborn.objects` would cut it substantially at the cost of the ggplot grammar.

## Not covered

Reverse proxy / WebSocket proxying, CI, tests, multi-worker scaling (Shiny sessions are stateful in-process, so sticky sessions are required behind a load balancer). The dashboard is read-only — no upload, no export.
