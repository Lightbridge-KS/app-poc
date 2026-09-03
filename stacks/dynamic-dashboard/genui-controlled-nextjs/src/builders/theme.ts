import type { Layout } from "plotly.js";

/** Colour-blind-safe categorical palette (Okabe–Ito), fixed — the model has no say in colours. */
export const PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#999999"];

export function baseLayout(title: string): Partial<Layout> {
  return {
    title: { text: title, font: { size: 14 }, x: 0.02 },
    margin: { l: 56, r: 16, t: 44, b: 48 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "ui-sans-serif, system-ui, sans-serif", size: 12 },
    legend: { orientation: "h", y: -0.22 },
    hovermode: "closest",
  };
}
