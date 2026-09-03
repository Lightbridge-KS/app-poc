/**
 * The catalog as the model sees it: two tools, one per builder.
 *
 * `execute` runs clean → transform on the server and returns the projected rows to the
 * card. `toModelOutput` hands the model only a one-line summary — the model never sees
 * data, only the schema. That asymmetry is the Controlled tier in one place.
 */
import { tool, type InferUITools, type ToolSet, type UIDataTypes, type UIMessage } from "ai";
import { DATASETS, loadClean, type Row } from "./datasets";
import { BarSpec, ScatterSpec } from "./schema";
import { applyFilters, dropIncomplete, groupAggregate } from "./transform";
import type { BarOutput, ScatterOutput } from "./output";

export function buildScatter(spec: ScatterSpec): ScatterOutput {
  const all = loadClean(spec.dataset);
  const filtered = applyFilters(all, spec.filter);
  const used = [spec.x, spec.y, ...(spec.color ? [spec.color] : [])];
  const { rows, dropped } = dropIncomplete(filtered, used);
  const labelCol = DATASETS[spec.dataset].rowLabel;
  const points = rows.map((r) => ({
    x: r[spec.x] as number,
    y: r[spec.y] as number,
    color: spec.color ? String(r[spec.color]) : null,
    label: labelCol ? String(r[labelCol]) : null,
  }));
  const meta = { n_used: rows.length, n_total: all.length, n_filtered: filtered.length, n_dropped: dropped };
  return {
    kind: "scatter",
    spec,
    points,
    meta,
    summary: `Rendered scatter of ${spec.dataset}: ${spec.x} × ${spec.y}${spec.color ? ` by ${spec.color}` : ""}, ${rows.length}/${all.length} rows.`,
  };
}

export function buildBar(spec: BarSpec): BarOutput {
  const all = loadClean(spec.dataset);
  const filtered = applyFilters(all, spec.filter);
  const used = [spec.by, ...(spec.color ? [spec.color] : []), ...(spec.measure.op === "count" ? [] : [spec.measure.column])];
  const { rows, dropped } = dropIncomplete(filtered, used);
  const bars = groupAggregate(rows, spec.by, spec.measure, spec.color);
  const meta = { n_used: rows.length, n_total: all.length, n_filtered: filtered.length, n_dropped: dropped };
  const what = spec.measure.op === "count" ? "count" : `${spec.measure.op} ${spec.measure.column}`;
  return {
    kind: "bar",
    spec,
    bars,
    meta,
    summary: `Rendered bar of ${spec.dataset}: ${what} by ${spec.by}${spec.color ? ` split by ${spec.color}` : ""}, ${bars.length} bars from ${rows.length}/${all.length} rows.`,
  };
}

export const tools = {
  scatter_plot: tool({
    description:
      "Add a scatter plot card to the dashboard: one numeric column against another, optionally coloured by a category.",
    inputSchema: ScatterSpec,
    execute: async (spec) => buildScatter(spec),
    toModelOutput: ({ output }) => ({ type: "text", value: output.summary }),
  }),
  bar_plot: tool({
    description:
      "Add a bar plot card to the dashboard: one bar per category level, height = row count or mean/median of a numeric column.",
    inputSchema: BarSpec,
    execute: async (spec) => buildBar(spec),
    toModelOutput: ({ output }) => ({ type: "text", value: output.summary }),
  }),
} satisfies ToolSet;

export type ChatTools = InferUITools<typeof tools>;
export type ChatMessage = UIMessage<never, UIDataTypes, ChatTools>;

export type { Row };
export type { PlotOutput } from "./output";
