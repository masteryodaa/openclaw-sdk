"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import {
  getProject,
  listProjects,
  getSessionStatus,
  readWorkspaceFile,
  saveWorkspaceRecord,
} from "@/lib/api";
import { streamSSE } from "@/lib/sse";
import { ChatPanel } from "@/components/chat-panel";
import { PreviewPanel } from "@/components/preview-panel";
import { ProjectSidebar } from "@/components/project-sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Project, ChatMessage, GeneratedFile } from "@/lib/types";
import type { SessionTool } from "@/lib/api";

/**
 * Inline all relative CSS and JS assets referenced in the HTML so it renders
 * correctly inside a sandboxed srcdoc iframe (which has no base URL).
 *
 * Example: <link href="style.css"> → <style>...css content...</style>
 *          <script src="app.js"> → <script>...js content...</script>
 */
async function inlineWorkspaceAssets(html: string, htmlPath: string): Promise<string> {
  // Derive base directory from the HTML file's path (e.g. "erp-website/")
  const baseDir = htmlPath.includes("/")
    ? htmlPath.slice(0, htmlPath.lastIndexOf("/") + 1)
    : "";

  let result = html;

  // Inline CSS: <link rel="stylesheet" href="relative/path.css">
  const linkRe = /<link([^>]*?)href=["']([^"']+)["']([^>]*?)\/?>/gi;
  const cssReplacements: Array<{ tag: string; path: string }> = [];
  let m: RegExpExecArray | null;
  while ((m = linkRe.exec(html)) !== null) {
    const attrs = m[1] + m[3];
    const href = m[2];
    if (/rel=["']stylesheet["']/i.test(attrs) && !/^https?:|^\/\//i.test(href)) {
      cssReplacements.push({ tag: m[0], path: baseDir + href });
    }
  }
  for (const { tag, path } of cssReplacements) {
    try {
      const css = await readWorkspaceFile(path);
      result = result.replace(tag, `<style>${css}</style>`);
    } catch { /* skip missing files */ }
  }

  // Inline JS: <script src="relative/path.js"></script>
  const scriptRe = /<script([^>]*?)src=["']([^"']+)["']([^>]*?)><\/script>/gi;
  const jsReplacements: Array<{ tag: string; path: string }> = [];
  while ((m = scriptRe.exec(html)) !== null) {
    const src = m[2];
    if (!/^https?:|^\/\//i.test(src)) {
      jsReplacements.push({ tag: m[0], path: baseDir + src });
    }
  }
  for (const { tag, path } of jsReplacements) {
    try {
      const js = await readWorkspaceFile(path);
      result = result.replace(tag, `<script>${js}</script>`);
    } catch { /* skip missing files */ }
  }

  return result;
}

/** Describes what the agent is currently doing — with real tool names. */
export interface StreamingStatus {
  active: boolean;
  phase: string;
  toolName?: string;
  toolHistory: SessionTool[];
  elapsed: number;
}

export default function WorkspacePage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [files, setFiles] = useState<GeneratedFile[]>([]);
  /** Wrapper: keep filesRef in sync so callbacks always see current list. */
  const setFilesAndRef = useCallback((updater: GeneratedFile[] | ((prev: GeneratedFile[]) => GeneratedFile[])) => {
    setFiles((prev) => {
      const next = typeof updater === "function" ? updater(prev) : updater;
      filesRef.current = next;
      return next;
    });
  }, []);
  const [streaming, setStreaming] = useState(false);
  const [streamStatus, setStreamStatus] = useState<StreamingStatus>({
    active: false, phase: "", toolHistory: [], elapsed: 0,
  });
  const [buildMode, setBuildMode] = useState<"pipeline" | "supervisor">("pipeline");
  const [building, setBuilding] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);
  const [workspaceHtml, setWorkspaceHtml] = useState<string | null>(null);

  const [autoSent, setAutoSent] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  // Ref to trigger an immediate session status check from inside SSE handler
  const immediateCheckRef = useRef<(() => Promise<void>) | null>(null);
  // Mirror of files state for use inside callbacks without stale closure issues
  const filesRef = useRef<GeneratedFile[]>([]);

  /** Persist a workspace file to DB, inline its CSS/JS, then update preview.
   *  Always reflects the current disk state — handles agent re-writing a file. */
  const persistAndPreview = useCallback(async (path: string) => {
    try {
      const saved = await saveWorkspaceRecord(projectId, path);
      // Replace stale entry or add new entry (file may have been re-written)
      setFilesAndRef((prev) => {
        const without = prev.filter((f) => f.path !== saved.path);
        return [...without, saved];
      });
      // Only preview HTML files — always read fresh content from disk via the
      // workspace endpoint so CSS/JS siblings are up-to-date too
      if (saved.mime_type === "text/html" || saved.name.endsWith(".html") || saved.name.endsWith(".htm")) {
        // Read directly from disk (workspace endpoint) to get the absolute latest;
        // saved.content is already fresh from the upsert but re-fetching siblings
        // (CSS/JS) via inlineWorkspaceAssets ensures they're also current.
        const rawHtml = saved.content;
        const inlined = await inlineWorkspaceAssets(rawHtml, path);
        setWorkspaceHtml(inlined);
      }
    } catch {
      // Fallback: read + inline directly from disk
      try {
        const rawHtml = await readWorkspaceFile(path);
        const inlined = await inlineWorkspaceAssets(rawHtml, path);
        setWorkspaceHtml(inlined);
      } catch { /* ignore */ }
    }
  }, [projectId, setFilesAndRef]);

  /** Check session status immediately and update tool/file state. */
  const checkSessionNow = useCallback(async () => {
    try {
      const status = await getSessionStatus(projectId);
      const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
      if (status.tools.length > 0) {
        const lastTool = status.tools[status.tools.length - 1];
        setStreamStatus((prev) => ({
          ...prev,
          phase: lastTool.phase === "call" ? "tool_call" : prev.phase,
          toolName: lastTool.phase === "call" ? lastTool.tool : prev.toolName,
          toolHistory: status.tools,
          elapsed,
        }));
      } else {
        setStreamStatus((prev) => ({ ...prev, elapsed }));
      }

      // Collect ALL HTML paths to refresh: session-detected new files + already-known files
      // This is the key fix: don't rely solely on session text-parsing to detect re-writes
      const htmlPaths = new Set<string>();
      for (const f of status.files) {
        if (f.path.endsWith(".html") || f.path.endsWith(".htm")) htmlPaths.add(f.path);
      }
      for (const f of filesRef.current) {
        if (f.mime_type === "text/html" || f.name.endsWith(".html") || f.name.endsWith(".htm")) {
          htmlPaths.add(f.path);
        }
      }
      for (const path of Array.from(htmlPaths)) {
        await persistAndPreview(path);
      }
    } catch { /* polling failure is not fatal */ }
  }, [projectId, persistAndPreview]);

  // Mount: load project + restore preview from DB (no OpenClaw session dependency)
  useEffect(() => {
    getProject(projectId).then((p) => {
      setProject(p);
      setMessages(p.messages || []);
      const projectFiles: GeneratedFile[] = p.files || [];
      filesRef.current = projectFiles;
      setFiles(projectFiles);

      // Restore workspace HTML — always call persistAndPreview for known HTML files
      // so the upsert path runs and picks up any disk changes from the last session.
      const htmlFiles = projectFiles.filter(
        (f) => f.mime_type === "text/html" || f.name.endsWith(".html") || f.name.endsWith(".htm"),
      );
      if (htmlFiles.length > 0) {
        // Re-sync all known HTML files with disk (upsert updates DB if agent re-wrote them)
        Promise.all(htmlFiles.map((f) => persistAndPreview(f.path))).catch(() => {});
      } else {
        // No known HTML yet — fall back to session poll
        getSessionStatus(projectId).then((status) => {
          for (const f of status.files) {
            if (f.path.endsWith(".html") || f.path.endsWith(".htm")) {
              persistAndPreview(f.path);
              break;
            }
          }
        }).catch(() => {});
      }
    });
    listProjects().then(setProjects).catch(() => {});
  }, [projectId, persistAndPreview]);

  const refreshProject = useCallback(async () => {
    try {
      const p = await getProject(projectId);
      setProject(p);
      setMessages(p.messages || []);
      setFilesAndRef(p.files || []);
    } catch (err) {
      console.error("Refresh failed:", err);
    }
  }, [projectId, setFilesAndRef]);

  // Poll session for real tool names every 2.5s during streaming
  const startSessionPolling = useCallback(() => {
    if (pollRef.current) return;
    startTimeRef.current = Date.now();
    // Expose immediate check so SSE handler can call it
    immediateCheckRef.current = checkSessionNow;
    pollRef.current = setInterval(checkSessionNow, 2500);
  }, [checkSessionNow]);

  const stopSessionPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    immediateCheckRef.current = null;
  }, []);

  useEffect(() => {
    return () => stopSessionPolling();
  }, [stopSessionPolling]);

  const handleSendMessage = useCallback(async (text: string) => {
    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      project_id: projectId,
      role: "user",
      content: text,
      thinking: null,
      tool_calls: null,
      files: null,
      token_usage: null,
      cost_usd: 0,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setStreaming(true);
    setStreamStatus({ active: true, phase: "start", toolHistory: [], elapsed: 0 });
    startSessionPolling();

    let fullContent = "";
    let fullThinking = "";

    const assistantMsg: ChatMessage = {
      id: `temp-assistant-${Date.now()}`,
      project_id: projectId,
      role: "assistant",
      content: "",
      thinking: null,
      tool_calls: null,
      files: null,
      token_usage: null,
      cost_usd: 0,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      await streamSSE(
        "/api/chat/stream",
        { project_id: projectId, message: text, thinking: true },
        (event, data: unknown) => {
          const d = data as Record<string, unknown>;

          if (event === "run_start") {
            setStreamStatus((prev) => ({ ...prev, active: true, phase: "start" }));
          } else if (event === "status") {
            const phase = (d.phase as string) || "";
            setStreamStatus((prev) => ({ ...prev, active: true, phase }));
          } else if (event === "content") {
            fullContent += (d.text as string) || "";
            setStreamStatus((prev) => ({ ...prev, phase: "content" }));
            setMessages((prev) => {
              if (prev.length === 0) return prev;
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                updated[updated.length - 1] = { ...last, content: fullContent };
              }
              return updated;
            });
          } else if (event === "thinking") {
            fullThinking += (d.text as string) || "";
            setStreamStatus((prev) => ({ ...prev, phase: "thinking" }));
            setMessages((prev) => {
              if (prev.length === 0) return prev;
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                updated[updated.length - 1] = { ...last, thinking: fullThinking };
              }
              return updated;
            });
          } else if (event === "tool_call") {
            const toolName = (d.tool as string) || "tool";
            setStreamStatus((prev) => ({ ...prev, phase: "tool_call", toolName }));
            setMessages((prev) => {
              if (prev.length === 0) return prev;
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                const calls = last.tool_calls || [];
                updated[updated.length - 1] = {
                  ...last,
                  tool_calls: [...calls, { tool: toolName, input: (d.input as string) || "" }],
                };
              }
              return updated;
            });
          } else if (event === "tool_result") {
            setStreamStatus((prev) => ({ ...prev, phase: "start" }));
            setMessages((prev) => {
              if (prev.length === 0) return prev;
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant" && last.tool_calls && last.tool_calls.length > 0) {
                const calls = [...last.tool_calls];
                const lastCall = calls[calls.length - 1];
                calls[calls.length - 1] = { ...lastCall, output: (d.output as string) || "" };
                updated[updated.length - 1] = { ...last, tool_calls: calls };
              }
              return updated;
            });
            // Immediately check for files written by this tool (no waiting for next 2.5s poll)
            immediateCheckRef.current?.();
          } else if (event === "file_generated") {
            const filePath = d.path as string;
            setFilesAndRef((prev) => {
              if (prev.find((f) => f.path === filePath)) return prev;
              return [...prev, {
                id: `file-${Date.now()}`,
                project_id: projectId,
                name: d.name as string,
                path: filePath,
                content: "",
                size_bytes: (d.size as number) || 0,
                mime_type: (d.mimeType as string) || "text/plain",
                created_at: new Date().toISOString(),
              }];
            });
            // Immediately persist + preview if it's an HTML file
            if (filePath.endsWith(".html") || filePath.endsWith(".htm")) {
              persistAndPreview(filePath);
            }
          }
        }
      );
    } catch (err) {
      console.error("Stream error:", err);
    } finally {
      stopSessionPolling();
      setStreaming(false);
      setStreamStatus({ active: false, phase: "", toolHistory: [], elapsed: 0 });

      // Final sweep: persist ALL known HTML files + any new ones from session status.
      // Using filesRef.current (not stale closure) so we catch files added during streaming.
      try {
        const finalStatus = await getSessionStatus(projectId);
        const htmlPaths = new Set<string>();
        for (const f of finalStatus.files) {
          if (f.path.endsWith(".html") || f.path.endsWith(".htm")) htmlPaths.add(f.path);
        }
        for (const f of filesRef.current) {
          if (f.mime_type === "text/html" || f.name.endsWith(".html") || f.name.endsWith(".htm")) {
            htmlPaths.add(f.path);
          }
        }
        for (const path of Array.from(htmlPaths)) {
          await persistAndPreview(path);
        }
      } catch { /* ignore */ }

      refreshProject();
    }
  }, [projectId, refreshProject, startSessionPolling, stopSessionPolling, persistAndPreview, setFilesAndRef]);

  useEffect(() => {
    if (project && !autoSent && messages.length === 0 && project.description) {
      setAutoSent(true);
      handleSendMessage(project.description);
    }
  }, [project, autoSent, messages.length, handleSendMessage]);

  const handleBuild = useCallback(async () => {
    setBuilding(true);
    try {
      await streamSSE(
        "/api/build/stream",
        { project_id: projectId, mode: buildMode },
        (event, data: unknown) => {
          const d = data as Record<string, unknown>;
          if (event === "step_start" || event === "step_complete" || event === "build_complete" || event === "build_error") {
            const content = event === "build_error"
              ? `[Build Error] ${d.message as string}`
              : `[${event}] ${(d.step as string) || ""} ${(d.content as string) || ""}`.trim();
            setMessages((prev) => [...prev, {
              id: `build-${Date.now()}-${Math.random()}`,
              project_id: projectId,
              role: "assistant",
              content,
              thinking: null,
              tool_calls: null,
              files: null,
              token_usage: null,
              cost_usd: 0,
              created_at: new Date().toISOString(),
            }]);
          }
          if (event === "build_complete" || event === "build_error") {
            setBuilding(false);
          }
        }
      );
    } catch (err) {
      console.error("Build error:", err);
      setBuilding(false);
    } finally {
      refreshProject();
    }
  }, [projectId, buildMode, refreshProject]);

  if (!project) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="animate-pulse text-zinc-400">Loading project...</div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {sidebarOpen && (
        <ProjectSidebar
          projects={projects}
          currentId={projectId}
          onClose={() => setSidebarOpen(false)}
        />
      )}

      <div className="flex flex-1 flex-col min-w-0">
        <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-2">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="mr-1 rounded p-1 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                title="Show projects"
              >
                &#9776;
              </button>
            )}
            <h1 className="font-semibold truncate max-w-md">{project.name}</h1>
            <Badge variant="outline" className="text-xs">
              {project.status}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">
              ${project.total_cost_usd.toFixed(4)}
            </span>
            <select
              value={buildMode}
              onChange={(e) => setBuildMode(e.target.value as "pipeline" | "supervisor")}
              className="rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs text-zinc-300"
            >
              <option value="pipeline">Pipeline</option>
              <option value="supervisor">Supervisor</option>
            </select>
            <Button
              size="sm"
              onClick={handleBuild}
              disabled={building}
              className="bg-emerald-600 hover:bg-emerald-500"
            >
              {building ? "Building..." : "Build"}
            </Button>
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          <div className="w-[45%] border-r border-zinc-800">
            <ChatPanel
              messages={messages}
              onSend={handleSendMessage}
              streaming={streaming}
              streamStatus={streamStatus}
            />
          </div>
          <div className="w-[55%]">
            <PreviewPanel files={files} messages={messages} workspaceHtml={workspaceHtml} />
          </div>
        </div>
      </div>
    </div>
  );
}
