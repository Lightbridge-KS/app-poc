"use client";

/**
 * The prebuilt component the model "selects". It receives a fully computed PlotOutput;
 * nothing here is model-authored except the values inside `spec`.
 */
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { barFigure } from "@/builders/bar";
import { scatterFigure } from "@/builders/scatter";
import { describe } from "@/catalog/output";
import type { Card } from "./CardGrid";

const Plot = dynamic(
  async () => {
    const [{ default: factory }, { default: Plotly }] = await Promise.all([
      import("react-plotly.js/factory"),
      import("plotly.js-dist-min"),
    ]);
    return factory(Plotly);
  },
  { ssr: false, loading: () => <div className="h-[320px] animate-pulse rounded bg-zinc-100" /> },
);

export function PlotCard({ card, onDismiss }: { card: Card; onDismiss: () => void }) {
  const [flipped, setFlipped] = useState(false);
  const figure = useMemo(() => {
    if (card.state !== "ready") return null;
    return card.output.kind === "scatter" ? scatterFigure(card.output) : barFigure(card.output);
  }, [card]);

  return (
    <section className="min-w-0 overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm" data-testid="plot-card" data-state={card.state}>
      <header className="flex items-center gap-2 border-b border-zinc-100 px-3 py-2">
        <p className="flex-1 truncate font-mono text-[11px] text-zinc-600">
          {card.state === "ready" ? describe(card.output) : card.state === "building" ? "building…" : `✗ ${card.error}`}
        </p>
        {card.state === "ready" && (
          <button className="text-[11px] text-zinc-500 hover:text-zinc-900" onClick={() => setFlipped((f) => !f)}>
            {flipped ? "plot" : "spec"}
          </button>
        )}
        <button className="text-[11px] text-zinc-500 hover:text-red-600" onClick={onDismiss} aria-label="Remove card">
          ✕
        </button>
      </header>

      {card.state === "ready" && figure && !flipped && (
        <Plot data={figure.data} layout={figure.layout} config={{ displayModeBar: false, responsive: true }} style={{ width: "100%", height: 320 }} useResizeHandler />
      )}
      {card.state === "ready" && flipped && (
        <pre className="max-h-[320px] overflow-auto p-3 font-mono text-[11px] leading-snug text-zinc-700" data-testid="plot-spec">
          {JSON.stringify(card.output.spec, null, 2)}
        </pre>
      )}
      {card.state === "building" && <div className="h-[320px] animate-pulse rounded-b bg-zinc-50" />}
      {card.state === "error" && <div className="p-3 text-sm text-red-600">{card.error}</div>}
    </section>
  );
}
