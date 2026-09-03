---
summary: Retrospective on the dynamic-dashboard family — what three stacks (LLM via AI SDK, YAML file, LLM via chatlas) taught about where the control/flexibility cutpoint sits in a data→plot pipeline, and what to carry into the next tier or a real project.
read_when: Deciding how much to let a model or a config file decide in any dashboard or report-generating system; planning a declarative-tier stack; writing a contract an LLM will fill; before promising a clinical dashboard "the model can draw anything".
---

# dynamic-dashboard — retrospective on the cutpoint

**The question (2026-09-03, KS):** in a pipeline that turns data into dashboard plots,
where should the cutpoint between *control* and *flexibility* sit — and what does each
position cost?

**The method:** hold everything constant except who fills one typed object, the
**PlotSpec**, and measure. Three stacks, one day:

| stack | filler | language / SDK |
|---|---|---|
| `genui-controlled-nextjs` | LLM, tool call | TypeScript, AI SDK 7, Zod |
| `config-driven-shiny` | a person, YAML file | Python, Pydantic, polars, Shiny |
| `genui-controlled-shiny` | LLM, tool call, on a grid seeded from the file | Python, chatlas, Pydantic |

Evidence lives in each stack's README; the design doc carries the measured table. This
document is the *reading* of that evidence. Claims that are KS's to make carry a 💡.

---

## 1. What held: the contract is the cutpoint, and it travelled

The PlotSpec — two builders, per-dataset column enums, a whitelisted filter and aggregate,
**no free text** — was filled identically by:

- a model through the AI SDK: 20/20 tool choice, 20/20 byte-identical props;
- a person through YAML: 4/4 outputs equal to the model's, float for float;
- a model through chatlas: 20/20 tool choice, 20/20 identical validated specs (run B),
  4/4 equal to the AI SDK stack's specs.

The same words survived Zod and Pydantic (vocabularies proven identical) and a human
author. **The place to spend design effort is the schema, not the prompt and not the
renderer.** Every field is a decision the filler may make; every absent field is a
decision it may not. That sentence did more work than any instruction in the system prompt.

💡 *The claim worth adopting as an invariant:* a plot the system shows a person is
described by a typed spec that carries no prose, whoever fills it.

## 2. What broke, and what each break teaches

**Free text is the drift channel.** With one optional `title` string in the schema, the
model varied it on 2 of 4 intents — punctuation, casing, "vs" versus "—". Every other
field was identical. Delete the field: 20/20. This is the cheapest, most reproducible
result the family produced, and it generalises: *constrain copy as tightly as layout, or
copy is where the variance goes.*

**Humans may write copy; models may not.** The YAML stack gives `title` back to the
person, *outside* the PlotSpec, on a `Card` wrapper. The line is not "no titles" but
"who writes them". Card ≠ PlotSpec is the family's one settled design decision.

**Ambiguous language stays ambiguous.** "Horsepower vs weight" swapped x and y in 2 of 5
runs on the chatlas path and 0 of 10 on the AI SDK path. The contract cannot fix what
the prompt leaves open; it can only make the swap visible (the caption says `wt × hp`).
💡 *Whether to add a rule ("first-named quantity goes on y") or accept the ambiguity is a
product decision, not a schema one.*

**The environment is part of the contract.** chatlas ships tools `strict`; OpenAI strict
mode rejects a union at the root; the AI SDK sent the identical schema non-strict and it
passed untouched. Three keyword edits and one flag later the Python path matched. The
schema was never wrong — the *defaults around it* were different. Record the SDK's
defaults next to the schema, or the next port loses an afternoon.

**HTTP evidence cannot see layout.** The first browser pass found a CSS-grid overflow
and a legend collision that twenty perfect tool calls could not have shown. Every
dashboard stack needs one browser pass, and the repo's standing gap in the two older
dashboards is real.

## 3. What each position on the dial cost

| position | who decides | what it bought | what it cost |
|---|---|---|---|
| Controlled, LLM-filled | model picks builder + props | natural-language intent → plot in ~2–4 s; refusals 3/3 clean | tokens per turn; a consistency run before you trust it; nothing the model says reaches the screen |
| Controlled, file-filled | person edits YAML | zero model, zero cost, live reload, errors that teach in place | a person must know the column names; no "show me…" |
| Both on one grid | file seeds, chat appends | the human's dashboard *plus* exploration | two fillers to keep honest; chat cards are ephemeral |

None of the three positions is "flexible" in the sense the original sketch might have
implied. All three sit at the Controlled tier of the generative-UI spectrum; the family
moved the *filler*, not the tier. That was deliberate — a baseline first — and it is why
the numbers are clean.

## 4. What this implies for the next tier

The obvious next stack is Declarative: let the model compose a *dashboard* (which cards,
which order, how many columns) from the same catalog. The family says what to expect:

- Composition without a composition contract will drift the way `title` did. Templates
  with named slots and eligible categories are the schema for layout; the free-text
  lesson applies to layout descriptions too.
- The equivalence test still works: a declared layout is a `cards.yaml`, so the
  config-driven stack is the oracle for whatever the model composes.
- The consistency check needs to diff *arrangement*, not just props, and N=5 is a
  smoke test, not a rate. Budget for N=20 on the intents that matter.

💡 *Whether the declarative tier is worth building at all* depends on whether a person
would ever ask for "a dashboard about X" rather than "a plot of Y". In the department's
use, the second is the common request.

## 5. What it means for a real project

For a clinical or departmental dashboard — where a wrong plot is a wrong finding:

- **The model selects and fills; it never draws.** Builders are prebuilt; the palette,
  layout, caption and title are derived, never generated. This is the house rule the
  generative-UI skill states for clinical surfaces, and the family measured why.
- **The schema is the review artefact.** A reviewer signs off on the PlotSpec's enums,
  filters and aggregates, not on prompt wording. Changing a column list is a contract
  change and gets an ADR; changing prompt phrasing is not.
- **Refusal is a feature to test**, with the same rigour as success. Three out-of-catalog
  prompts refused 3/3 on both LLM paths; keep that list growing with the requests real
  users make.
- **A file-filled path should exist beside any model-filled path.** It is the oracle, the
  fallback when the key is missing, and the way a person keeps a dashboard after the
  session ends.
- 💡 **What never goes to a model:** row-level data (the family never sent a row; the
  model saw a schema and one-sentence summaries), and anything the schema would need to
  describe with free text to be useful. If a surface needs prose to be right, it is not a
  Controlled-tier surface, and it is not a model-filled one in a clinical setting.

## 6. Open threads (not decisions yet)

- "Save this dashboard": chat cards written back to `cards.yaml`, closing the loop
  between the two fillers. Small; useful; not yet built.
- Multi-turn behaviour on the chatlas path ("now split that by island") is unexercised.
- Cost was dropped from the evidence by choice; the latency gap (AI SDK ~2 s, chatlas
  ~4 s because of a second model call) is the only cost signal recorded.
- The `filter` object inside the PlotSpec versus a reusable "view" object — unchanged by
  three stacks, still open.
