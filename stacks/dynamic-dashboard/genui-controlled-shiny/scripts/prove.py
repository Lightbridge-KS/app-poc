"""Evidence for the README. Costs tokens: every row is a real model call.

  consistency   — each intent prompt N times; which tool, which props (validated PlotSpec;
                  "raw nulls" counts runs where the model spelled out null for optional fields)
  refusal       — out-of-catalog prompts must produce text and zero tool calls
  cross-stack   — this stack's majority spec per intent vs the nextjs stack's Run-2 spec

Same prompts as genui-controlled-nextjs/scripts/prompts.json (vendored in fixtures/).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agent import MODEL, turn  # noqa: E402

FIX = ROOT / "fixtures"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def stable(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"))


def main() -> int:
    prompts = json.loads((FIX / "prompts.json").read_text())
    run2 = json.loads((FIX / "nextjs-run2-specs.json").read_text())
    failures = 0

    print(f"# prove — {N} runs per intent, model {MODEL}, chatlas, {__import__('datetime').date.today()}\n")
    print("## Consistency\n")
    print("| intent | tool (n/N) | distinct specs | raw nulls | median ms | spec (validated) |")
    print("|---|---|---|---|---|---|")
    majority: dict[str, str] = {}
    for it in prompts["intents"]:
        turns = [turn(it["prompt"]) for _ in range(N)]
        names = Counter("+".join(n for n, _ in t.tools) or "(none)" for t in turns)
        specs = Counter(stable([a for _, a in t.specs]) for t in turns)
        nulls = sum(t.raw_nulls for t in turns)
        top_name, top_n = names.most_common(1)[0]
        top_spec = specs.most_common(1)[0][0]
        majority[it["id"]] = top_spec
        if len(specs) > 1:
            failures += 1
        ms = sorted(t.ms for t in turns)[N // 2]
        print(f"| {it['id']} | {top_name} ({top_n}/{N}) | {len(specs)} | {nulls}/{N} | {ms} | `{top_spec}` |")
        if len(specs) > 1:
            for s, c in specs.most_common():
                print(f"|   ↳ variant ×{c} | | | | | `{s}` |")
    print()

    print("## Refusal\n")
    print("| prompt | tool calls | reply |")
    print("|---|---|---|")
    leaks = 0
    for r in prompts["refusals"]:
        t = turn(r["prompt"])
        leaks += len(t.tools) > 0
        print(f"| {r['prompt']} | {len(t.tools)} | {t.text.replace('|', '\\|')[:220]} |")
    print(f"\nOut-of-catalog prompts that produced a plot: {leaks}/{len(prompts['refusals'])}\n")

    print("## Cross-stack — majority spec here vs the nextjs stack's Run-2 spec\n")
    print("| intent | equal | nextjs Run-2 spec |")
    print("|---|---|---|")
    mismatches = 0
    for it, expected in zip(prompts["intents"], run2, strict=True):
        exp = stable([{k: v for k, v in expected.items() if k != "kind"}])
        equal = majority[it["id"]] == exp
        mismatches += not equal
        print(f"| {it['id']} | {'✓' if equal else '✗'} | `{exp}` |")
    print(f"\nIntents whose majority spec differs from the nextjs stack: {mismatches}/{len(run2)}")
    return 1 if (failures or leaks or mismatches) else 0


if __name__ == "__main__":
    sys.exit(main())
