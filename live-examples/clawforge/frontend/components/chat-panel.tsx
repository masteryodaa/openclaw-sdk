"use client";

import { useRef, useEffect, useCallback } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessage } from "@/components/chat-message";
import { PromptInput } from "@/components/prompt-input";
import type { ChatMessage as ChatMessageType } from "@/lib/types";

interface ChatPanelProps {
  messages: ChatMessageType[];
  onSend: (text: string) => void;
  streaming: boolean;
}

export function ChatPanel({ messages, onSend, streaming }: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    // ScrollArea uses a [data-radix-scroll-area-viewport] child as the actual scrollable element
    const viewport = scrollRef.current?.querySelector("[data-radix-scroll-area-viewport]");
    if (viewport) {
      viewport.scrollTo({ top: viewport.scrollHeight, behavior: "smooth" });
    }
  }, []);

  useEffect(() => {
    // Small delay to let React finish rendering new content
    const t = setTimeout(scrollToBottom, 50);
    return () => clearTimeout(t);
  }, [messages, scrollToBottom]);

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
