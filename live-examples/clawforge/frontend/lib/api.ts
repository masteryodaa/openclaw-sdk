import type { Project, Template, BillingSummary, GeneratedFile } from "./types";

interface ChatResponse {
  success: boolean;
  content: string;
  thinking: string | null;
  tool_calls: unknown[];
  files: unknown[];
  token_usage: unknown;
  stop_reason: string | null;
  error_message: string | null;
  latency_ms: number;
  message_id: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8200";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || res.statusText);
  }
  return res.json();
}

// Projects
export const listProjects = () => fetchAPI<Project[]>("/api/projects");
export const createProject = (description: string, name?: string, template?: string) =>
  fetchAPI<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify({ description, name: name || "", template }),
  });
export const getProject = (id: string) => fetchAPI<Project>(`/api/projects/${id}`);
export const deleteProject = (id: string) =>
  fetchAPI<{ deleted: boolean }>(`/api/projects/${id}`, { method: "DELETE" });

// Chat
export const sendChat = (projectId: string, message: string, agentId = "main", thinking = false) =>
  fetchAPI<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, message, agent_id: agentId, thinking }),
  });

// Templates
export const listTemplates = () => fetchAPI<Template[]>("/api/templates");
export const createFromTemplate = (templateId: string, name?: string) =>
  fetchAPI<Project>("/api/templates/create", {
    method: "POST",
    body: JSON.stringify({ template_id: templateId, name: name || "" }),
  });

// Billing
export const getBillingSummary = () => fetchAPI<BillingSummary>("/api/billing/summary");

// Files
export const getProjectFiles = (projectId: string) =>
  fetchAPI<GeneratedFile[]>(`/api/files/${projectId}`);

// Workspace files (from OpenClaw's agent workspace)
export const readWorkspaceFile = async (path: string): Promise<string> => {
  const res = await fetch(`${API_URL}/api/files/workspace/${path}`);
  if (!res.ok) throw new Error(`Failed to read workspace file: ${res.status}`);
  return res.text();
};

/** Persist a workspace file to the project's generated_files DB record. Idempotent. */
export const saveWorkspaceRecord = (projectId: string, path: string) =>
  fetchAPI<GeneratedFile>(
    `/api/files/workspace-record/${projectId}?path=${encodeURIComponent(path)}`,
    { method: "POST" },
  );

// Session status (real-time tool activity polling)
export interface SessionTool { tool: string; phase: string; output?: string }
export interface SessionFile { path: string; size: number }
export interface SessionStatus { tools: SessionTool[]; files: SessionFile[]; error?: string }

export const getSessionStatus = (projectId: string, agentId = "main") =>
  fetchAPI<SessionStatus>(`/api/chat/session-status/${projectId}?agent_id=${agentId}`);

// Framework app build (npm install + npm run build / vite build --base=./)
export interface NpmBuildResult {
  success: boolean;
  index_path: string;   // e.g. "erp-dashboard/dist/index.html"
  preview_url: string;  // e.g. "/workspace-site/erp-dashboard/dist/index.html"
  output: string;
}

export const buildWorkspaceApp = (directory: string) =>
  fetchAPI<NpmBuildResult>("/api/build/workspace-npm", {
    method: "POST",
    body: JSON.stringify({ directory }),
  });

/** Returns the full URL to a workspace file served via the backend.
 *  Use this for iframe src= so it works for remote gateways too. */
export const workspaceSiteUrl = (path: string) => `${API_URL}/workspace-site/${path}`;
