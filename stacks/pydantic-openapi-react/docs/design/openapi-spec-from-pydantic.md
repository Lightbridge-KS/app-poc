---
summary: The argument for treating Pydantic models as the API contract and generating TypeScript downstream — now grounded in the working PoC in this repo, with two of its original claims corrected.
read_when: Deciding whether to adopt code-first OpenAPI on a project, or looking for the reasoning behind how this repo is wired.
---

# OpenAPI as the contract, generated *from* your Pydantic models

> **Status:** this started as a standalone argument and is now backed by a working PoC in
> this repo. Every claim below either points at running code or has been corrected where the
> code proved it wrong. Run `just dev` for the app, `just drift-demo` for the payoff.
> The [README](../../README.md) is the tour; this doc is the reasoning.

## The core idea

FastAPI already derives an OpenAPI 3.1 document from your Pydantic models and route
signatures. So you don't hand-write a contract — the Python types *are* the contract, and
TypeScript is generated downstream.

```
   ┌─────────────────────────────────────────────────┐
   │  SSOT: Pydantic models + route signatures (.py)  │
   │        backend/app/models.py, routes.py          │
   └───────────────────────┬─────────────────────────┘
                           │  app.openapi()   ← no server booted
                           ▼
                  ┌──────────────────┐
                  │  openapi.json    │  ← committed artifact
                  └────────┬─────────┘
                           │  codegen (openapi-typescript / orval)
                           ▼
              ┌─────────────────────────────┐
              │  frontend/src/api/schema.d.ts│  ← never hand-edited
              │  + typed client wrapper      │
              └─────────────────────────────┘
                           │
                           ▼
                  TS app code (compile error if drift)
```

Drift becomes a **compile error**, not a runtime 422.

That sentence is the whole bet, so the PoC makes it falsifiable. `just drift-demo` renames
`ReportIn.impression` in Python, regenerates, and lets `tsc` object:

```
src/pages/FetchPage.tsx(51,25): error TS2353: Object literal may only specify known
  properties, and 'impression' does not exist in type '{ findings: string; conclusion: string; … }'
src/pages/OrvalPage.tsx(116,33): error TS2353: … 'impression' does not exist in type 'ReportIn'
```

Both clients, one backend edit, zero runtime traffic.

## Concrete pipeline

**1. Dump the spec without booting a server** (fast, CI-friendly) —
[`backend/scripts/export_openapi.py`](../../backend/scripts/export_openapi.py):

```python
import json
from app.main import app

with open("openapi.json", "w") as f:
    json.dump(app.openapi(), f, indent=2)
```

**2. Generate TS types:**

```bash
npx openapi-typescript openapi.json -o src/api/schema.d.ts
```

**3. Use a *typed* fetch client** so paths, params, and bodies are all checked —
[`frontend/src/api/client.ts`](../../frontend/src/api/client.ts):

```ts
import createClient from "openapi-fetch";
import type { paths } from "./schema";

export const api = createClient<paths>({ baseUrl: "/api" });

// path, method, body, and response are all inferred
const { data, error } = await api.POST("/studies/{study_id}/report", {
  params: { path: { study_id: studyId } },
  body: { findings: "...", impression: "..." },  // ← type-checked vs Pydantic
});
```

In this repo the whole chain is `just gen`, and the three steps are ~15 lines of config total.

## Enforcing it in CI (the part people skip)

Committing `openapi.json` and regenerating in CI lets you fail the build on drift:

```bash
python scripts/export_openapi.py
git diff --exit-code openapi.json || \
  { echo "OpenAPI changed — regenerate TS client"; exit 1; }
```

Same trick for `schema.d.ts`. Now a backend PR that renames a field can't merge without the
frontend being updated in the same commit. That form lives in
[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).

**One refinement the PoC added:** `just gate` does the same job *without* git — it regenerates
into a temp dir and `diff`s. That means the gate runs identically on an un-versioned checkout,
in a worktree, or in CI, and you can test it locally before trusting it. Which you should:

```
✗ openapi.json is stale — the Python models changed. Run: just gen
```

**Verify your gate fails before you trust it passing.** See the last gotcha for why that
sentence is not boilerplate.

## Tool choices

The PoC implements the first and third rows side by side over one spec — two tabs, identical
markup ([`src/components.tsx`](../../frontend/src/components.tsx)), so the only variable is the
data layer.

| Tool | Gives you |
|---|---|
| `openapi-typescript` + `openapi-fetch` | Types only + ~6kb client. Minimal, my default |
| `@hey-api/openapi-ts` | Full SDK with named functions, optional Zod schemas |
| `orval` | SDK + TanStack Query hooks + MSW mocks |

What running both actually surfaced:

| | openapi-fetch | orval |
|---|---|---|
| Generated | one `schema.d.ts` | 15 files: hooks, models, MSW handlers, faker |
| Errors | `{ data, error }` | union discriminated on `status` — **404 and 409 are separate typed branches** |
| Enums | type only; hand-write the list and pin it with `satisfies` | type **and** runtime value, so `Object.values(Modality)` just works |
| Needs good operationIds | no | yes — hook names come from them |
| Mocks | — | `just web-mock` serves the whole app from generated MSW handlers, no Python running |

The honest read: `openapi-fetch` stays the better default because the type flow is *legible* —
you can see exactly where safety comes from. orval earns its machinery when you want caching
and mocks anyway, and its status-discriminated errors are genuinely stronger than
`{ data, error }`. Pick by whether you already need TanStack Query, not by type safety —
both are safe.

If you want **runtime** validation on the TS side too (not just compile-time), generate Zod
schemas — useful when the backend is a separate deploy and could be a version behind. Not
implemented here.

## Gotchas worth knowing up front

Each is pinned to running code in [`docs/GOTCHAS.md`](../GOTCHAS.md); `just gotchas`
prints the first two live.

- **~~Split input/output schemas.~~ This advice is stale — see below.**
- **Ugly generated names.** Override `generate_unique_id_function` to get `createReport`
  instead of `create_report_studies__study_id__report_post`. ✅ Still true, still worth doing,
  and it is what decides whether orval hands you `useCreateReport` or
  `useCreateReportStudiesStudyIdReportPost`. See `camel_operation_id` in
  [`backend/app/main.py`](../../backend/app/main.py).
- **Dates are strings.** `datetime` → `string` in TS. Decide once whether you parse at the
  client boundary. ✅ The PoC parses at the boundary in `parseStudy()`, and renames the field
  `acquired_at` → `acquiredAt` on the way through so an unparsed study is structurally
  incompatible with a parsed one — the decision is enforced, not just documented.
- **Enums.** Use `str, Enum` in Python so they land as string literal unions, not opaque ints.
  ✅ Confirmed: `Modality: "CT" | "MR" | "XR" | "US"`.
- **Errors aren't typed by default.** Declare `responses={404: {"model": ErrorOut}}`
  explicitly or your error branch stays `any`. ✅ Confirmed — with a wrinkle the original
  draft missed: FastAPI's stock `HTTPException` serialises to `{"detail": ...}`, which does
  **not** match the `ErrorOut` you just declared. Declaring one shape and returning another is
  the same drift wearing a different hat. Hence
  [`backend/app/errors.py`](../../backend/app/errors.py).

### Correction: `separate_input_output_schemas` no longer does anything

The original claim was:

> Pydantic v2 + FastAPI generates `FooInput`/`FooOutput` when a model has defaults. Set
> `FastAPI(separate_input_output_schemas=False)` if you want one TS type.

On **FastAPI 0.141 + Pydantic 2.13, neither half survives contact with the code.**
`just gotchas` flips the flag and shows a byte-identical spec.

- *A plain default no longer splits anything.* Pydantic 2.13 emits identical validation and
  serialization schemas for a model like `ReportIn`. There is one `ReportIn`, flag or no flag.
- *When schemas genuinely do differ, the flag is ignored.* From `fastapi/_compat/v2.py`:

  ```python
  override_mode = None if (separate_input_output_schemas or _has_computed_fields(field)) else "validation"
  ```

  A computed field forces separation whichever way you set it.

What actually splits a model now is both of these at once: its validation and serialization
schemas genuinely differ (a `@computed_field`, or asymmetric aliases), **and** it is used in
both a request body and a response. `ReportDraft` in the PoC meets both and yields
`ReportDraft-Input` / `ReportDraft-Output`.

So the fix is a **modelling decision, not a flag**: either let the split stand — the client
genuinely may not send a server-derived field, and two types is the honest encoding of that —
or drop the computed field and derive it client-side. Reaching for the flag and assuming it
worked is the one option that leaves you wrong.

### New gotcha: `tsc --noEmit` can silently check nothing

Not in the original draft, and the most dangerous thing found while building the PoC.

Vite's React-TS template ships a root `tsconfig.json` with `"files": []` and project
references. A bare `tsc --noEmit` against it type-checks **zero files and exits 0**. Wire that
into your gate and the whole scheme stays green through unlimited drift, while looking
enforced. The check must be `tsc -b --force`.

This is the failure mode the whole approach is supposed to prevent, reintroduced by the tool
meant to catch it. It is also why `just drift-demo` exists as a *test of the gate* rather than
a demo of the happy path.

## The inverse approach

Spec-first: hand-write `openapi.yaml`, generate *both* Pydantic models and TS. Better when
multiple teams/languages consume the API, or when the API is the product. Worse ergonomics for
a solo/small team — you lose FastAPI's natural flow. For RAMAAI-scale work, code-first from
Pydantic is almost certainly the right trade.

Building the PoC didn't move that conclusion, but it did sharpen the cost: code-first buys
excellent ergonomics and pays for it in **vigilance about the generation step**. The contract
is only real if the gate is real. Two of the five original gotchas turned out to be wrong or
incomplete within a couple of releases, and the gate itself could silently no-op — so budget
for occasionally re-testing that your pipeline still does what you think it does, rather than
setting it up once and trusting it forever.
