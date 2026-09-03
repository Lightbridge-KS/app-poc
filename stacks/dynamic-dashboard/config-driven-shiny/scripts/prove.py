"""Evidence for the README, all hermetic (no server, no model). Prints markdown.

equivalence  — the four Run-2 specs → our outputs vs the nextjs stack's vendored outputs
contract     — Pydantic vs Zod vocabulary, per dataset
errors       — what each deliberately bad card in fixtures/bad-cards.yaml teaches
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.catalog.build import build_bar, build_scatter, describe  # noqa: E402
from app.catalog.config import load_dashboard  # noqa: E402
from app.catalog.contract import vocabulary  # noqa: E402
from app.catalog.schema import BarSpecAdapter, ScatterSpecAdapter  # noqa: E402

FIX = ROOT / "fixtures"


def norm(v: Any) -> Any:
    if isinstance(v, float):
        return "nan" if math.isnan(v) else round(v, 9)
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    if isinstance(v, list):
        return [norm(x) for x in v]
    return v


def main() -> int:
    failures = 0
    print("## Equivalence — same PlotSpec, our polars build vs the nextjs build\n")
    print("| spec | caption (ours) | items | meta | equal to nextjs |")
    print("|---|---|---|---|---|")
    specs = json.loads((FIX / "specs.json").read_text())
    expected = json.loads((FIX / "nextjs-outputs.json").read_text())
    for s, exp in zip(specs, expected, strict=True):
        spec = {k: v for k, v in s.items() if k != "kind"}
        out = build_scatter(spec) if s["kind"] == "scatter" else build_bar(spec)
        equal = norm(out) == norm(exp)
        failures += not equal
        items = len(out.get("points", out.get("bars", [])))
        spec_s = json.dumps(spec, separators=(",", ":"))
        print(f"| `{spec_s}` | {describe(out)} | {items} | `{json.dumps(out['meta'])}` | {'✓' if equal else '✗'} |")

    print("\n## Contract — vocabulary of the Pydantic PlotSpec vs the Zod PlotSpec\n")
    nextjs = {t["name"]: t["inputSchema"] for t in json.loads((FIX / "nextjs-catalog.json").read_text())}
    for name, adapter in (("scatter_plot", ScatterSpecAdapter), ("bar_plot", BarSpecAdapter)):
        ours, theirs = vocabulary(adapter.json_schema()), vocabulary(nextjs[name])
        equal = ours == theirs
        failures += not equal
        print(f"{name}: {'✓ identical' if equal else '✗ differ'}")
        for ds, fields in sorted(ours.items()):
            for f, vals in sorted(fields.items()):
                print(f"  {ds}.{f}: {', '.join(vals)}")
        if not equal:
            print(f"  theirs: {json.dumps(theirs)}")
        print()

    print("## Errors teach — fixtures/bad-cards.yaml\n")
    dash = load_dashboard(FIX / "bad-cards.yaml")
    print(f"{len(dash.cards)} cards: {len(dash.errors)} rejected, {len(dash.ok)} rendered\n")
    for e in dash.errors:
        print(f"card {e.index} `{json.dumps(e.raw, separators=(',', ':'))[:80]}…`")
        for m in e.messages:
            print(f"  → {m}")
    print()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
