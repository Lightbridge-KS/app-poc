"use client";

/**
 * Owns the one chat session and derives the two surfaces from it:
 * the chat rail (text parts) and the card grid (tool parts).
 */
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useMemo, useState } from "react";
import type { PlotOutput } from "@/catalog/output";
import type { ChatMessage } from "@/catalog/tools";
import { CardGrid, type Card } from "./CardGrid";
import { ChatRail } from "./ChatRail";

export function Dashboard() {
  const chat = useChat<ChatMessage>({
    transport: new DefaultChatTransport({ api: "/api/chat" }),
  });
  const [dismissed, setDismissed] = useState<ReadonlySet<string>>(new Set());

  const cards = useMemo<Card[]>(() => {
    const out: Card[] = [];
    for (const m of chat.messages) {
      if (m.role !== "assistant") continue;
      for (const part of m.parts) {
        if (part.type !== "tool-scatter_plot" && part.type !== "tool-bar_plot") continue;
        if (dismissed.has(part.toolCallId)) continue;
        if (part.state === "output-available") {
          out.push({ id: part.toolCallId, state: "ready", output: part.output as PlotOutput });
        } else if (part.state === "output-error") {
          out.push({ id: part.toolCallId, state: "error", error: part.errorText ?? "tool failed" });
        } else {
          out.push({ id: part.toolCallId, state: "building" });
        }
      }
    }
    return out;
  }, [chat.messages, dismissed]);

  return (
    <div className="grid h-screen grid-cols-[380px_minmax(0,1fr)] bg-zinc-50 text-zinc-900">
      <ChatRail chat={chat} />
      <CardGrid
        cards={cards}
        onDismiss={(id) => setDismissed((s) => new Set(s).add(id))}
        onSuggest={(text) => chat.sendMessage({ text })}
      />
    </div>
  );
}
