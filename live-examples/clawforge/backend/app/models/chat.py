"""Chat-related Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    project_id: str
    message: str
    agent_id: str = "main"
    session_name: str | None = None
    thinking: bool = False
    timeout_seconds: int = 300


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    thinking: str | None = None
    tool_calls: list[dict] | None = None
    files: list[dict] | None = None
    token_usage: dict | None = None
    cost_usd: float = 0
    created_at: str
