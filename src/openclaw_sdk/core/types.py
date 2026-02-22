from __future__ import annotations

import base64
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from openclaw_sdk.core.constants import AgentStatus, EventType


class Attachment(BaseModel):
    """A file attachment sent with a query.

    The gateway accepts **any MIME type** and **any file size** within its
    WebSocket frame limit.  The SDK does not impose its own restrictions —
    the gateway is the authority.

    **Verified against OpenClaw 2026.2.3-1 (2026-02-23):**

    - All MIME types accepted (no server-side allowlist)
    - Gateway ``maxPayload`` = 512 KiB per WS frame (~380 KB raw after
      base64 + JSON overhead).  Oversized frames cause a WS disconnect
      which surfaces as a connection error.

    Use :meth:`from_path` to create from a local file with auto-detected
    MIME type, or construct directly with ``content_base64`` to skip file I/O.
    """

    file_path: str
    mime_type: str | None = None
    name: str | None = None
    content_base64: str | None = None

    def to_gateway(self) -> dict[str, Any]:
        """Serialize this attachment to the gateway ``chat.send`` payload format.

        If ``content_base64`` is set, uses it directly; otherwise reads
        ``file_path`` and base64-encodes its contents.

        Returns:
            Dict with keys ``type``, ``mimeType``, ``fileName``, ``content``.

        Raises:
            ValueError: If the MIME type cannot be determined.
            FileNotFoundError: If ``file_path`` does not exist and no
                ``content_base64`` was provided.
        """
        # Resolve MIME type: explicit > guessed from extension
        resolved_mime = self.mime_type
        if resolved_mime is None:
            guessed, _ = mimetypes.guess_type(self.file_path)
            resolved_mime = guessed

        if resolved_mime is None:
            raise ValueError(
                f"Cannot determine mime type for '{self.file_path}'. "
                f"Please specify mime_type explicitly."
            )

        # Resolve content
        if self.content_base64 is not None:
            b64_content = self.content_base64
        else:
            path = Path(self.file_path)
            raw = path.read_bytes()
            b64_content = base64.b64encode(raw).decode("ascii")

        # Resolve file name
        file_name = self.name or Path(self.file_path).name

        return {
            "type": resolved_mime,
            "mimeType": resolved_mime,
            "fileName": file_name,
            "content": b64_content,
        }

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        mime_type: str | None = None,
    ) -> Attachment:
        """Create an :class:`Attachment` from a local file path.

        Auto-detects MIME type from the file extension if *mime_type* is not
        provided.

        Args:
            path: Path to the file.
            mime_type: Explicit MIME type override.

        Returns:
            A new :class:`Attachment` instance.
        """
        p = Path(path)
        if mime_type is None:
            guessed, _ = mimetypes.guess_type(str(p))
            mime_type = guessed
        return cls(
            file_path=str(p),
            mime_type=mime_type,
            name=p.name,
        )


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
    cache_read: int = Field(default=0, alias="cacheRead")
    cache_write: int = Field(default=0, alias="cacheWrite")
    total_tokens: int = Field(default=0, alias="totalTokens")

    model_config = {"populate_by_name": True}

    @classmethod
    def from_gateway(cls, data: dict[str, Any]) -> TokenUsage:
        """Create from gateway response data with camelCase field names."""
        input_val = data.get("input", 0)
        output_val = data.get("output", 0)
        total_val = data.get("totalTokens", 0) or (input_val + output_val)
        return cls.model_validate({
            "input": input_val,
            "output": output_val,
            "cacheRead": data.get("cacheRead", 0),
            "cacheWrite": data.get("cacheWrite", 0),
            "totalTokens": total_val,
        })

    @property
    def total(self) -> int:
        """Total tokens: uses total_tokens if non-zero, else input + output."""
        return self.total_tokens if self.total_tokens > 0 else self.input + self.output


class ContentBlock(BaseModel):
    """A single content block from polymorphic gateway responses."""

    type: str
    text: str | None = None
    thinking: str | None = None

    @property
    def value(self) -> str:
        """Return the first non-None text value."""
        return self.text or self.thinking or ""


class ExecutionResult(BaseModel):
    success: bool
    content: str
    content_blocks: list[ContentBlock] = Field(default_factory=list)
    files: list[GeneratedFile] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    thinking: str | None = None
    latency_ms: int = 0
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    stop_reason: str | None = None
    """Stop reason: ``"complete"``, ``"aborted"``, ``"error"``, ``"timeout"``."""
    error_message: str | None = None
    """Error details when the agent or LLM failed (e.g. rate-limit, auth error)."""

    @property
    def has_files(self) -> bool:
        return len(self.files) > 0


class StreamEvent(BaseModel):
    event_type: EventType
    data: dict[str, Any]


# ---------------------------------------------------------------------------
# Typed stream events — strongly-typed alternatives to raw StreamEvent
# ---------------------------------------------------------------------------


class TypedStreamEvent(BaseModel):
    """Base class for typed stream events.

    Subclasses provide typed fields for each gateway event kind, replacing
    the raw ``data: dict`` pattern.  Use with :meth:`Agent.execute_stream_typed`.
    """

    event_type: EventType


class ContentEvent(TypedStreamEvent):
    """A content chunk from the agent."""

    event_type: EventType = EventType.CONTENT
    text: str = ""


class ThinkingEvent(TypedStreamEvent):
    """A thinking/reasoning chunk from the agent."""

    event_type: EventType = EventType.THINKING
    thinking: str = ""


class ToolCallEvent(TypedStreamEvent):
    """The agent is invoking a tool."""

    event_type: EventType = EventType.TOOL_CALL
    tool: str = ""
    input: str = ""


class ToolResultEvent(TypedStreamEvent):
    """The result from a tool invocation."""

    event_type: EventType = EventType.TOOL_RESULT
    tool: str = ""
    output: str = ""
    duration_ms: int = 0


class FileEvent(TypedStreamEvent):
    """A file generated by the agent."""

    event_type: EventType = EventType.FILE_GENERATED
    name: str = ""
    path: str = ""
    size_bytes: int = 0
    mime_type: str = "application/octet-stream"


class DoneEvent(TypedStreamEvent):
    """Agent execution completed."""

    event_type: EventType = EventType.DONE
    content: str = ""
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    stop_reason: str = "complete"


class ErrorEvent(TypedStreamEvent):
    """Agent execution error."""

    event_type: EventType = EventType.ERROR
    message: str = ""


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
