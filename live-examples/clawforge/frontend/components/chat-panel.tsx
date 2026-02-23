"use client";

import { useRef, useEffect, useCallback } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessage } from "@/components/chat-message";
import { PromptInput } from "@/components/prompt-input";
import { StreamingIndicator } from "@/components/streaming-indicator";
import type { ChatMessage as ChatMessageType } from "@/lib/types";
import type { StreamingStatus } from "@/app/workspace/[id]/page";

interface ChatPanelProps {
  messages: ChatMessageType[];
  onSend: (text: string) => void;
  streaming: boolean;
  streamStatus?: StreamingStatus;
  /** True while polling for sub-agent file writes after the main stream ends. */
  postStreamChecking?: boolean;
}

export function ChatPanel({ messages, onSend, streaming, streamStatus, postStreamChecking }: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    const viewport = scrollRef.current?.querySelector("[data-radix-scroll-area-viewport]");
    if (viewport) {
      viewport.scrollTo({ top: viewport.scrollHeight, behavior: "smooth" });
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(scrollToBottom, 50);
    return () => clearTimeout(t);
  }, [messages, streamStatus, scrollToBottom]);

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 overflow-hidden">
        <ScrollArea className="h-full px-4 py-4">
          <div className="space-y-4">
            {messages.length === 0 ? (
              <p className="text-center text-zinc-500 py-12">
                Start a conversation with your AI agent.
              </p>
            ) : (
              messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))
            )}
            {/* Real-time streaming indicator */}
            {streamStatus?.active && (
              <StreamingIndicator status={streamStatus} />
            )}
            {/* Post-stream indicator: sub-agent still writing files */}
            {!streaming && postStreamChecking && (
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-800/60 border border-zinc-700/40 text-xs text-zinc-400">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                Agent working in background — checking for files…
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
      <div className="border-t border-zinc-800 p-4">
        <PromptInput
          onSubmit={onSend}
          placeholder="Send a message..."
          loading={streaming}
          buttonText="Send"
          compact
        />
      </div>
    </div>
  );
}
