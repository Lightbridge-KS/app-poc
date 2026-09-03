---
summary: Family-level design for the dynamic-dashboard PoCs — the PlotSpec seam, the generative-UI tier per surface, catalog and composition contracts, security posture, determinism plan.
read_when: Building or reviewing any stacks/dynamic-dashboard/* stack; deciding how much freedom a variant gives the LLM or a config file; adding a builder or a dataset.
---

# dynamic-dashboard — design

**Question the family answers:** where should the control/flexibility cutpoint sit in a
pipeline that turns data into dashboard plots — and what does each position cost in
determinism, safety, and expressiveness?

**Method:** hold everything constant except *who fills the PlotSpec*.

```
 RawData ──► CleanedData ──► Transform ──► Builder ──► Card
  (CSV)       fixed per      whitelisted   Scatter |    in the
              dataset,       ops: filter,  Bar          dashboard grid
              no LLM         group_by+agg
                         ▲
                         │  PlotSpec = the catalog contract (Zod / Pydantic)
                    ┌────┴──────────────────────────┐
                    │ LLM tool call   genui-controlled-nextjs  (built)
                    │ LLM tool call   genui-controlled-shiny   (built)
                    │ YAML file       config-driven-shiny      (built)
                    │ layout JSON     declarative tier         (deferred)
                    └───────────────────────────────┘
```

The seam is the **PlotSpec**. Its schema is the whole contract: every field is a decision
the filler may make; every absent field is a decision it may not. Clean and Transform are
deterministic and shared; the Builders are prebuilt components; only the filler varies.

## Generative UI (per the `generative-ui` skill)

**Runs in:** our own Next.js app — no super-host; the dashboard is the product.
**Model emits:** a tool call + props (Controlled). Nothing else.

| surface | tier | rubric line | protocol (verified) |
|---|---|---|---|
| Plot card (scatter, bar) | **Controlled** | rubric 2: the few brand-defining surfaces; a wrong plot is a wrong finding | AI SDK 7 tool call → typed `tool-<name>` UI message part (verified 2026-09-03 against ai-sdk.dev) |
| Chat text (refusals, errors) | Controlled (text only) | rubric 1: a refusal must not be dressed up as a plot | same stream, `text` parts |
| Dashboard layout | **not model-controlled** | — | fixed template, see Composition |

House default for analytics is Declarative; this family deliberately starts one notch
tighter (Controlled) to measure the baseline, then relaxes in later variants.

### Catalog

Two entries. The authoritative form is the tools' JSON Schema, printed by `just catalog`
in each stack; the summary:

| tool | required props | optional props | data reference | actions | copy the model may write |
|---|---|---|---|---|---|
| `scatter_plot` | `dataset`, `x`, `y` (numeric col enums per dataset) | `color` (categorical enum), `filter[≤3]` | server loads the dataset; model never sees rows | none (card is inert; dismiss is client-side) | none |
| `bar_plot` | `dataset`, `by` (categorical enum), `measure` (`count` \| `mean`/`median` of a numeric col) | `color`, `filter[≤3]` | same | none | none |

`Filter = {column ∈ dataset cols, op ∈ == != > >= < <= in, value: number | string | string[]}`.
Column enums are per dataset (discriminated union on `dataset`), so an unknown column is a
schema error, not a runtime guess.

Representative queries — scatter: "flipper length vs body mass by species", "hp against
weight for 6- and 8-cylinder cars". Bar: "how many penguins per island", "average mpg by
cylinders", "median body mass by species split by sex".

Constraints: one card per tool call; cards are repeatable; no slot choice. Captions and
plot titles are derived from the spec by the client, never written by the model. (An
optional `title` prop was in the first draft; `just prove` showed it was the only field that
ever drifted, so it was removed — see the nextjs stack's Evidence.)

### Composition

```
Template  Dashboard
└── Slot  chat rail (left, fixed)      eligible: ChatRail          cardinality 1
└── Slot  card grid (right)            eligible: PlotCard          cardinality 0..n, call order
```

No other slot exists; the model cannot place, size, or reorder anything.

### Security posture

- Controlled: the model invokes only the two shipped tools; inputs are schema-validated
  before `execute`; outputs are typed objects rendered by our own React component.
- No PHI anywhere in this family (public teaching datasets). If a future variant touches
  hospital data, the Controlled tier is the ceiling and Open-ended is excluded.
- The model receives only the schema and one-line summaries of prior tool results
  (`toModelOutput`); rows never enter the prompt.

### Determinism plan

- Consistency check: `just prove` sends each of K=4 intents N=5 times through the real
  HTTP route and diffs tool choice **and** every prop. Any drift is reported per field.
- Refusal check: 3 out-of-catalog prompts must yield text and zero tool calls.
- No human gate: cards are inert; nothing changes state outside the browser.
- Model pinned per stack (`OPENAI_MODEL`); reasoning effort `low`. GPT-5-family models
  expose no temperature.

## Cutpoint ladder (what each variant relaxes)

| variant | who fills PlotSpec | transform freedom | layout freedom | what it buys down |
|---|---|---|---|---|
| genui-controlled-nextjs | LLM, tool call | whitelisted ops | none | can an LLM drive a Controlled surface *consistently*? |
| genui-controlled-shiny | LLM, chatlas tool call, seeded from the YAML | whitelisted ops | file's `columns`; chat appends | same question in Python. **Built**: tool choice 20/20, validated specs 20/20 identical in run B (one x/y swap on "vs" in 2/5 in run A), refusals 3/3, majority specs 4/4 equal to the nextjs Run-2 specs. |
| config-driven-shiny | YAML file | whitelisted ops | `columns: 1\|2`, card order, human `title` per card | is the PlotSpec a good *human* authoring surface with no LLM at all? **Built**: 4/4 outputs equal the nextjs stack's, Pydantic and Zod vocabularies identical, bad cards fail in place. |
| declarative (deferred) | LLM, layout JSON | whitelisted ops | templates + slots | how much composition can be handed over before drift bites? |

## What the three stacks measured (2026-09-03)

| | genui-controlled-nextjs | config-driven-shiny | genui-controlled-shiny |
|---|---|---|---|
| filler | LLM tool call (AI SDK) | YAML file | LLM tool call (chatlas) |
| tool choice | 20/20 | — | 20/20 |
| identical specs | 20/20 once `title` removed | 4/4 equal to nextjs outputs | 20/20 (run B); 18/20 (run A, x/y swap on "vs") |
| refusals | 3/3 | 4 bad cards → 4 teaching errors | 3/3 |
| cross-stack | — | outputs ≡ nextjs, vocabulary ≡ Zod | specs ≡ nextjs Run 2, 4/4 |
| median turn | 1.6–2.2 s | n/a | 3.5–4.5 s (chatlas adds a closing-text call) |

The contract survives two languages, two SDKs and a human filler unchanged. The SDK
defaults do not: chatlas ships tools `strict`, and OpenAI strict mode rejects a union at
the root, so the identical schema needed `strict=False` and three keyword edits to be
accepted where the AI SDK sent it as-is.

## Card vs PlotSpec (settled 2026-09-03, config-driven-shiny)

The **PlotSpec** is the contract and carries no free text. A **Card** wraps a PlotSpec with
what the *filler* is trusted with: `kind` (explicit, since a file has no tool call) and,
for human fillers only, an optional `title`. The LLM tier never gets `title`; the file
tier does. The equivalence and contract checks compare PlotSpecs, never Cards.

## Retrospective

The reading of the three stacks' evidence — what held, what broke, what it implies for the
next tier and a real project — is [`dynamic-dashboard-retrospective.md`](dynamic-dashboard-retrospective.md).

## Open questions

- 💡 Refusal as text vs a typed `decline` tool (typed = machine-checkable, but a third catalog entry).
- 💡 Whether `filter` belongs in the PlotSpec at all, or in a separate, reusable "view" object — unchanged by config-driven-shiny; the YAML reads fine with inline filters at four cards.
