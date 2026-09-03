/**
 * The PlotSpec — the catalog contract.
 *
 * These Zod schemas are the tool `inputSchema`s the model fills. Everything the model is
 * allowed to decide is a field here; everything it is not allowed to decide is absent.
 * The same schemas will be what a YAML file satisfies in the config-driven sibling.
 *
 * No free-text field: a first `just prove` run with an optional `title` showed it was the
 * only prop that ever drifted (see README → Evidence). Titles are derived from the spec.
 */
import { z } from "zod";
import { DATASETS } from "./datasets";

const FILTER_OPS = ["==", "!=", ">", ">=", "<", "<=", "in"] as const;
export type FilterOp = (typeof FILTER_OPS)[number];

type Cols = readonly [string, ...string[]];

function filterFor<const C extends Cols>(cols: C) {
  return z
    .object({
      column: z.enum(cols),
      op: z.enum(FILTER_OPS).describe("'in' takes a string[] value; the rest take a scalar"),
      value: z.union([z.number(), z.string(), z.array(z.string()).min(1).max(10)]),
    })
    .describe("One row filter; filters are ANDed");
}

function specsFor<const D extends string, const N extends Cols, const C extends Cols>(
  dataset: D,
  def: { label: string; numeric: N; categorical: C },
) {
  const all = [...def.numeric, ...def.categorical] as unknown as readonly [N[number] | C[number], ...(N[number] | C[number])[]];
  const filter = z.array(filterFor(all)).max(3).optional();

  const scatter = z.object({
    dataset: z.literal(dataset).describe(def.label),
    x: z.enum(def.numeric),
    y: z.enum(def.numeric),
    color: z.enum(def.categorical).optional().describe("Colour points by this category"),
    filter,
  });

  const bar = z.object({
    dataset: z.literal(dataset).describe(def.label),
    by: z.enum(def.categorical).describe("One bar per level of this column"),
    measure: z
      .discriminatedUnion("op", [
        z.object({ op: z.literal("count") }),
        z.object({ op: z.enum(["mean", "median"]), column: z.enum(def.numeric) }),
      ])
      .describe("Bar height: row count, or mean/median of a numeric column"),
    color: z.enum(def.categorical).optional().describe("Split each bar by this category (grouped bars)"),
    filter,
  });

  return { scatter, bar };
}

const penguins = specsFor("penguins", DATASETS.penguins);
const mtcars = specsFor("mtcars", DATASETS.mtcars);

export const ScatterSpec = z.discriminatedUnion("dataset", [penguins.scatter, mtcars.scatter]);
export const BarSpec = z.discriminatedUnion("dataset", [penguins.bar, mtcars.bar]);

export type ScatterSpec = z.infer<typeof ScatterSpec>;
export type BarSpec = z.infer<typeof BarSpec>;
export type Filter = { column: string; op: FilterOp; value: number | string | string[] };
export type PlotSpec = ScatterSpec | BarSpec;
