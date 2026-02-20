from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from openclaw_sdk.core.constants import AgentStatus, EventType


class Attachment(BaseModel):
    """A file attachment sent with a query. Any file type: images, PDFs, audio, video, CSVs, etc."""

    file_path: str
    mime_type: str | None = None
    name: str | None = None


class ToolCall(BaseModel):
    tool: str
    input: str
    output: str | None = None
    duration_ms: int | None = None


class GeneratedFile(BaseModel):
    name: str
    path: str
    size_bytes: int
    mime_type: str


class TokenUsage(BaseModel):
    input: int = 0
    output: int = 0


class ExecutionResult(BaseModel):
    success: bool
    content: str
    files: list[GeneratedFile] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    thinking: str | None = None
    latency_ms: int = 0
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def has_files(self) -> bool:
        return len(self.files) > 0


class StreamEvent(BaseModel):
    event_type: EventType
    data: dict[str, Any]


class AgentSummary(BaseModel):
    agent_id: str
    name: str | None = None
    status: AgentStatus


class HealthStatus(BaseModel):
    healthy: bool
    latency_ms: float | None = None
    version: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class SessionInfo(BaseModel):
    """Real session object shape from the OpenClaw gateway."""

    key: str  # e.g. "agent:main:main"
    kind: str | None = None
    chat_type: str | None = Field(default=None, alias="chatType")
    session_id: str | None = Field(default=None, alias="sessionId")
    updated_at: int | None = Field(default=None, alias="updatedAt")
    system_sent: bool | None = Field(default=None, alias="systemSent")
    aborted_last_run: bool | None = Field(default=None, alias="abortedLastRun")
    input_tokens: int | None = Field(default=None, alias="inputTokens")
    output_tokens: int | None = Field(default=None, alias="outputTokens")
    total_tokens: int | None = Field(default=None, alias="totalTokens")
    model_provider: str | None = Field(default=None, alias="modelProvider")
    model: str | None = None
    context_tokens: int | None = Field(default=None, alias="contextTokens")
    delivery_context: dict[str, Any] | None = Field(default=None, alias="deliveryContext")
    last_channel: str | None = Field(default=None, alias="lastChannel")

    model_config = {"populate_by_name": True}
