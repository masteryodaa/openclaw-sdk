from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


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
    tools: list[str] = Field(default_factory=list)
    tool_config: dict[str, dict[str, Any]] = Field(default_factory=dict)
    channels: list[str] = Field(default_factory=list)
    enable_memory: bool = True
    memory_backend: Literal["memory", "redis"] = "memory"
    permission_mode: Literal["accept", "confirm", "reject"] = "accept"


class ExecutionOptions(BaseModel):
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    stream: bool = False
    max_tool_calls: int = Field(default=50, ge=1, le=200)
    attachments: list[str | Path] = Field(default_factory=list)
