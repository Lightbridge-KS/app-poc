---
summary: The five gotchas from the source doc, each pinned to the line of code that demonstrates it — including the one whose advice is now stale.
read_when: Adopting this pipeline on a real project, or wondering why a generated TS type looks the way it does.
---

# The five gotchas, as running code

Companion to [`design/openapi-spec-from-pydantic.md`](design/openapi-spec-from-pydantic.md),
which argues the approach; this file is the sharp edges in detail.

Each entry names the file that demonstrates it and what you can run to see it.
`just gotchas` prints the first two live.

---

## 1. Split input/output schemas — **the doc's advice is stale**

> The doc says: *"Pydantic v2 + FastAPI generates `FooInput`/`FooOutput` when a model has
> defaults. Set `FastAPI(separate_input_output_schemas=False)` if you want one TS type."*

On **FastAPI 0.141 + Pydantic 2.13, neither half of that still holds.** This PoC ships the
proof rather than the claim — `just gotchas` flips the flag and shows the emitted spec is
byte-identical either way.

**What changed.** Two separate things:

- *A plain default no longer splits anything.* Pydantic 2.13 emits identical validation and
  serialization schemas for a model like `ReportIn` (`findings`, `impression`,
  `critical: bool = False`). There is one `ReportIn` in the spec, flag or no flag.
- *When schemas genuinely do differ, the flag is ignored.* From `fastapi/_compat/v2.py`:

  ```python
  override_mode = None if (separate_input_output_schemas or _has_computed_fields(field)) else "validation"
  ```

  A computed field forces separation whichever way the flag is set.

**What actually splits a model now** — both conditions at once:

1. its validation and serialization schemas genuinely differ (a `@computed_field`, or
   asymmetric `validation_alias`/`serialization_alias`), **and**
2. it is used in *both* a request body and a response.

`ReportDraft` in `backend/app/models.py` meets both — it carries an `is_complete` computed
field and is PUT in and echoed back — so the spec contains:

```
ReportDraft-Input     ← what the client may send  (no is_complete)
ReportDraft-Output    ← what the server returns   (readonly is_complete: boolean)
```

**So the fix is a modelling decision, not a flag.** Either let the split stand and treat the
two shapes as what they honestly are — the client genuinely may not send a server-derived
field — or drop the computed field and derive it client-side. This PoC lets it stand.

The one thing not to do is reach for `separate_input_output_schemas=False` and assume it
worked. It is kept in `main.py` only to document the intent, with a comment saying so.

---

## 2. Ugly generated names — **still worth doing**

`backend/app/main.py:camel_operation_id` overrides `generate_unique_id_function`.
This flag very much still works:

| FastAPI default | Overridden |
|---|---|
| `create_report_studies__study_id__report_post` | `createReport` |
| `list_studies_studies_get` | `listStudies` |

It matters because the operationId is what SDK generators name things after. It is the
difference between orval giving you `useCreateReport` and
`useCreateReportStudiesStudyIdReportPost`. `openapi-fetch` never uses operation ids at all
— another small way the two tools differ.

---

## 3. Dates are strings

`acquired_at: datetime` in Python arrives as `acquired_at: string` in `schema.d.ts`. JSON has
no date type; nothing can change that.

The doc says decide once whether you parse at the boundary. **This PoC parses at the
boundary** — `parseStudy()` in `frontend/src/api/client.ts` is the only place a date string
becomes a `Date`:

```ts
export type ParsedStudy = Omit<Study, 'acquired_at'> & { acquiredAt: Date }
```

The rename from `acquired_at` to `acquiredAt` is deliberate: it makes the parsed type
structurally incompatible with the raw one, so a component can't accidentally accept an
unparsed study.

---

## 4. Enums

`Modality(str, Enum)` in Python lands as a literal union:

```ts
Modality: "CT" | "MR" | "XR" | "US";
```

Drop the `str` base and these become opaque integers. The two clients then diverge:

- **openapi-fetch** gives you the *type* only, so the PoC hand-writes the list and pins it
  with `satisfies readonly Modality[]` (`client.ts`). Typo an entry → compile error.
- **orval** additionally emits a runtime *value*, so `OrvalPage.tsx` iterates
  `Object.values(Modality)` and there is no list to keep in sync at all.

---

## 5. Errors aren't typed by default

Each route declares its failures:

```python
responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}}
```

Without this the error branch is an untyped blob and `error.message` doesn't compile.

One thing the doc doesn't mention and this PoC had to solve: FastAPI's stock `HTTPException`
serialises to `{"detail": ...}`, which does **not** match the `ErrorOut` you just declared.
Declaring one shape and returning another is the same drift by another route. Hence
`backend/app/errors.py` — a small `ApiError` plus handler that renders the declared model.

The two clients narrow differently, and orval's is stronger:

| | openapi-fetch | orval + fetch |
|---|---|---|
| Shape | `{ data, error }` | union discriminated on `status` |
| 404 vs 409 | both land in `error` | `res.status === 404` and `409` are separate branches |

---

## Not in the doc, but bit us here

**`tsc --noEmit` can silently check nothing.** Vite's React-TS template ships a root
`tsconfig.json` with `"files": []` and project references. A bare `tsc --noEmit` against it
type-checks *zero* files and exits 0 — which would make this entire PoC's central claim
untestable while looking green. The check is `tsc -b --force` (see `frontend/package.json`).

If you adopt this pipeline, verify your gate fails before you trust it passing.
