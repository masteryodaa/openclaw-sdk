"use client";

import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

interface PromptInputProps {
  onSubmit: (text: string) => void;
  placeholder?: string;
  loading?: boolean;
  buttonText?: string;
}

export function PromptInput({
  onSubmit,
  placeholder = "Describe what you want to build...",
  loading = false,
  buttonText = "Start Building",
}: PromptInputProps) {
  const [text, setText] = useState("");

  const handleSubmit = () => {
    if (!text.trim() || loading) return;
    onSubmit(text.trim());
    setText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="relative">
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="min-h-[120px] resize-none rounded-xl border-zinc-700 bg-zinc-900 pr-24 text-base placeholder:text-zinc-500 focus:border-emerald-500 focus:ring-emerald-500/20"
        disabled={loading}
      />
      <Button
        onClick={handleSubmit}
        disabled={!text.trim() || loading}
        className="absolute bottom-3 right-3 bg-emerald-600 hover:bg-emerald-500 text-white"
        size="sm"
      >
        {loading ? "Creating..." : buttonText}
      </Button>
    </div>
  );
}
