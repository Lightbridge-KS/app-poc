"""Same PlotSpec, same numbers, no LLM: our builders must reproduce the nextjs stack's outputs.

`fixtures/nextjs-outputs.json` is generated in the sibling stack by
`just fixtures ../config-driven-shiny/fixtures/specs.json` — see README → Evidence.
"""

import json
import math
from pathlib import Path
from typing import Any

import pytest

from app.catalog.build import build_bar, build_scatter, describe

FIXTURES = Path(__file__).parent.parent / "fixtures"
SPECS = json.loads((FIXTURES / "specs.json").read_text())
EXPECTED = json.loads((FIXTURES / "nextjs-outputs.json").read_text())


def _norm(v: Any) -> Any:
    """Round floats so 26.663636363636364 and 26.66363636363636 compare equal; NaN == NaN."""
    if isinstance(v, float):
        return "nan" if math.isnan(v) else round(v, 9)
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_norm(x) for x in v]
    return v


@pytest.mark.parametrize("i", range(len(SPECS)), ids=[f"{s['kind']}-{s['dataset']}" for s in SPECS])
def test_output_equals_nextjs(i: int) -> None:
    spec = {k: v for k, v in SPECS[i].items() if k != "kind"}
    ours = build_scatter(spec) if SPECS[i]["kind"] == "scatter" else build_bar(spec)
    theirs = EXPECTED[i]
    assert _norm(ours) == _norm(theirs)


def test_caption_wording_matches_nextjs() -> None:
    captions = [
        describe(
            build_scatter({k: v for k, v in s.items() if k != "kind"})
            if s["kind"] == "scatter"
            else build_bar({k: v for k, v in s.items() if k != "kind"})
        )
        for s in SPECS
    ]
    assert captions[0] == "Scatter · penguins · flipper_length_mm × body_mass_g by species · 342/344 rows"
    assert captions[1] == "Bar · mtcars · mean(mpg) by cyl · 32/32 rows"
