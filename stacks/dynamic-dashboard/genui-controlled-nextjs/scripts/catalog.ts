/** Print the catalog contract exactly as the model receives it: tool name, description, JSON Schema. */
import { z } from "zod";
import { tools } from "../src/catalog/tools";
import { BarSpec, ScatterSpec } from "../src/catalog/schema";

const schemas = { scatter_plot: ScatterSpec, bar_plot: BarSpec } as const;

const out = Object.entries(tools).map(([name, t]) => ({
  name,
  description: t.description,
  inputSchema: z.toJSONSchema(schemas[name as keyof typeof schemas], { target: "draft-7" }),
}));

console.log(JSON.stringify(out, null, 2));
