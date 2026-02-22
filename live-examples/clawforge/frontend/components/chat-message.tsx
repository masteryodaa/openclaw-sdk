"use client";

import { ThinkingBlock } from "@/components/thinking-block";
import { ToolCallBlock } from "@/components/tool-call-block";
import type { ChatMessage as ChatMessageType } from "@/lib/types";

/**
 * Simple markdown-ish renderer for assistant content.
 * Handles code blocks, bold, inline code, and newlines.
 */
function renderContent(content: string) {
  if (!content) return null;

  // Split by code blocks first
  const parts = content.split(/(```[\s\S]*?```)/g);

  return parts.map((part, i) => {
    if (part.startsWith("```")) {
      // Code block — extract language and code
      const match = part.match(/```(\w+)?\n?([\s\S]*?)```/);
      if (match) {
        const lang = match[1] || "";
        const code = match[2].trimEnd();
        return (
          <div key={i} className="my-2 rounded-md border border-zinc-700 bg-zinc-900 overflow-x-auto">
            {lang && (
              <div className="border-b border-zinc-700 px-3 py-1 text-[10px] text-zinc-500 uppercase">
                {lang}
              </div>
            )}
            <pre className="p-3 text-xs leading-relaxed text-zinc-300">
              <code>{code}</code>
            </pre>
          </div>
        );
      }
    }

    // Regular text — handle inline formatting
    return (
      <span key={i} className="whitespace-pre-wrap">
        {part.split(/(\*\*.*?\*\*|`[^`]+`)/g).map((seg, j) => {
          if (seg.startsWith("**") && seg.endsWith("**")) {
            return <strong key={j} className="font-semibold">{seg.slice(2, -2)}</strong>;
          }
          if (seg.startsWith("`") && seg.endsWith("`")) {
            return (
              <code key={j} className="rounded bg-zinc-700/50 px-1 py-0.5 text-xs text-emerald-300 font-mono">
                {seg.slice(1, -1)}
              </code>
            );
          }
          return seg;
        })}
      </span>
    );
  });
}

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
        <div className="text-sm leading-relaxed">
          {isUser ? (
            <span className="whitespace-pre-wrap">{message.content}</span>
          ) : (
            renderContent(message.content)
          )}
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
