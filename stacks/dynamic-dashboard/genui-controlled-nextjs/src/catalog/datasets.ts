/**
 * The two datasets the catalog knows, and the fixed "clean" step for each.
 *
 * This is the RawData → CleanedData arrow of the concept sketch: deterministic, no LLM
 * anywhere. The column lists below are the *only* columns the model can name — they are
 * lifted into the Zod enums in `schema.ts`, so an unknown column is a schema error, never
 * a runtime guess.
 */
import { readFileSync } from "node:fs";
import path from "node:path";

export const DATASETS = {
  penguins: {
    file: "penguins.csv",
    label: "Palmer Penguins — 344 penguins, 3 species, 3 islands (2007–2009)",
    numeric: [
      "bill_length_mm",
      "bill_depth_mm",
      "flipper_length_mm",
      "body_mass_g",
      "year",
    ],
    categorical: ["species", "island", "sex"],
    rowLabel: null,
  },
  mtcars: {
    file: "mtcars.csv",
    label: "Motor Trend cars (1974) — 32 cars, fuel economy and design",
    numeric: ["mpg", "disp", "hp", "drat", "wt", "qsec"],
    categorical: ["cyl", "vs", "am", "gear", "carb"],
    rowLabel: "model",
  },
} as const;

export type DatasetId = keyof typeof DATASETS;
export type NumericCol<D extends DatasetId> = (typeof DATASETS)[D]["numeric"][number];
export type CategoricalCol<D extends DatasetId> = (typeof DATASETS)[D]["categorical"][number];

/** A cleaned row: numeric columns are number|null, categorical columns string|null. */
export type Row = Record<string, number | string | null>;

const cache = new Map<DatasetId, Row[]>();

/** CleanedData for a dataset — parsed, typed, NA → null. Cached per process. */
export function loadClean(dataset: DatasetId): Row[] {
  const hit = cache.get(dataset);
  if (hit) return hit;
  const def = DATASETS[dataset];
  const text = readFileSync(path.join(process.cwd(), "data", def.file), "utf8");
  const rows = parseCsv(text).map((raw) => clean(raw, dataset));
  cache.set(dataset, rows);
  return rows;
}

function clean(raw: Record<string, string>, dataset: DatasetId): Row {
  const def = DATASETS[dataset];
  const out: Row = {};
  for (const col of def.numeric) out[col] = toNumber(raw[col]);
  for (const col of def.categorical) out[col] = toCategory(raw[col]);
  if (def.rowLabel) out[def.rowLabel] = toCategory(raw[def.rowLabel]);
  return out;
}

function toNumber(v: string | undefined): number | null {
  if (v === undefined || v === "" || v === "NA") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function toCategory(v: string | undefined): string | null {
  if (v === undefined || v === "" || v === "NA") return null;
  return v;
}

/** Minimal RFC-4180 parser: quoted fields, embedded commas, no embedded newlines. */
export function parseCsv(text: string): Record<string, string>[] {
  const lines = text.split(/\r?\n/).filter((l) => l.length > 0);
  const header = splitLine(lines[0] ?? "");
  return lines.slice(1).map((line) => {
    const cells = splitLine(line);
    const rec: Record<string, string> = {};
    header.forEach((h, i) => (rec[h] = cells[i] ?? ""));
    return rec;
  });
}

function splitLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"' && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else if (ch === '"') quoted = false;
      else cur += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") {
      out.push(cur);
      cur = "";
    } else cur += ch;
  }
  out.push(cur);
  return out;
}
