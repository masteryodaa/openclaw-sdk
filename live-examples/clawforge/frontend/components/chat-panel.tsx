"use client";

import { useRef, useEffect } from "react";
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
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1 px-4 py-4">
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
          <div ref={bottomRef} />
        </div>
      </ScrollArea>
      <div className="border-t border-zinc-800 p-4">
        <PromptInput
          onSubmit={onSend}
          placeholder="Send a message..."
          loading={streaming}
          buttonText="Send"
        />
      </div>
    </div>
  );
}
