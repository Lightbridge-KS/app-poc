# app-poc

Runnable proof-of-concept **application stacks**. Each one answers a single
deployment question — *can this run the way I'd actually ship it, and what does
it cost?* — and answers it with measured evidence rather than recollection.

The point is not the app. The point is the evidence, the gotchas that only show
up once something is containerized or wired end to end, and the honest list of
what still isn't verified.

## Stacks

| Stack | Question it answers | Verdict | Verified |
|---|---|---|---|
| [`stacks/shiny-docker`](stacks/shiny-docker) | Shiny for Python under Docker Compose — a stateful WebSocket app | ✅ works · 863 MB · in-process sessions, so sticky sessions are required behind a LB | 2026-08-14 |
| [`stacks/dash-docker`](stacks/dash-docker) | The same dashboard on Plotly Dash — does it scale statelessly? | ✅ works · 500 MB · 4 gunicorn workers, one identical answer, no stickiness | 2026-08-14 |
| [`stacks/pydantic-openapi-react`](stacks/pydantic-openapi-react) | Can Pydantic models *be* the API contract, with TypeScript generated downstream? | ✅ schema drift becomes a compile error · 2 gotchas found in the source doc | 2026-08-14 † |
| [`stacks/dynamic-dashboard/genui-controlled-nextjs`](stacks/dynamic-dashboard/genui-controlled-nextjs) | Can an LLM drive a *Controlled-tier* generative UI — pick a prebuilt plot, fill typed props — consistently enough to trust? | ✅ works · tool choice 20/20 · props 20/20 identical once the one free-text prop was removed · 3/3 out-of-catalog prompts refused | 2026-09-03 |
| [`stacks/dynamic-dashboard/config-driven-shiny`](stacks/dynamic-dashboard/config-driven-shiny) | The same PlotSpec filled by a YAML file instead of a model — same result, in a second language? | ✅ works · 4/4 outputs equal the nextjs stack's · Pydantic ≡ Zod vocabulary · bad cards fail in place, live reload in 3 s | 2026-09-03 |
| [`stacks/dynamic-dashboard/genui-controlled-shiny`](stacks/dynamic-dashboard/genui-controlled-shiny) | The same LLM-filled contract in Python + chatlas, seeded from the YAML — same consistency, same specs? | ✅ works · tool choice 20/20 · specs 4/4 equal to the nextjs run · refusals 3/3 · needed `strict=False` where the AI SDK needed nothing | 2026-09-03 |

† Inferred from the working session — this stack's README carries no
verified-on line yet. Stamp one on its next pass.

## The controlled pair

`shiny-docker` and `dash-docker` are **the same EDA dashboard over the same
344-row Palmer Penguins dataset**, built twice. Same sidebar filters, same three
plots, same two tables, same three value boxes, same measured dataset facts
(344 rows · 333 complete cases · 342 rows surviving an all-inclusive filter) —
so any divergence in those numbers means a vendored CSV is wrong, not that the
frameworks disagree.

What differs is everything downstream of the framework choice:

| | shiny-docker | dash-docker |
|---|---|---|
| Reactivity | server-side, over a **WebSocket** | callbacks, over **HTTP POST** |
| State | in-process session — **sticky sessions required** | stateless — inputs ride in the request body |
| Scaling | one process per session pool | `--workers N`, proved across 4 |
| Plot grammar | plotnine (ggplot) → PNG | plotly `graph_objects` → JSON, interactive |
| Cross-filtering | not attempted | box-drag brush, keyed on row ids |
| Image | **863 MB** (scipy + statsmodels via plotnine) | **500 MB** (no pandas, no numpy anywhere) |
| pandas | one unavoidable conversion at the plot edge | none |

The image-size gap and the statefulness gap are the two findings worth carrying
into a real project; both READMEs explain what buys them.

## Anatomy of a stack

Every stack follows the same shape:

```
stacks/<stack-name>/
├── README.md        # verified-on · quick start · dataflow · Evidence · ⚠️ Not verified · lessons
├── justfile         # the front door — every claim in the README has a recipe here
├── <manifest>       # pyproject.toml + uv.lock, package.json, …
└── <source>         # the app itself
```

Read a stack's `README.md` first — the **Evidence** section is the payload, and
the **⚠️ Not verified** section is the part you must not skip before trusting it.

## Running

Each stack is independent and self-contained. `just` is the front door
everywhere; run it with no arguments to see that stack's recipes:

```bash
cd stacks/dash-docker
just            # list recipes
just up         # start, block until healthy
just prove      # make the container show its work
just down
```

Recipe vocabulary is shared where the lifecycle is shared (`build up smoke dev
down`) and stack-specific where it isn't — `pydantic-openapi-react` has no
container to start, so its verbs are `setup gen check gate drift-demo`.

## The dynamic-dashboard family

`stacks/dynamic-dashboard/` is the first *family*: several stacks answering variants of
one question — where should the control/flexibility cutpoint sit between an LLM (or a
config file) and the plots on a dashboard? Everything is held constant except who fills
the typed `PlotSpec`. The family design lives in
[`docs/design/dynamic-dashboard.md`](docs/design/dynamic-dashboard.md), the tracker in
[`docs/progress/dynamic-dashboard.md`](docs/progress/dynamic-dashboard.md).

## Conventions

Layout invariants, the README section contract, and the re-verification rule
live in [`AGENTS.md`](AGENTS.md).

## Sibling repo

[`architecture-poc`](../architecture-poc) is the counterpart: where this repo
asks *does this stack work when deployed*, that one distills **architecture
patterns** from production codebases into small readable references. Same
skeleton, different payload — patterns age slowly, deployment evidence does not.
