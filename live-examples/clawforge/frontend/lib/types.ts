export interface Project {
  id: string;
  name: string;
  description: string;
  status: string;
  template: string | null;
  created_at: string;
  updated_at: string;
  total_cost_usd: number;
  total_tokens: number;
  plan_json: Record<string, unknown> | null;
  messages?: ChatMessage[];
  files?: GeneratedFile[];
}

export interface ChatMessage {
  id: string;
  project_id: string;
  role: "user" | "assistant";
  content: string;
  thinking: string | null;
  tool_calls: ToolCall[] | null;
  files: FileRef[] | null;
  token_usage: TokenUsage | null;
  cost_usd: number;
  created_at: string;
}

export interface ToolCall {
  tool: string;
  input: string;
  output?: string;
}

export interface FileRef {
  name: string;
  path: string;
  size: number;
  mimeType: string;
}

export interface TokenUsage {
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  inputTokens?: number;
  outputTokens?: number;
  totalTokens?: number;
}

export interface GeneratedFile {
  id: string;
  project_id: string;
  name: string;
  path: string;
  content: string;
  size_bytes: number;
  mime_type: string;
  created_at: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  difficulty: string;
  tags: string[];
  sdk_template: string;
}

export interface BillingSummary {
  total_cost_usd: number;
  total_tokens: number;
  project_count: number;
  projects: ProjectBilling[];
}

export interface ProjectBilling {
  project_id: string;
  project_name: string;
  total_cost_usd: number;
  total_tokens: number;
  message_count: number;
}

export interface BuildStepEvent {
  step: string;
  status: string;
  content: string;
  metadata?: Record<string, unknown>;
}
