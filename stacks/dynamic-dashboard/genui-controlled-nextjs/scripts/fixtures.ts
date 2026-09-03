/**
 * Fixture generator for sibling stacks: read a JSON list of `{kind, ...PlotSpec}` and print
 * the exact outputs `execute` would return for each. The config-driven stack vendors the
 * result and asserts its own builders reproduce it — same contract, same numbers, no LLM.
 *
 *   node --import tsx scripts/fixtures.ts path/to/specs.json
 */
import { readFileSync } from "node:fs";
import { BarSpec, ScatterSpec } from "../src/catalog/schema";
import { buildBar, buildScatter } from "../src/catalog/tools";

const file = process.argv[2];
if (!file) {
  console.error("usage: fixtures.ts <specs.json>");
  process.exit(2);
}
const specs = JSON.parse(readFileSync(file, "utf8")) as ({ kind: "scatter" | "bar" } & Record<string, unknown>)[];

const outputs = specs.map(({ kind, ...spec }) =>
  kind === "scatter" ? buildScatter(ScatterSpec.parse(spec)) : buildBar(BarSpec.parse(spec)),
);
console.log(JSON.stringify(outputs, null, 2));
