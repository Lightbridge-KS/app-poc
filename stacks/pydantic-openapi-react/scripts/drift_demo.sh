#!/usr/bin/env bash
# The whole thesis, in about ten seconds.
#
# Mutate the Pydantic models, regenerate the contract, and let `tsc` object.
# Every mutation is reverted on exit, including on Ctrl-C or failure.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
models="$root/backend/app/models.py"
backup="$(mktemp)"

bold=$'\033[1m'; dim=$'\033[2m'; red=$'\033[31m'; green=$'\033[32m'; off=$'\033[0m'

cp "$models" "$backup"
restore() {
    cp "$backup" "$models"
    rm -f "$backup"
    # Leave the committed artifacts consistent with the restored models.
    (cd "$root/backend" && uv run python scripts/export_openapi.py >/dev/null 2>&1)
    (cd "$root/frontend" && npm run gen --silent >/dev/null 2>&1)
    echo
    echo "${dim}Models, spec and generated types restored.${off}"
}
trap restore EXIT INT TERM

regenerate() {
    (cd "$root/backend" && uv run python scripts/export_openapi.py >/dev/null) || return 1
    (cd "$root/frontend" && npm run gen --silent >/dev/null 2>&1) || return 1
}

# Runs tsc and reports whether it failed, which here is the desired outcome.
expect_failure() {
    echo "${dim}regenerating contract…${off}"
    regenerate
    local out
    out="$(cd "$root/frontend" && npm run check --silent 2>&1)"
    if [[ -n "$out" ]]; then
        echo "${red}✗ tsc rejected the frontend — drift caught at compile time:${off}"
        echo "$out" | grep -E "error TS" | head -6 | sed 's/^/    /'
    else
        echo "${red}UNEXPECTED: tsc passed. The gate is not doing its job.${off}"
        return 1
    fi
    echo
}

echo
echo "${bold}Baseline${off}"
if [[ -n "$(cd "$root/frontend" && npm run check --silent 2>&1)" ]]; then
    echo "${red}The frontend does not compile before we even start. Fix that first.${off}"
    exit 1
fi
echo "${green}✓ frontend compiles against the current contract${off}"
echo

echo "${bold}Scenario 1 — a backend field is renamed${off}"
echo "${dim}  ReportIn.impression → ReportIn.conclusion${off}"
perl -0pi -e 's/    impression: str = Field\(min_length=1, description="What it means\."\)/    conclusion: str = Field(min_length=1, description="What it means.")/' "$models"
expect_failure

cp "$backup" "$models"

echo "${bold}Scenario 2 — a required field is added to the request body${off}"
echo "${dim}  ReportIn gains a required radiologist_id${off}"
perl -0pi -e 's/    critical: bool = False\n\n\nclass ReportDraft/    critical: bool = False\n    radiologist_id: str\n\n\nclass ReportDraft/' "$models"
expect_failure

echo "${bold}Both failures were compile errors, not runtime 422s.${off}"
echo "${dim}A backend PR that renames a field cannot merge without the frontend changing too.${off}"
