/**
 * Deterministic checks on the clean → transform → build path. No LLM, no server.
 * Each expected value is a dataset fact known independently (R's `mtcars`, the
 * dash-docker README's 344 / 342 counts), so a failure means the pipeline is wrong.
 */
import { DATASETS, loadClean } from "../src/catalog/datasets";
import { buildBar, buildScatter } from "../src/catalog/tools";

let failures = 0;
function check(name: string, got: unknown, want: unknown) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  console.log(`${ok ? "✓" : "✗"} ${name}: ${JSON.stringify(got)}${ok ? "" : `  (want ${JSON.stringify(want)})`}`);
  if (!ok) failures++;
}
const r2 = (x: number) => Math.round(x * 100) / 100;

check("penguins rows", loadClean("penguins").length, 344);
check("mtcars rows", loadClean("mtcars").length, 32);
check("catalog columns", Object.fromEntries(Object.entries(DATASETS).map(([k, d]) => [k, d.numeric.length + d.categorical.length])), {
  penguins: 8,
  mtcars: 11,
});

const sc = buildScatter({ dataset: "penguins", x: "flipper_length_mm", y: "body_mass_g", color: "species" });
check("scatter flipper×mass by species: complete rows", sc.meta, { n_used: 342, n_total: 344, n_filtered: 344, n_dropped: 2 });

const sc2 = buildScatter({ dataset: "mtcars", x: "wt", y: "hp", filter: [{ column: "cyl", op: ">", value: 4 }] });
check("scatter mtcars hp×wt, cyl>4: rows", sc2.meta.n_used, 21);
check("scatter mtcars carries model label", sc2.points[0]?.label, "Mazda RX4");

const bar = buildBar({ dataset: "mtcars", by: "cyl", measure: { op: "mean", column: "mpg" } });
check(
  "bar mean mpg by cyl",
  bar.bars.map((b) => [b.category, r2(b.value), b.n]),
  [
    ["4", 26.66, 11],
    ["6", 19.74, 7],
    ["8", 15.1, 14],
  ],
);

const bar2 = buildBar({
  dataset: "penguins",
  by: "island",
  measure: { op: "count" },
  filter: [{ column: "species", op: "!=", value: "Gentoo" }],
});
check(
  "bar count by island, Gentoo excluded",
  bar2.bars.map((b) => [b.category, b.value]),
  [
    ["Biscoe", 44],
    ["Dream", 124],
    ["Torgersen", 52],
  ],
);

const bar3 = buildBar({ dataset: "penguins", by: "species", measure: { op: "median", column: "body_mass_g" }, color: "sex" });
check(
  "bar median mass by species split by sex (6 bars, sex-null rows dropped)",
  [bar3.bars.length, bar3.meta.n_used, bar3.bars.map((b) => `${b.category}/${b.group}=${b.value}`)],
  [6, 333, ["Adelie/female=3400", "Adelie/male=4000", "Chinstrap/female=3550", "Chinstrap/male=3950", "Gentoo/female=4700", "Gentoo/male=5500"]],
);

const inFilter = buildBar({
  dataset: "penguins",
  by: "species",
  measure: { op: "count" },
  filter: [{ column: "species", op: "in", value: ["Adelie", "Gentoo"] }],
});
check("filter op in", inFilter.bars.map((b) => [b.category, b.value]), [["Adelie", 152], ["Gentoo", 124]]);

console.log(failures === 0 ? "\nall checks passed" : `\n${failures} check(s) failed`);
process.exit(failures === 0 ? 0 : 1);
