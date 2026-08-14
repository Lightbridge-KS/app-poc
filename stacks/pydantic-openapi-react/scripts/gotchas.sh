#!/usr/bin/env bash
# Re-export the spec with each OpenAPI-shaping flag flipped, and diff the names.
# One of the doc's two flags still earns its place; the other no longer does.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

bold=$'\033[1m'; dim=$'\033[2m'; green=$'\033[32m'; yellow=$'\033[33m'; off=$'\033[0m'

cd "$root/backend"
uv run python scripts/export_openapi.py "$tmp/fixed.json" >/dev/null
POC_UGLY_IDS=1 uv run python scripts/export_openapi.py "$tmp/ugly_ids.json" >/dev/null
POC_SEPARATE_IO=1 uv run python scripts/export_openapi.py "$tmp/split_io.json" >/dev/null

ids() { jq -r '.paths[] | .[] | .operationId' "$1" | sort; }
schemas() { jq -r '.components.schemas | keys[]' "$1" | sort; }

echo
echo "${bold}Gotcha #2 — generate_unique_id_function${off}   ${green}still worth doing${off}"
echo "${dim}These names become your SDK function and hook names.${off}"
paste <(printf 'FastAPI default\n---------------\n'; ids "$tmp/ugly_ids.json") \
      <(printf 'overridden\n----------\n'; ids "$tmp/fixed.json") \
  | column -t -s $'\t' | sed 's/^/  /'

echo
echo "${bold}Gotcha #1 — separate_input_output_schemas${off}   ${yellow}no longer does anything${off}"
echo "${dim}The doc says set it to False to collapse Input/Output. Flipping it now:${off}"
if diff -q <(schemas "$tmp/fixed.json") <(schemas "$tmp/split_io.json") >/dev/null; then
    echo "  ${yellow}no difference — the emitted schemas are byte-identical either way${off}"
else
    echo "  the flag changed the spec:"
    diff <(schemas "$tmp/fixed.json") <(schemas "$tmp/split_io.json") | sed 's/^/  /'
fi

echo
echo "${dim}  Why: on FastAPI 0.141 + Pydantic 2.13 a plain default no longer makes the${off}"
echo "${dim}  validation and serialization schemas differ, so there is nothing to collapse —${off}"
echo "${dim}  and when they genuinely do differ (ReportDraft's computed field), FastAPI forces${off}"
echo "${dim}  the split regardless. See fastapi/_compat/v2.py:${off}"
echo "${dim}      separate_input_output_schemas or _has_computed_fields(field)${off}"
echo
echo "  The split that survives, and which the frontend must model as two types:"
schemas "$tmp/fixed.json" | grep -E '^ReportDraft' | sed 's/^/    /'

echo
echo "${bold}Gotchas #3, #4, #5 — read them off the generated types${off}"
echo "${dim}  #3 datetime → string${off}"
rg -n "acquired_at" "$root/frontend/src/api/schema.d.ts" | head -1 | sed 's/^/    /'
echo "${dim}  #4 str Enum → literal union${off}"
rg -n "Modality:" "$root/frontend/src/api/schema.d.ts" | head -1 | sed 's/^/    /'
echo "${dim}  #5 typed errors → the 404 branch is ErrorOut, not any${off}"
rg -n "ErrorOut" "$root/frontend/src/api/orval/poc.ts" | head -1 | sed 's/^/    /'
echo
