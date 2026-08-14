# Pydantic is the contract

A runnable PoC for the argument in
[`docs/design/openapi-spec-from-pydantic.md`](docs/design/openapi-spec-from-pydantic.md):
the Python types *are* the API contract, TypeScript is generated downstream, and **schema
drift becomes a compile error instead of a runtime 422**.

Thin FastAPI backend, React + TS + Vite frontend, radiology studies and reports. Not one
request or response type is written twice.

Built 2026-08-14 on macOS / Apple Silicon, FastAPI 0.141 + Pydantic 2.13. ⚠️ The date is
reconstructed from the working session rather than stamped by a verification run — re-run
`just gate` and re-stamp this line on the next pass.

```
   ┌─────────────────────────────────────────────────┐
   │  SSOT: Pydantic models + route signatures (.py)  │
   └───────────────────────┬─────────────────────────┘
                           │  app.openapi()   ← no server booted
                           ▼
                  ┌──────────────────┐
                  │  openapi.json    │  ← committed artifact
                  └────────┬─────────┘
              ┌────────────┴────────────┐
              ▼                         ▼
     openapi-typescript              orval
     + openapi-fetch          SDK · hooks · MSW mocks
              │                         │
              └────────────┬────────────┘
                           ▼
              TS app code — compile error if drift
```

## Run it

```bash
just setup     # uv sync + npm install
just dev       # FastAPI on :8000, Vite on :5173
```

Open <http://localhost:5173>. Two tabs, same backend, same `openapi.json` — one wired with
`openapi-fetch`, one with `orval`. Click a study row to report it.

## See the point

```bash
just drift-demo
```

Renames `ReportIn.impression` on the Python side, regenerates, and lets `tsc` object — then
adds a required field and does it again. Both mutations are reverted on exit. Output:

```
✗ tsc rejected the frontend — drift caught at compile time:
    src/pages/FetchPage.tsx(51,25): error TS2353: ... 'impression' does not exist in type
    src/pages/OrvalPage.tsx(116,33): error TS2353: ... 'impression' does not exist in type 'ReportIn'
```

That is the whole thesis. A backend PR renaming a field cannot merge without the frontend
changing in the same commit.

## The rest of the recipes

| Command | Does |
|---|---|
| `just gen` | models → `openapi.json` → `schema.d.ts` + orval SDK |
| `just check` | `tsc -b --force` — does the app still compile against the contract? |
| `just gate` | the CI check: fails if any committed artifact is stale, then typechecks |
| `just gotchas` | flips the doc's two OpenAPI flags and shows which still does anything |
| `just web-mock` | serves the whole app from orval's generated MSW mocks, no Python running |

`just gate` is deliberately git-free — it regenerates into a temp dir and diffs, so it behaves
identically here and in CI. [`.github/workflows/ci.yml`](.github/workflows/ci.yml) shows the
same gate in the doc's literal `git diff --exit-code` form. Nothing is pushed anywhere.

## What the two clients actually cost

Both tabs render identical markup (`src/components.tsx`), so the only thing that differs is
the data layer.

| | openapi-typescript + openapi-fetch | orval |
|---|---|---|
| Generated | one `schema.d.ts` | 15 files: hooks, models, MSW handlers, faker |
| Call site | `api.POST('/studies/{study_id}/report', {…})` | `useCreateReport().mutate({…})` |
| Enums | type only — you hand-write the list, pinned with `satisfies` | type **and** runtime value |
| Errors | `{ data, error }` | union discriminated on `status`, so 404 and 409 are separate branches |
| Caching | yours to write | TanStack Query, included |
| Mocks | — | MSW handlers, generated |
| Needs operationIds | no | yes — hook names come from them |

The honest summary: `openapi-fetch` is the smaller, more legible thing and makes the type
flow obvious, which is why the doc defaults to it. orval earns its extra machinery when you
want caching and mocks anyway — and its status-discriminated errors are genuinely stronger.

## Two findings worth carrying forward

Both are written up in [`docs/GOTCHAS.md`](docs/GOTCHAS.md), which pins all five of the doc's
gotchas to the lines that demonstrate them.

**1. The doc's gotcha #1 advice is now stale.** `separate_input_output_schemas=False` no
longer does anything on FastAPI 0.141 + Pydantic 2.13 — `just gotchas` proves it by flipping
the flag and showing an identical spec. A plain default no longer splits a model, and when
schemas genuinely differ (a `@computed_field`) FastAPI forces the split regardless:

```python
# fastapi/_compat/v2.py
override_mode = None if (separate_input_output_schemas or _has_computed_fields(field)) else "validation"
```

The fix is a modelling decision, not a flag. Gotcha #2 (`generate_unique_id_function`), by
contrast, is still very much worth doing.

**2. `tsc --noEmit` can silently check nothing.** Vite's React-TS template ships a root
`tsconfig.json` with `"files": []` and project references; a bare `tsc --noEmit` checks zero
files and exits 0. Wire that into your gate and it stays green through any amount of drift.
The check here is `tsc -b --force`. Before trusting a gate that passes, confirm it fails.

## Layout

```
backend/app/models.py     ← the SSOT. Everything downstream derives from it
backend/app/routes.py     ← route signatures + typed error responses
backend/app/main.py       ← where the OpenAPI shape is tuned
backend/scripts/export_openapi.py
openapi.json              ← committed artifact
frontend/src/api/schema.d.ts   ← generated, never hand-edited
frontend/src/api/orval/        ← generated, never hand-edited
frontend/src/pages/            ← one page per client
scripts/drift_demo.sh
```
