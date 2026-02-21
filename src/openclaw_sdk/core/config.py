from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from openclaw_sdk.core.types import Attachment
from openclaw_sdk.mcp.server import HttpMcpServer, StdioMcpServer
from openclaw_sdk.skills.config import SkillsConfig
from openclaw_sdk.tools.policy import ToolPolicy


class ClientConfig(BaseModel):
    mode: Literal["local", "protocol", "openai_compat", "auto"] = "auto"
    openclaw_path: str = "openclaw"
    work_dir: Path = Path("./.openclaw")
    gateway_ws_url: str | None = None
    openai_base_url: str | None = None
    api_key: str | None = None
    timeout: int = Field(default=300, ge=1, le=3600)
    max_retries: int = Field(default=3, ge=0, le=10)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # Note: env var reading (OPENCLAW_* prefix) is handled by pydantic-settings in MD4


class AgentConfig(BaseModel):
    agent_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    name: str | None = None
    system_prompt: str = "You are a helpful assistant."
    llm_provider: Literal["anthropic", "openai", "gemini", "ollama"] = "anthropic"
    llm_model: str = "claude-sonnet-4-20250514"
    llm_api_key: str | None = None
    channels: list[str] = Field(default_factory=list)
    enable_memory: bool = True
    memory_backend: Literal["memory", "redis"] = "memory"
    permission_mode: Literal["accept", "confirm", "reject"] = "accept"
    tool_policy: ToolPolicy | None = None
    mcp_servers: dict[str, StdioMcpServer | HttpMcpServer] | None = None
    skills: SkillsConfig | None = None

    def to_openclaw_agent(self) -> dict[str, Any]:
        """Serialize to OpenClaw's native agent config JSON structure."""
        result: dict[str, Any] = {}
        if self.name:
            result["name"] = self.name
        if self.system_prompt != "You are a helpful assistant.":
            result["systemPrompt"] = self.system_prompt
        if self.tool_policy is not None:
            result["tools"] = self.tool_policy.to_openclaw()
        if self.mcp_servers:
            result["mcpServers"] = {
                name: server.to_openclaw()
                for name, server in self.mcp_servers.items()
            }
        if self.skills is not None:
            skills_data = self.skills.to_openclaw()
            if skills_data:
                result["skills"] = skills_data
        return result


class ExecutionOptions(BaseModel):
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    stream: bool = False
    max_tool_calls: int = Field(default=50, ge=1, le=200)
    attachments: list[Attachment | str | Path] = Field(default_factory=list)
