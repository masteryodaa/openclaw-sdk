"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileTree } from "@/components/file-tree";
import { CodeViewer } from "@/components/code-viewer";
import { BuildProgress } from "@/components/build-progress";
import type { GeneratedFile, ChatMessage } from "@/lib/types";

interface PreviewPanelProps {
  files: GeneratedFile[];
  messages: ChatMessage[];
}

interface BuildEvent {
  event: string;
  detail: string;
}

export function PreviewPanel({ files, messages }: PreviewPanelProps) {
  const [selectedFile, setSelectedFile] = useState<GeneratedFile | null>(null);

  // Extract build events from messages
  const buildEvents: BuildEvent[] = messages
    .filter((m) => m.content.startsWith("["))
    .map((m) => {
      const match = m.content.match(/\[(\w+)\]\s*(.*)/);
      return match ? { event: match[1], detail: match[2] } : null;
    })
    .filter((e): e is BuildEvent => e !== null);

  return (
    <Tabs defaultValue="files" className="flex h-full flex-col">
      <TabsList className="mx-4 mt-2 bg-zinc-800">
        <TabsTrigger value="files" className="text-xs">Files</TabsTrigger>
        <TabsTrigger value="code" className="text-xs">Code</TabsTrigger>
        <TabsTrigger value="build" className="text-xs">Build</TabsTrigger>
      </TabsList>

      <TabsContent value="files" className="flex-1 overflow-hidden px-4">
        <ScrollArea className="h-full">
          {files.length === 0 ? (
            <p className="text-zinc-500 text-sm py-8 text-center">
              No files generated yet. Start building!
            </p>
          ) : (
            <FileTree
              files={files}
              onSelect={(f) => setSelectedFile(f)}
              selected={selectedFile?.id}
            />
          )}
        </ScrollArea>
      </TabsContent>

      <TabsContent value="code" className="flex-1 overflow-hidden px-4">
        <ScrollArea className="h-full">
          {selectedFile ? (
            <CodeViewer file={selectedFile} />
          ) : (
            <p className="text-zinc-500 text-sm py-8 text-center">
              Select a file to view its code.
            </p>
          )}
        </ScrollArea>
      </TabsContent>

      <TabsContent value="build" className="flex-1 overflow-hidden px-4">
        <ScrollArea className="h-full">
          <BuildProgress events={buildEvents} />
        </ScrollArea>
      </TabsContent>
    </Tabs>
  );
}
