"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { GeneratedFile } from "@/lib/types";

export function CodeViewer({ file }: { file: GeneratedFile }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(file.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = file.content.split("\n");

  return (
    <div className="py-2">
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-sm text-zinc-300">{file.path || file.name}</span>
        <Button variant="ghost" size="sm" onClick={handleCopy} className="text-xs h-7">
          {copied ? "Copied!" : "Copy"}
        </Button>
      </div>
      <div className="rounded-lg border border-zinc-700 bg-zinc-900 overflow-x-auto">
        <pre className="p-4 text-sm leading-relaxed">
          {lines.map((line, i) => (
            <div key={i} className="flex">
              <span className="mr-4 inline-block w-8 text-right text-zinc-600 select-none">
                {i + 1}
              </span>
              <code className="text-zinc-300">{line || " "}</code>
            </div>
          ))}
        </pre>
      </div>
    </div>
  );
}
