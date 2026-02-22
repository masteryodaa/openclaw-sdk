"use client";

import { ThinkingBlock } from "@/components/thinking-block";
import { ToolCallBlock } from "@/components/tool-call-block";
import type { ChatMessage as ChatMessageType } from "@/lib/types";

/**
 * Render inline formatting: bold, inline code, links.
 */
function renderInline(text: string, keyPrefix: string) {
  // Match **bold**, `code`, [text](url)
  const parts = text.split(/(\*\*.*?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g);
  return parts.map((seg, j) => {
    if (seg.startsWith("**") && seg.endsWith("**")) {
      return <strong key={`${keyPrefix}-${j}`} className="font-semibold text-zinc-100">{seg.slice(2, -2)}</strong>;
    }
    if (seg.startsWith("`") && seg.endsWith("`")) {
      return (
        <code key={`${keyPrefix}-${j}`} className="rounded bg-zinc-700/60 px-1.5 py-0.5 text-xs text-emerald-300 font-mono">
          {seg.slice(1, -1)}
        </code>
      );
    }
    const linkMatch = seg.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      return (
        <a key={`${keyPrefix}-${j}`} href={linkMatch[2]} target="_blank" rel="noopener noreferrer"
           className="text-emerald-400 underline underline-offset-2 hover:text-emerald-300">
          {linkMatch[1]}
        </a>
      );
    }
    return seg;
  });
}

/**
 * Markdown renderer for assistant content.
 * Handles code blocks, headings, lists, bold, inline code, links.
 */
function renderContent(content: string) {
  if (!content) return null;

  // Strip incomplete/orphan HTML tags that OpenClaw sometimes leaves
  let cleaned = content.replace(/<\/?\w*\s*$/g, "").replace(/<[^>]*$/g, "");
  // Remove stray `</` fragments
  cleaned = cleaned.replace(/<\/\s*$/, "").trim();
  content = cleaned;

  // Split by fenced code blocks first
  const parts = content.split(/(```[\s\S]*?```)/g);

  return parts.map((part, i) => {
    if (part.startsWith("```")) {
      const match = part.match(/```(\w+)?\n?([\s\S]*?)```/);
      if (match) {
        const lang = match[1] || "";
        const code = match[2].trimEnd();
        return (
          <div key={i} className="my-3 rounded-lg border border-zinc-700 bg-zinc-900/80 overflow-x-auto">
            {lang && (
              <div className="border-b border-zinc-700/60 px-3 py-1 text-[10px] text-zinc-500 uppercase tracking-wider">
                {lang}
              </div>
            )}
            <pre className="p-3 text-xs leading-relaxed text-zinc-300">
              <code>{code}</code>
            </pre>
          </div>
        );
      }
    }

    // Process lines for headings, lists, paragraphs
    const lines = part.split("\n");
    const elements: React.ReactNode[] = [];
    let listItems: React.ReactNode[] = [];
    let listType: "ul" | "ol" | null = null;

    const flushList = () => {
      if (listItems.length > 0 && listType) {
        const Tag = listType;
        elements.push(
          <Tag key={`list-${elements.length}`}
               className={`my-1.5 space-y-0.5 ${listType === "ul" ? "list-disc" : "list-decimal"} pl-5 text-zinc-300`}>
            {listItems}
          </Tag>
        );
        listItems = [];
        listType = null;
      }
    };

    for (let li = 0; li < lines.length; li++) {
      const line = lines[li];
      const trimmed = line.trim();

      // Skip empty lines (flush list)
      if (trimmed === "") {
        flushList();
        continue;
      }

      // Headings: ### / ## / #
      const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)/);
      if (headingMatch) {
        flushList();
        const level = headingMatch[1].length;
        const text = headingMatch[2];
        const cls = level === 1 ? "text-base font-bold text-zinc-50 mt-3 mb-1"
          : level === 2 ? "text-sm font-bold text-zinc-100 mt-2.5 mb-1"
          : "text-sm font-semibold text-zinc-200 mt-2 mb-0.5";
        elements.push(
          <div key={`h-${i}-${li}`} className={cls}>
            {renderInline(text, `h-${i}-${li}`)}
          </div>
        );
        continue;
      }

      // Unordered list: * item, - item
      const ulMatch = trimmed.match(/^[*\-+]\s+(.+)/);
      if (ulMatch) {
        if (listType !== "ul") flushList();
        listType = "ul";
        listItems.push(
          <li key={`li-${i}-${li}`} className="text-sm leading-relaxed">
            {renderInline(ulMatch[1], `li-${i}-${li}`)}
          </li>
        );
        continue;
      }

      // Ordered list: 1. item
      const olMatch = trimmed.match(/^\d+[.)]\s+(.+)/);
      if (olMatch) {
        if (listType !== "ol") flushList();
        listType = "ol";
        listItems.push(
          <li key={`li-${i}-${li}`} className="text-sm leading-relaxed">
            {renderInline(olMatch[1], `li-${i}-${li}`)}
          </li>
        );
        continue;
      }

      // Horizontal rule
      if (/^[-*_]{3,}$/.test(trimmed)) {
        flushList();
        elements.push(<hr key={`hr-${i}-${li}`} className="my-2 border-zinc-700" />);
        continue;
      }

      // Regular paragraph line
      flushList();
      elements.push(
        <span key={`p-${i}-${li}`} className="block text-sm leading-relaxed">
          {renderInline(trimmed, `p-${i}-${li}`)}
        </span>
      );
    }

    flushList();

    return <div key={i}>{elements}</div>;
  });
}

export function ChatMessage({ message }: { message: ChatMessageType }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-3 ${
          isUser
            ? "bg-emerald-600/20 text-emerald-50 border border-emerald-500/20"
            : "bg-zinc-800 text-zinc-100 border border-zinc-700"
        }`}
      >
        {/* Thinking block */}
        {message.thinking && (
          <ThinkingBlock thinking={message.thinking} />
        )}

        {/* Tool calls */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mb-2 space-y-1">
            {message.tool_calls.map((tc, i) => (
              <ToolCallBlock key={i} toolCall={tc} />
            ))}
          </div>
        )}

        {/* Content */}
        <div className="text-sm leading-relaxed">
          {isUser ? (
            <span className="whitespace-pre-wrap">{message.content}</span>
          ) : (
            renderContent(message.content)
          )}
        </div>

        {/* Files */}
        {message.files && message.files.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {message.files.map((f, i) => (
              <span
                key={i}
                className="inline-flex items-center rounded bg-zinc-700 px-2 py-0.5 text-xs text-zinc-300"
              >
                {f.name || f.path}
              </span>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <div className="mt-1 text-xs text-zinc-500">
          {new Date(message.created_at).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}
