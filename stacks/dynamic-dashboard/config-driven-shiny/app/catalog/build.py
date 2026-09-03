"""Spec → output: the same dict `execute` returns in the nextjs stack, key for key.

`build(card)` is what the dashboard calls; `build_scatter`/`build_bar` take a plain
PlotSpec dict so the equivalence test can feed them the vendored specs directly.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from .datasets import DATASETS, load_clean
from .transform import apply_filters, drop_incomplete, group_aggregate

Output = dict[str, Any]


def _num(v: float) -> float | int:
    return int(v) if float(v).is_integer() else float(v)


def build_scatter(spec: dict[str, Any]) -> Output:
    d = DATASETS[spec["dataset"]]
    all_df = load_clean(spec["dataset"])
    filtered_df = apply_filters(all_df, spec.get("filter"))
    color = spec.get("color")
    used = [spec["x"], spec["y"]] + ([color] if color else [])
    rows_df, dropped = drop_incomplete(filtered_df, used)
    points = [
        {
            "x": _num(r[spec["x"]]),
            "y": _num(r[spec["y"]]),
            "color": str(r[color]) if color else None,
            "label": str(r[d.row_label]) if d.row_label else None,
        }
        for r in rows_df.iter_rows(named=True)
    ]
    meta = {"n_used": rows_df.height, "n_total": all_df.height, "n_filtered": filtered_df.height, "n_dropped": dropped}
    by = f" by {color}" if color else ""
    return {
        "kind": "scatter",
        "spec": spec,
        "points": points,
        "meta": meta,
        "summary": (
            f"Rendered scatter of {spec['dataset']}: {spec['x']} × {spec['y']}{by}, "
            f"{rows_df.height}/{all_df.height} rows."
        ),
    }


def build_bar(spec: dict[str, Any]) -> Output:
    all_df = load_clean(spec["dataset"])
    filtered_df = apply_filters(all_df, spec.get("filter"))
    color = spec.get("color")
    measure = spec["measure"]
    used = [spec["by"]] + ([color] if color else []) + ([] if measure["op"] == "count" else [measure["column"]])
    rows_df, dropped = drop_incomplete(filtered_df, used)
    bars = group_aggregate(rows_df, spec["by"], measure, color)
    meta = {"n_used": rows_df.height, "n_total": all_df.height, "n_filtered": filtered_df.height, "n_dropped": dropped}
    what = "count" if measure["op"] == "count" else f"{measure['op']} {measure['column']}"
    split = f" split by {color}" if color else ""
    return {
        "kind": "bar",
        "spec": spec,
        "bars": bars,
        "meta": meta,
        "summary": (
            f"Rendered bar of {spec['dataset']}: {what} by {spec['by']}{split}, "
            f"{len(bars)} bars from {rows_df.height}/{all_df.height} rows."
        ),
    }


def build(card: BaseModel) -> Output:
    from .schema import spec_of  # local import: schema imports datasets, not build

    spec = spec_of(card)
    return build_scatter(spec) if card.kind == "scatter" else build_bar(spec)  # type: ignore[attr-defined]


def describe(output: Output) -> str:
    """Deterministic caption — identical wording to `describe()` in output.ts."""
    spec, meta = output["spec"], output["meta"]
    n = len(spec.get("filter") or [])
    filt = f" · {n} filter{'s' if n > 1 else ''}" if n else ""
    rows = f" · {meta['n_used']}/{meta['n_total']} rows"
    if output["kind"] == "scatter":
        by = f" by {spec['color']}" if spec.get("color") else ""
        return f"Scatter · {spec['dataset']} · {spec['x']} × {spec['y']}{by}{filt}{rows}"
    m = spec["measure"]
    what = "count" if m["op"] == "count" else f"{m['op']}({m['column']})"
    split = f" split by {spec['color']}" if spec.get("color") else ""
    return f"Bar · {spec['dataset']} · {what} by {spec['by']}{split}{filt}{rows}"
