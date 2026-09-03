/** ScatterOutput → Plotly figure. Pure; the card just renders what this returns. */
import type { Data, Layout } from "plotly.js";
import type { ScatterOutput } from "@/catalog/output";
import { PALETTE, baseLayout } from "./theme";

export function scatterFigure(out: ScatterOutput): { data: Data[]; layout: Partial<Layout> } {
  const { spec, points } = out;
  const groups = new Map<string, typeof points>();
  for (const p of points) {
    const k = p.color ?? "all";
    const g = groups.get(k) ?? [];
    g.push(p);
    groups.set(k, g);
  }
  const data: Data[] = [...groups.entries()].map(([name, pts], i) => ({
    type: "scatter",
    mode: "markers",
    name,
    x: pts.map((p) => p.x),
    y: pts.map((p) => p.y),
    text: pts.map((p) => p.label ?? ""),
    hovertemplate: `${spec.x}=%{x}<br>${spec.y}=%{y}${pts[0]?.label !== null ? "<br>%{text}" : ""}<extra>${name}</extra>`,
    marker: { color: PALETTE[i % PALETTE.length], size: 8, opacity: 0.8 },
  }));
  const layout: Partial<Layout> = {
    ...baseLayout(`${spec.y} vs ${spec.x}`),
    xaxis: { title: { text: spec.x }, zeroline: false },
    yaxis: { title: { text: spec.y }, zeroline: false },
    showlegend: spec.color !== undefined,
  };
  return { data, layout };
}
