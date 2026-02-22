"use client";

import type { StreamingStatus } from "@/app/workspace/[id]/page";

const phaseLabels: Record<string, { icon: string; label: string; color: string }> = {
  start: { icon: "\u2699\uFE0F", label: "Agent is working...", color: "text-blue-400" },
  end: { icon: "\u2705", label: "Agent finished", color: "text-emerald-400" },
  thinking: { icon: "\uD83E\uDDE0", label: "Thinking...", color: "text-purple-400" },
  content: { icon: "\u270D\uFE0F", label: "Writing response...", color: "text-emerald-400" },
  tool_call: { icon: "\uD83D\uDD27", label: "Using tool", color: "text-amber-400" },
};

const defaultPhase = { icon: "\u23F3", label: "Processing...", color: "text-zinc-400" };

export function StreamingIndicator({ status }: { status: StreamingStatus }) {
  const info = phaseLabels[status.phase] || defaultPhase;

  return (
    <div className="flex items-center gap-2 px-2 py-1.5">
      <div className="flex items-center gap-2 rounded-lg bg-zinc-800/60 border border-zinc-700/50 px-3 py-2 text-xs">
        {/* Animated pulse dot */}
        <span className="relative flex h-2 w-2">
          <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${
            status.phase === "thinking" ? "bg-purple-400"
            : status.phase === "tool_call" ? "bg-amber-400"
            : status.phase === "content" ? "bg-emerald-400"
            : "bg-blue-400"
          }`} />
          <span className={`relative inline-flex h-2 w-2 rounded-full ${
            status.phase === "thinking" ? "bg-purple-400"
            : status.phase === "tool_call" ? "bg-amber-400"
            : status.phase === "content" ? "bg-emerald-400"
            : "bg-blue-400"
          }`} />
        </span>

        <span className="text-sm">{info.icon}</span>
        <span className={info.color}>
          {info.label}
          {status.phase === "tool_call" && status.toolName && (
            <span className="ml-1 font-mono text-zinc-300">{status.toolName}</span>
          )}
        </span>

        {/* Animated dots */}
        {status.phase !== "end" && status.phase !== "content" && (
          <span className="inline-flex gap-0.5">
            <span className="animate-bounce text-zinc-500" style={{ animationDelay: "0ms" }}>.</span>
            <span className="animate-bounce text-zinc-500" style={{ animationDelay: "150ms" }}>.</span>
            <span className="animate-bounce text-zinc-500" style={{ animationDelay: "300ms" }}>.</span>
          </span>
        )}
      </div>
    </div>
  );
}
