"""The whitelisted transform ops — the only data manipulation a config may request.

Pure polars, every verb returns a new frame. Semantics match `transform.ts` in the
nextjs stack exactly, because the equivalence test says they must.
"""

from __future__ import annotations

from typing import Any

import polars as pl

Filter = dict[str, Any]  # {column, op, value} — already validated by the schema


def _is_number(v: Any) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _filter_expr(f: Filter) -> pl.Expr:
    col, op, value = f["column"], f["op"], f["value"]
    if op == "in":
        values = value if isinstance(value, list) else [str(value)]
        return pl.col(col).cast(pl.String).is_in(values)
    if isinstance(value, list):
        return pl.lit(False)
    # Compare numerically when both sides parse as numbers (mtcars `cyl` is a String column
    # holding "4"/"6"/"8"); otherwise as strings. Nulls compare to null → row dropped.
    if _is_number(value):
        lhs, rhs = pl.col(col).cast(pl.Float64, strict=False), float(value)
        numeric = pl.col(col).cast(pl.Float64, strict=False).is_not_null()
        text = pl.col(col).cast(pl.String)
        expr_num = _cmp(lhs, rhs, op)
        expr_str = _cmp(text, str(value), op)
        return pl.when(numeric).then(expr_num).otherwise(expr_str)
    return _cmp(pl.col(col).cast(pl.String), str(value), op)


def _cmp(lhs: pl.Expr, rhs: Any, op: str) -> pl.Expr:
    match op:
        case "==":
            return lhs == rhs
        case "!=":
            return lhs != rhs
        case ">":
            return lhs > rhs
        case ">=":
            return lhs >= rhs
        case "<":
            return lhs < rhs
        case "<=":
            return lhs <= rhs
    raise ValueError(op)


def apply_filters(df: pl.DataFrame, filters: list[Filter] | None) -> pl.DataFrame:
    if not filters:
        return df
    expr = pl.all_horizontal([_filter_expr(f).fill_null(False) for f in filters])
    return df.filter(expr)


def drop_incomplete(df: pl.DataFrame, cols: list[str]) -> tuple[pl.DataFrame, int]:
    kept = df.drop_nulls(subset=cols)
    return kept, df.height - kept.height


def group_aggregate(df: pl.DataFrame, by: str, measure: dict[str, Any], group: str | None) -> list[dict[str, Any]]:
    """group_by + aggregate, optionally split by a second category. Numeric-aware category order."""
    keys = [by] + ([group] if group else [])
    if measure["op"] == "count":
        value_expr = pl.len().cast(pl.Float64)
    else:
        col = pl.col(measure["column"])
        value_expr = col.mean() if measure["op"] == "mean" else col.median()
    agg_df = df.group_by(keys, maintain_order=True).agg(pl.len().alias("n"), value_expr.alias("value"))
    rows = [
        {
            "category": str(r[by]),
            "group": str(r[group]) if group else None,
            "n": int(r["n"]),
            "value": _tidy(r["value"]),
        }
        for r in agg_df.iter_rows(named=True)
    ]
    return sorted(rows, key=lambda r: (_sort_key(r["category"]), _sort_key(r["group"] or "")))


def _sort_key(s: str) -> tuple[int, float, str]:
    """Numbers before strings, numbers by value, strings lexically — same order as `cmp` in transform.ts."""
    return (0, float(s), "") if _is_number(s) else (1, 0.0, s)


def _tidy(v: Any) -> float | int:
    """Integral floats print as ints, as they do from JavaScript's Number."""
    if v is None:
        return float("nan")
    return int(v) if float(v).is_integer() else float(v)
