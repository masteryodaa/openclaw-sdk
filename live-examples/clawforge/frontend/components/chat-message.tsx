"use client";

import { ThinkingBlock } from "@/components/thinking-block";
import { ToolCallBlock } from "@/components/tool-call-block";
import type { ChatMessage as ChatMessageType } from "@/lib/types";

export function ChatMessage({ message }: { message: ChatMessageType }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-3 ${
          isUser
            ? "bg-emerald-600/20 text-emerald-50 border border-emerald-500/20"
            : "bg-zinc-800 text-zinc-100 border border-zinc-700"
        }`}
      >
        {/* Thinking block */}
        {message.thinking && (
          <ThinkingBlock thinking={message.thinking} />
        )}

        {/* Tool calls */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mb-2 space-y-1">
            {message.tool_calls.map((tc, i) => (
              <ToolCallBlock key={i} toolCall={tc} />
            ))}
          </div>
        )}

        {/* Content */}
        <div className="whitespace-pre-wrap text-sm leading-relaxed">
          {message.content}
        </div>

        {/* Files */}
        {message.files && message.files.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {message.files.map((f, i) => (
              <span
                key={i}
                className="inline-flex items-center rounded bg-zinc-700 px-2 py-0.5 text-xs text-zinc-300"
              >
                {f.name || f.path}
              </span>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <div className="mt-1 text-xs text-zinc-500">
          {new Date(message.created_at).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}
