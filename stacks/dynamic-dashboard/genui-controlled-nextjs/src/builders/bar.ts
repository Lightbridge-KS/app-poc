/** BarOutput → Plotly figure. Grouped bars when the spec has a `color` split. */
import type { Data, Layout } from "plotly.js";
import type { BarOutput } from "@/catalog/output";
import { PALETTE, baseLayout } from "./theme";

export function barFigure(out: BarOutput): { data: Data[]; layout: Partial<Layout> } {
  const { spec, bars } = out;
  const measureLabel = spec.measure.op === "count" ? "count" : `${spec.measure.op}(${spec.measure.column})`;
  const groups = new Map<string, typeof bars>();
  for (const b of bars) {
    const k = b.group ?? "all";
    const g = groups.get(k) ?? [];
    g.push(b);
    groups.set(k, g);
  }
  const data: Data[] = [...groups.entries()].map(([name, rows], i) => ({
    type: "bar",
    name,
    x: rows.map((b) => b.category),
    y: rows.map((b) => b.value),
    customdata: rows.map((b) => b.n),
    hovertemplate: `${spec.by}=%{x}<br>${measureLabel}=%{y:.2f}<br>n=%{customdata}<extra>${name}</extra>`,
    marker: { color: PALETTE[i % PALETTE.length] },
  }));
  const layout: Partial<Layout> = {
    ...baseLayout(`${measureLabel} by ${spec.by}`),
    barmode: "group",
    xaxis: { title: { text: spec.by }, type: "category" },
    yaxis: { title: { text: measureLabel }, zeroline: true },
    showlegend: spec.color !== undefined,
  };
  return { data, layout };
}
