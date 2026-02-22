"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { getProject, listProjects } from "@/lib/api";
import { streamSSE } from "@/lib/sse";
import { ChatPanel } from "@/components/chat-panel";
import { PreviewPanel } from "@/components/preview-panel";
import { ProjectSidebar } from "@/components/project-sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Project, ChatMessage, GeneratedFile } from "@/lib/types";

export default function WorkspacePage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [files, setFiles] = useState<GeneratedFile[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [buildMode, setBuildMode] = useState<"pipeline" | "supervisor">("pipeline");
  const [building, setBuilding] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);

  const [autoSent, setAutoSent] = useState(false);

  // Load project + project list
  useEffect(() => {
    getProject(projectId).then((p) => {
      setProject(p);
      setMessages(p.messages || []);
      setFiles(p.files || []);
    });
    listProjects().then(setProjects).catch(() => {});
  }, [projectId]);

  // Refresh project data (messages + files) from DB
  const refreshProject = useCallback(async () => {
    try {
      const p = await getProject(projectId);
      setProject(p);
      setMessages(p.messages || []);
      setFiles(p.files || []);
    } catch (err) {
      console.error("Refresh failed:", err);
    }
  }, [projectId]);

  const handleSendMessage = useCallback(async (text: string) => {
    // Add user message optimistically
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

    // Stream response
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
          if (event === "content") {
            fullContent += (d.text as string) || "";
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
            setMessages((prev) => {
              if (prev.length === 0) return prev;
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                const calls = last.tool_calls || [];
                updated[updated.length - 1] = {
                  ...last,
                  tool_calls: [...calls, { tool: d.tool as string, input: d.input as string }],
                };
              }
              return updated;
            });
          } else if (event === "tool_result") {
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
          } else if (event === "file_generated") {
            setFiles((prev) => [...prev, {
              id: `file-${Date.now()}`,
              project_id: projectId,
              name: d.name as string,
              path: d.path as string,
              content: "",
              size_bytes: (d.size as number) || 0,
              mime_type: (d.mimeType as string) || "text/plain",
              created_at: new Date().toISOString(),
            }]);
          }
        }
      );
    } catch (err) {
      console.error("Stream error:", err);
    } finally {
      setStreaming(false);
      // Re-fetch project from DB to get saved messages, files, and costs
      refreshProject();
    }
  }, [projectId, refreshProject]);

  // Auto-send the project description as the first message for new projects
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
            // Add build events as system messages
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
      {/* Project sidebar */}
      {sidebarOpen && (
        <ProjectSidebar
          projects={projects}
          currentId={projectId}
          onClose={() => setSidebarOpen(false)}
        />
      )}

      {/* Main workspace */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Top bar */}
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

        {/* Two-panel layout */}
        <div className="flex flex-1 overflow-hidden">
          <div className="w-[45%] border-r border-zinc-800">
            <ChatPanel
              messages={messages}
              onSend={handleSendMessage}
              streaming={streaming}
            />
          </div>
          <div className="w-[55%]">
            <PreviewPanel files={files} messages={messages} />
          </div>
        </div>
      </div>
    </div>
  );
}
