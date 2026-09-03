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
- [x] Browser E2E via Chrome automation, screenshot — 2026-09-03, second attempt: the first failed because the MCP session was driving a *remote Linux* Chrome (Browser 2), not this Mac; `select_browser` fixed it. Two cards asserted, `docs/screenshot.jpg` saved, two layout bugs found + fixed. KS had also verified by hand after PR #1.
- [x] Docs: stack README (contract), design doc, root README + PROOF rows, AGENTS.md amendments, excalidraw retrofit
- [x] PR — https://github.com/Lightbridge-KS/app-poc/pull/1 (draft, `b136775`)

## Now: `config-driven-shiny` (2026-09-03)

YAML fills the same PlotSpec; Shiny for Python + Plotly renders; no LLM.

- [x] Scaffold (uv, Python 3.13, Shiny 1.7, Plotly 7, Pydantic 2.13, polars 1.44) + data
- [x] Catalog port: datasets, Pydantic schema, polars transform, build — key-for-key with the TS output
- [x] Fixtures vendored from nextjs (`just fixtures` added there) · `just check` 13/13 · `just prove` all ✓
- [x] Shiny app: file_reader, per-card validation, error cards, Plotly from package
- [x] Browser pass: four cards, live reload in 3 s, error card in place; three screenshots in `docs/`
- [x] Docs: README, design doc (Card vs PlotSpec), root README + PROOF rows
- [x] PR — https://github.com/Lightbridge-KS/app-poc/pull/2 (draft)

## Now: `genui-controlled-shiny` (2026-09-03)

Chat pane on the Python catalog; grid seeded from cards.yaml; chatlas tool calls.

- [x] Scaffold (uv, Shiny 1.7, chatlas 0.22, openai 3.7) + catalog copied from config-driven-shiny
- [x] `agent.py`: PlotSpec adapters → OpenAI-shaped tool schema; `strict=False`; direct tool registration
- [x] `dashboard.py`: seed + chat; cards synced on stream success; missing key is a message
- [x] `just check` 6/6 · `just prove` run A + run B pasted · browser pass, two screenshots
- [x] Docs: README, design doc (measured table), root README + PROOF rows, sketch
- [ ] PR

## Next

- "Save this dashboard": write chat cards back to cards.yaml (closes the loop between the two fillers).

## Deferred

- Latency / token cost per turn (dropped from the evidence set by choice, 2026-09-03).
- Docker image for this stack.
- Declarative tier (LLM emits a whole dashboard layout against the catalog).

## Confirmed contracts

- **SDK defaults are part of the contract's environment.** chatlas `strict=True` + OpenAI strict mode reject the union-at-root the AI SDK sends non-strict. Record the SDK's default with the schema.
- **Card ≠ PlotSpec.** The PlotSpec is the cross-stack contract (no free text); a Card adds what the filler is trusted with (`kind`, and `title` for humans). Compare PlotSpecs across stacks, never Cards.
- **HTTP evidence cannot see layout.** The browser pass found a CSS-grid overflow (Plotly canvas widening a `1fr` track) and a legend/axis collision that `just prove` was blind to. Every dashboard stack needs one browser pass.

- **No free-text prop in a PlotSpec.** Run 1 of `just prove` (2026-09-03): with an optional `title`, it was the only field that drifted (2/4 intents). Run 2 without it: 20/20 identical. Copy is derived from the spec on the client.
- `gpt-5.6-terra` at `reasoningEffort: low` accepts a `oneOf`-rooted (discriminated-union) tool schema and picks the right tool 20/20 on the four intents.
- The seam is the **PlotSpec** (tool `inputSchema`). Who fills it is the only variable across the family.
- The LLM never receives rows: `execute` returns rows to the card, `toModelOutput` returns a one-line summary to the model.
- Out-of-catalog requests are refused in text, never approximated with a builder.

## Open questions

- 💡 Refusal as text vs a typed `decline` tool — decide once the refusal evidence is in.
