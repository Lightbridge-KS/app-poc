---
summary: Tracker for the dynamic-dashboard PoC family — genui-controlled-nextjs first, then config-driven and a Shiny sibling.
read_when: Starting or resuming work on any stacks/dynamic-dashboard/* stack; checking what is landed, deferred, or still open.
---

# dynamic-dashboard — progress

Design: [`docs/design/dynamic-dashboard.md`](../design/dynamic-dashboard.md) ·
Concept sketch: [`docs/ideas/dynamic-dashboard/concept.excalidraw`](../ideas/dynamic-dashboard/concept.excalidraw) ·
Decisions record: `~/.lightbridge/projects/-Users-kittipos-my_poc-app_poc/asks/2026-09-03_1725_dynamic-dashboard-genui-controlled-design-decisions.md`

## Now: `genui-controlled-nextjs` (2026-09-03)

Controlled-tier generative UI: chat → LLM selects a plot builder and fills its typed
PlotSpec → server transforms → Plotly card in a grid.

- [x] Scaffold (Next.js 16, AI SDK 7, pnpm) + data (`penguins.csv`, `mtcars.csv`)
- [x] Catalog: datasets, Zod schema, transform, tools + `just check` self-checks
- [x] Route + UI: `/api/chat`, ChatRail, CardGrid, PlotCard
- [x] `just catalog` (JSON Schema of the tools)
- [x] `just prove`: consistency N=5 per prompt, out-of-catalog refusal
- [ ] Browser E2E via Chrome automation, screenshot — **blocked 2026-09-03**: extension returned an error page for `localhost`; recorded as the stack's ⚠️ Not verified gap
- [x] Docs: stack README (contract), design doc, root README + PROOF rows, AGENTS.md amendments, excalidraw retrofit
- [ ] PR

## Next

- `config-driven` variant: a YAML file fills the same PlotSpec; no LLM. Reuses `src/catalog/*` shape.
- `genui-controlled-shiny`: Shiny for Python + chatlas, Pydantic PlotSpec, same catalog.

## Deferred

- Latency / token cost per turn (dropped from the evidence set by choice, 2026-09-03).
- Docker image for this stack.
- Declarative tier (LLM emits a whole dashboard layout against the catalog).

## Confirmed contracts

- **No free-text prop in a PlotSpec.** Run 1 of `just prove` (2026-09-03): with an optional `title`, it was the only field that drifted (2/4 intents). Run 2 without it: 20/20 identical. Copy is derived from the spec on the client.
- `gpt-5.6-terra` at `reasoningEffort: low` accepts a `oneOf`-rooted (discriminated-union) tool schema and picks the right tool 20/20 on the four intents.
- The seam is the **PlotSpec** (tool `inputSchema`). Who fills it is the only variable across the family.
- The LLM never receives rows: `execute` returns rows to the card, `toModelOutput` returns a one-line summary to the model.
- Out-of-catalog requests are refused in text, never approximated with a builder.

## Open questions

- 💡 Refusal as text vs a typed `decline` tool — decide once the refusal evidence is in.
