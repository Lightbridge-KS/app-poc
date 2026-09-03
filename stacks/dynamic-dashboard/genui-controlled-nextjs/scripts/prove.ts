/**
 * Evidence for the README, produced against the *running* app (`just dev` first).
 *
 *   consistency  — each intent prompt N times through /api/chat; which tool, which props.
 *   refusal      — out-of-catalog prompts must produce text and zero tool calls.
 *
 * Goes through the real HTTP route via DefaultChatTransport, so this measures the app,
 * not a direct model call. Prints markdown; paste it into README → Evidence.
 */
import { DefaultChatTransport, readUIMessageStream, type UIMessage } from "ai";
import { readFileSync } from "node:fs";
import path from "node:path";

const API = process.env.PROVE_API ?? "http://localhost:3000/api/chat";
const N = Number(process.env.PROVE_N ?? 5);
const prompts = JSON.parse(readFileSync(path.join(import.meta.dirname, "prompts.json"), "utf8")) as {
  intents: { id: string; prompt: string }[];
  refusals: { id: string; prompt: string }[];
};

type ToolPart = { type: string; state: string; input?: unknown; errorText?: string };
type Turn = { tools: { name: string; input: unknown }[]; text: string; ms: number };

async function turn(prompt: string): Promise<Turn> {
  const transport = new DefaultChatTransport<UIMessage>({ api: API });
  const t0 = performance.now();
  const stream = await transport.sendMessages({
    chatId: `prove-${Date.now()}`,
    messageId: undefined,
    trigger: "submit-message",
    messages: [{ id: "u1", role: "user", parts: [{ type: "text", text: prompt }] }],
    abortSignal: undefined,
  });
  let last: UIMessage | undefined;
  for await (const m of readUIMessageStream({ stream })) last = m;
  const ms = Math.round(performance.now() - t0);
  const parts = (last?.parts ?? []) as ToolPart[];
  const tools = parts
    .filter((p) => p.type.startsWith("tool-"))
    .map((p) => ({ name: p.type.slice(5), input: p.input, state: p.state, errorText: p.errorText }));
  const text = parts
    .filter((p) => p.type === "text")
    .map((p) => (p as unknown as { text: string }).text)
    .join(" ")
    .trim();
  return { tools, text, ms };
}

/** Free-text props the model may write. Drift here is copy drift, reported but not a failure. */
const COPY_FIELDS = ["title"];

function stripCopy(input: unknown): unknown {
  if (!input || typeof input !== "object") return input;
  return Object.fromEntries(Object.entries(input as Record<string, unknown>).filter(([k]) => !COPY_FIELDS.includes(k)));
}

function stable<T>(v: T): string {
  return JSON.stringify(v, (_, x) => (x && typeof x === "object" && !Array.isArray(x) ? Object.fromEntries(Object.entries(x).sort()) : x));
}

async function main() {
  console.log(`# prove — ${N} runs per intent, model ${process.env.OPENAI_MODEL ?? "(server's OPENAI_MODEL)"}, ${new Date().toISOString().slice(0, 10)}\n`);

  console.log("## Consistency\n");
  console.log("| intent | tool (n/N) | distinct specs | distinct ignoring copy fields | median ms | spec |");
  console.log("|---|---|---|---|---|---|");
  let drifts = 0;
  let copyDrifts = 0;
  for (const it of prompts.intents) {
    const runs: Turn[] = [];
    for (let i = 0; i < N; i++) runs.push(await turn(it.prompt));
    const toolNames = runs.map((r) => r.tools.map((t) => t.name).join("+") || "(none)");
    const majority = mode(toolNames);
    const specs = runs.map((r) => stable(r.tools.map((t) => t.input)));
    const structural = runs.map((r) => stable(r.tools.map((t) => stripCopy(t.input))));
    const distinct = new Set(specs);
    const distinctStructural = new Set(structural);
    if (distinctStructural.size > 1) drifts++;
    else if (distinct.size > 1) copyDrifts++;
    const ms = runs.map((r) => r.ms).sort((a, b) => a - b)[Math.floor(N / 2)];
    console.log(`| ${it.id} | ${majority} (${toolNames.filter((t) => t === majority).length}/${N}) | ${distinct.size} | ${distinctStructural.size} | ${ms} | \`${mode(specs)}\` |`);
    if (distinct.size > 1) {
      for (const [s, c] of count(specs)) console.log(`|   ↳ variant ×${c} | | | | | \`${s}\` |`);
    }
  }
  console.log(`\nIntents with structural drift (any field but ${COPY_FIELDS.join(", ")}): ${drifts}/${prompts.intents.length}`);
  console.log(`Intents with copy-only drift (${COPY_FIELDS.join(", ")}): ${copyDrifts}/${prompts.intents.length}\n`);

  console.log("## Refusal\n");
  console.log("| prompt | tool calls | reply |");
  console.log("|---|---|---|");
  let leaks = 0;
  for (const r of prompts.refusals) {
    const t = await turn(r.prompt);
    if (t.tools.length > 0) leaks++;
    console.log(`| ${r.prompt} | ${t.tools.length} | ${t.text.replace(/\|/g, "\\|").slice(0, 220)} |`);
  }
  console.log(`\nOut-of-catalog prompts that produced a plot: ${leaks}/${prompts.refusals.length}`);
  process.exit(drifts === 0 && leaks === 0 ? 0 : 1);
}

function count(xs: string[]): Map<string, number> {
  const m = new Map<string, number>();
  for (const x of xs) m.set(x, (m.get(x) ?? 0) + 1);
  return m;
}
function mode(xs: string[]): string {
  return [...count(xs).entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "";
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
