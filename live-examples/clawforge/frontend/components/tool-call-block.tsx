"use client";

import { useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { ToolCall } from "@/lib/types";

export function ToolCallBlock({ toolCall }: { toolCall: ToolCall }) {
  const [open, setOpen] = useState(false);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex items-center gap-1.5 text-xs text-amber-400/80 hover:text-amber-300 transition-colors">
        <span className="text-sm">&#x1f527;</span>
        <span className="font-mono">{toolCall.tool}</span>
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-1">
        <div className="rounded bg-zinc-900 border border-zinc-700 p-2 text-xs font-mono">
          <div className="text-zinc-400">
            <span className="text-zinc-500">Input: </span>
            <span className="whitespace-pre-wrap">{typeof toolCall.input === "string" ? toolCall.input : JSON.stringify(toolCall.input, null, 2)}</span>
          </div>
          {toolCall.output && (
            <div className="mt-1 text-zinc-400">
              <span className="text-zinc-500">Output: </span>
              <span className="whitespace-pre-wrap">{typeof toolCall.output === "string" ? toolCall.output : JSON.stringify(toolCall.output, null, 2)}</span>
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
