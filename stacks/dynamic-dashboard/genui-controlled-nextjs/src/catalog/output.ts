/**
 * What a builder returns to the card — the client-safe half of the catalog.
 * No I/O here: this file is imported by client components; `tools.ts` (server) is not.
 */
import type { BarSpec, ScatterSpec } from "./schema";
import type { AggRow } from "./transform";

export type Meta = { n_used: number; n_total: number; n_filtered: number; n_dropped: number };

export type ScatterPoint = { x: number; y: number; color: string | null; label: string | null };

export type ScatterOutput = { kind: "scatter"; spec: ScatterSpec; points: ScatterPoint[]; meta: Meta; summary: string };
export type BarOutput = { kind: "bar"; spec: BarSpec; bars: AggRow[]; meta: Meta; summary: string };
export type PlotOutput = ScatterOutput | BarOutput;

/** Deterministic caption — the client writes it, not the model. */
export function describe(output: PlotOutput): string {
  const { spec, meta } = output;
  const filt = spec.filter?.length ? ` · ${spec.filter.length} filter${spec.filter.length > 1 ? "s" : ""}` : "";
  const rows = ` · ${meta.n_used}/${meta.n_total} rows`;
  if (output.kind === "scatter") {
    const s = output.spec;
    return `Scatter · ${s.dataset} · ${s.x} × ${s.y}${s.color ? ` by ${s.color}` : ""}${filt}${rows}`;
  }
  const s = output.spec;
  const what = s.measure.op === "count" ? "count" : `${s.measure.op}(${s.measure.column})`;
  return `Bar · ${s.dataset} · ${what} by ${s.by}${s.color ? ` split by ${s.color}` : ""}${filt}${rows}`;
}
