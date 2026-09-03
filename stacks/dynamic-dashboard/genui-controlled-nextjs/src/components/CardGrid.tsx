"use client";

import type { PlotOutput } from "@/catalog/output";
import { PlotCard } from "./PlotCard";

export type Card =
  | { id: string; state: "ready"; output: PlotOutput }
  | { id: string; state: "building" }
  | { id: string; state: "error"; error: string };

const SUGGESTIONS = [
  "flipper length vs body mass, coloured by species",
  "average mpg by number of cylinders",
  "how many penguins per island, Gentoo excluded",
  "horsepower vs weight for cars with more than 4 cylinders",
];

export function CardGrid({
  cards,
  onDismiss,
  onSuggest,
}: {
  cards: Card[];
  onDismiss: (id: string) => void;
  onSuggest: (text: string) => void;
}) {
  if (cards.length === 0) {
    return (
      <main className="flex items-center justify-center p-8">
        <div className="max-w-md text-center">
          <p className="text-sm text-zinc-500">No cards yet. Try one of these:</p>
          <ul className="mt-3 space-y-2">
            {SUGGESTIONS.map((s) => (
              <li key={s}>
                <button
                  className="w-full rounded-md border border-zinc-200 bg-white px-3 py-2 text-left text-sm hover:border-zinc-400"
                  onClick={() => onSuggest(s)}
                >
                  {s}
                </button>
              </li>
            ))}
          </ul>
        </div>
      </main>
    );
  }
  return (
    <main className="overflow-y-auto p-4">
      <div className="grid grid-cols-1 gap-4 2xl:grid-cols-2" data-testid="card-grid">
        {cards.map((c) => (
          <PlotCard key={c.id} card={c} onDismiss={() => onDismiss(c.id)} />
        ))}
      </div>
    </main>
  );
}
