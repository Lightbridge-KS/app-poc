/**
 * The one LLM call. Everything the model may do is in `tools`; everything it may not do
 * is enforced by their schemas. The response is the AI SDK UI message stream, so tool
 * calls arrive on the client as typed `tool-scatter_plot` / `tool-bar_plot` parts.
 */
import { openai } from "@ai-sdk/openai";
import { convertToModelMessages, createUIMessageStreamResponse, streamText, toUIMessageStream } from "ai";
import { SYSTEM_PROMPT } from "@/catalog/systemPrompt";
import { tools, type ChatMessage } from "@/catalog/tools";

export const maxDuration = 60;

export const MODEL_ID = process.env.OPENAI_MODEL ?? "gpt-5.6-terra";

export async function POST(req: Request) {
  const { messages }: { messages: ChatMessage[] } = await req.json();

  const result = streamText({
    model: openai(MODEL_ID),
    instructions: SYSTEM_PROMPT,
    // `tools` here applies each tool's toModelOutput to prior turns' outputs, so the
    // model sees the one-line summaries, never the rows.
    messages: await convertToModelMessages(messages, { tools }),
    tools,
    providerOptions: { openai: { reasoningEffort: "low" } },
  });

  return createUIMessageStreamResponse({
    stream: toUIMessageStream({
      stream: result.stream,
      // A PoC wants the real message in the chat rail (missing key, bad model id), not "An error occurred."
      onError: (e) => (e instanceof Error ? e.message : String(e)),
    }),
  });
}
