"use client";

import { useState, useMemo, useEffect, useRef } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileTree } from "@/components/file-tree";
import { CodeViewer } from "@/components/code-viewer";
import { BuildProgress } from "@/components/build-progress";
import type { GeneratedFile, ChatMessage } from "@/lib/types";

interface PreviewPanelProps {
  files: GeneratedFile[];
  messages: ChatMessage[];
  workspaceHtml?: string | null;
}

interface BuildEvent {
  event: string;
  detail: string;
}

interface ExtractedCode {
  language: string;
  filename: string;
  code: string;
}

/**
 * Extract code blocks from assistant messages.
 * Looks for ```lang ... ``` patterns in message content.
 */
function extractCodeBlocks(messages: ChatMessage[]): ExtractedCode[] {
  const blocks: ExtractedCode[] = [];
  const codeRegex = /```(\w+)?(?:\s*\n|\s)([\s\S]*?)```/g;

  for (const msg of messages) {
    if (msg.role !== "assistant" || !msg.content) continue;
    let match;
    while ((match = codeRegex.exec(msg.content)) !== null) {
      const lang = match[1] || "text";
      const code = match[2].trim();
      if (code.length > 10) {
        const beforeBlock = msg.content.slice(0, match.index);
        const filenameMatch = beforeBlock.match(/[`']([^`'\s]+\.\w+)[`']/g);
        const filename = filenameMatch
          ? filenameMatch[filenameMatch.length - 1].replace(/[`']/g, "")
          : `snippet-${blocks.length + 1}.${lang}`;
        blocks.push({ language: lang, filename, code });
      }
    }
  }
  return blocks;
}

/**
 * Find the best HTML content to preview.
 * Checks code blocks first, then generated files.
 */
function findPreviewableHtml(
  codeBlocks: ExtractedCode[],
  files: GeneratedFile[],
  workspaceHtml?: string | null,
): string | null {
  // Workspace HTML from OpenClaw agent takes priority (real file written to disk)
  if (workspaceHtml) return workspaceHtml;
  // Then check the latest HTML code block from messages
  for (let i = codeBlocks.length - 1; i >= 0; i--) {
    const block = codeBlocks[i];
    if (block.language === "html" || block.code.includes("<!DOCTYPE") || block.code.includes("<html")) {
      return block.code;
    }
  }
  // Check generated files for HTML
  for (let i = files.length - 1; i >= 0; i--) {
    const f = files[i];
    if (f.content && (f.mime_type === "text/html" || f.name.endsWith(".html"))) {
      return f.content;
    }
  }
  return null;
}

/** Sandboxed iframe preview for HTML content. */
function HtmlPreview({ html }: { html: string }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (iframeRef.current) {
      // Use srcdoc for sandboxed inline HTML rendering
      iframeRef.current.srcdoc = html;
    }
  }, [html]);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-zinc-700/50 bg-zinc-900/50">
        <span className="text-[10px] text-zinc-500 uppercase tracking-wider">Live Preview</span>
        <button
          onClick={() => {
            // Open in new tab
            const win = window.open("", "_blank");
            if (win) {
              win.document.write(html);
              win.document.close();
            }
          }}
          className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors"
          title="Open in new tab"
        >
          Open in tab &#8599;
        </button>
      </div>
      <div className="flex-1 bg-white rounded-b">
        <iframe
          ref={iframeRef}
          sandbox="allow-scripts"
          className="w-full h-full border-0 rounded-b"
          title="Preview"
        />
      </div>
    </div>
  );
}

export function PreviewPanel({ files, messages, workspaceHtml }: PreviewPanelProps) {
  const [selectedFile, setSelectedFile] = useState<GeneratedFile | null>(null);
  const [selectedCode, setSelectedCode] = useState<ExtractedCode | null>(null);
  const [activeTab, setActiveTab] = useState("preview");

  // Extract build events from messages
  const buildEvents: BuildEvent[] = messages
    .filter((m) => m.content && m.content.startsWith("["))
    .map((m) => {
      const match = m.content.match(/\[(\w+)\]\s*(.*)/);
      return match ? { event: match[1], detail: match[2] } : null;
    })
    .filter((e): e is BuildEvent => e !== null);

  // Extract code blocks from assistant messages
  const codeBlocks = useMemo(() => extractCodeBlocks(messages), [messages]);

  // Find previewable HTML
  const previewHtml = useMemo(
    () => findPreviewableHtml(codeBlocks, files, workspaceHtml),
    [codeBlocks, files, workspaceHtml],
  );

  // Auto-switch to preview tab when HTML appears
  const prevHtmlRef = useRef<string | null>(null);
  useEffect(() => {
    if (previewHtml && previewHtml !== prevHtmlRef.current) {
      prevHtmlRef.current = previewHtml;
      setActiveTab("preview");
    }
  }, [previewHtml]);

  const hasFiles = files.length > 0;

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="flex h-full flex-col">
      <TabsList className="mx-4 mt-2 bg-zinc-800">
        <TabsTrigger value="preview" className="text-xs">
          Preview {previewHtml ? "\u25CF" : ""}
        </TabsTrigger>
        <TabsTrigger value="code" className="text-xs">
          Code {codeBlocks.length > 0 && `(${codeBlocks.length})`}
        </TabsTrigger>
        <TabsTrigger value="files" className="text-xs">
          Files {hasFiles && `(${files.length})`}
        </TabsTrigger>
        <TabsTrigger value="build" className="text-xs">Build</TabsTrigger>
      </TabsList>

      <TabsContent value="preview" className="flex-1 overflow-hidden mx-4 mb-2 rounded-lg border border-zinc-700/50">
        {previewHtml ? (
          <HtmlPreview html={previewHtml} />
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <div className="text-3xl mb-2 opacity-30">&#x1F310;</div>
              <p className="text-zinc-500 text-sm">
                HTML previews will appear here automatically.
              </p>
              <p className="text-zinc-600 text-xs mt-1">
                Ask the agent to generate HTML, CSS, or a web page.
              </p>
            </div>
          </div>
        )}
      </TabsContent>

      <TabsContent value="code" className="flex-1 overflow-hidden px-4">
        <ScrollArea className="h-full">
          {selectedFile ? (
            <div>
              <button
                onClick={() => setSelectedFile(null)}
                className="text-xs text-zinc-500 hover:text-zinc-300 mb-2"
              >
                &larr; Back to code list
              </button>
              <CodeViewer file={selectedFile} />
            </div>
          ) : selectedCode ? (
            <div>
              <button
                onClick={() => setSelectedCode(null)}
                className="text-xs text-zinc-500 hover:text-zinc-300 mb-2"
              >
                &larr; Back to code list
              </button>
              <CodeViewer
                file={{
                  id: "extracted",
                  project_id: "",
                  name: selectedCode.filename,
                  path: selectedCode.filename,
                  content: selectedCode.code,
                  size_bytes: selectedCode.code.length,
                  mime_type: "text/plain",
                  created_at: "",
                }}
              />
            </div>
          ) : codeBlocks.length > 0 ? (
            <div className="space-y-1 py-2">
              {codeBlocks.map((block, i) => (
                <button
                  key={i}
                  onClick={() => setSelectedCode(block)}
                  className="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm text-zinc-300 hover:bg-zinc-800 transition-colors"
                >
                  <span className="text-xs text-emerald-500 font-mono uppercase w-10">
                    {block.language}
                  </span>
                  <span className="truncate font-mono text-xs">{block.filename}</span>
                  <span className="ml-auto text-xs text-zinc-600">
                    {block.code.split("\n").length} lines
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-zinc-500 text-sm py-8 text-center">
              Code from agent responses will appear here.
            </p>
          )}
        </ScrollArea>
      </TabsContent>

      <TabsContent value="files" className="flex-1 overflow-hidden px-4">
        <ScrollArea className="h-full">
          {files.length === 0 ? (
            <p className="text-zinc-500 text-sm py-8 text-center">
              No files generated yet. Start building!
            </p>
          ) : (
            <FileTree
              files={files}
              onSelect={(f) => {
                setSelectedFile(f);
                setSelectedCode(null);
                setActiveTab("code");
              }}
              selected={selectedFile?.id}
            />
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
