"""Contract vocabulary: the enums a PlotSpec JSON Schema allows, per dataset, shape-agnostic.

Zod emits `oneOf` branches; Pydantic emits `$defs` plus a discriminator. Both say the same
thing about *which words are legal*, and that is what this extracts and compares.
"""

from __future__ import annotations

from typing import Any

Vocab = dict[str, dict[str, list[str]]]  # {dataset: {field: sorted enum}}
FIELDS = ("x", "y", "color", "by", "column", "op")


def _resolve(node: Any, root: dict[str, Any]) -> Any:
    while isinstance(node, dict) and "$ref" in node:
        node = root
        for part in node and _ref_parts(node):
            node = node[part]
    return node


def _ref_parts(node: dict[str, Any]) -> list[str]:
    return node["$ref"].split("/")[1:]


def _deref(node: Any, root: dict[str, Any]) -> Any:
    while isinstance(node, dict) and "$ref" in node:
        target = root
        for part in node["$ref"].split("/")[1:]:
            target = target[part]
        node = target
    return node


def _enum_of(node: Any, root: dict[str, Any]) -> list[str] | None:
    node = _deref(node, root)
    if not isinstance(node, dict):
        return None
    if "enum" in node:
        return sorted(str(v) for v in node["enum"])
    if "const" in node:
        return [str(node["const"])]
    for key in ("anyOf", "oneOf"):
        if key in node:
            vals: set[str] = set()
            for alt in node[key]:
                e = _enum_of(alt, root)
                if e:
                    vals.update(e)
            return sorted(vals) if vals else None
    return None


def vocabulary(schema: dict[str, Any]) -> Vocab:
    """Every object schema under a `dataset` const → the enums of its column-valued fields."""
    out: Vocab = {}

    def walk(node: Any, dataset: str | None) -> None:
        node = _deref(node, schema)
        if isinstance(node, list):
            for x in node:
                walk(x, dataset)
            return
        if not isinstance(node, dict):
            return
        props = node.get("properties")
        if isinstance(props, dict):
            ds = _enum_of(props["dataset"], schema) if "dataset" in props else None
            if ds and len(ds) == 1:
                dataset = ds[0]
            if dataset:
                bucket = out.setdefault(dataset, {})
                for f in FIELDS:
                    if f in props:
                        e = _enum_of(props[f], schema)
                        if e:
                            bucket[f] = sorted(set(bucket.get(f, [])) | set(e))
            for v in props.values():
                walk(v, dataset)
        for key in ("anyOf", "oneOf", "items"):
            if key in node:
                walk(node[key], dataset)

    walk(schema, None)
    return out
