"use client";

import { useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

export function ThinkingBlock({ thinking }: { thinking: string }) {
  const [open, setOpen] = useState(false);

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="mb-2">
      <CollapsibleTrigger className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-300 transition-colors">
        <span className="text-sm">&#x1f9e0;</span>
        <span>{open ? "Hide thinking" : "Show thinking"}</span>
        <span className="text-zinc-600">({thinking.length} chars)</span>
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-1">
        <div className="rounded bg-zinc-900 border border-zinc-700 p-3 text-xs text-zinc-400 whitespace-pre-wrap max-h-60 overflow-y-auto">
          {thinking}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
