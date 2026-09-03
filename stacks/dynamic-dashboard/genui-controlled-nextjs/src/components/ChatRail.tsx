"use client";

import type { useChat } from "@ai-sdk/react";
import { useState } from "react";
import { describe, type PlotOutput } from "@/catalog/output";
import type { ChatMessage } from "@/catalog/tools";

type Chat = ReturnType<typeof useChat<ChatMessage>>;

export function ChatRail({ chat }: { chat: Chat }) {
  const [input, setInput] = useState("");
  const busy = chat.status === "submitted" || chat.status === "streaming";

  return (
    <aside className="flex h-screen flex-col border-r border-zinc-200 bg-white">
      <header className="border-b border-zinc-200 px-4 py-3">
        <h1 className="text-sm font-semibold">Controlled generative UI</h1>
        <p className="text-xs text-zinc-500">Ask for a scatter or bar plot over penguins or mtcars.</p>
      </header>

      <ol className="flex-1 space-y-3 overflow-y-auto px-4 py-3 text-sm" data-testid="chat-log">
        {chat.messages.map((m) => (
          <li key={m.id} className={m.role === "user" ? "text-right" : ""}>
            {m.parts.map((part, i) => {
              if (part.type === "text") {
                return (
                  <p
                    key={i}
                    className={
                      m.role === "user"
                        ? "inline-block rounded-2xl bg-zinc-900 px-3 py-1.5 text-white"
                        : "rounded-2xl bg-zinc-100 px-3 py-1.5"
                    }
                  >
                    {part.text}
                  </p>
                );
              }
              if (part.type === "tool-scatter_plot" || part.type === "tool-bar_plot") {
                const label =
                  part.state === "output-available"
                    ? describe(part.output as PlotOutput)
                    : part.state === "output-error"
                      ? `✗ ${part.errorText ?? "tool failed"}`
                      : `building ${part.type.replace("tool-", "").replace("_", " ")}…`;
                return (
                  <p key={i} className="rounded-md border border-dashed border-zinc-300 px-2 py-1 font-mono text-[11px] text-zinc-600">
                    {label}
                  </p>
                );
              }
              return null;
            })}
          </li>
        ))}
        {chat.error && <li className="text-xs text-red-600">{chat.error.message}</li>}
      </ol>

      <form
        className="border-t border-zinc-200 p-3"
        onSubmit={(e) => {
          e.preventDefault();
          const text = input.trim();
          if (!text || busy) return;
          chat.sendMessage({ text });
          setInput("");
        }}
      >
        <input
          className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-zinc-500"
          placeholder="e.g. flipper length vs body mass by species"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={busy}
          aria-label="Ask for a plot"
        />
        <p className="mt-1 text-[11px] text-zinc-400">{busy ? "thinking…" : "Enter to send"}</p>
      </form>
    </aside>
  );
}
