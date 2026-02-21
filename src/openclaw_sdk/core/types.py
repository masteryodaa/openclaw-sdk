from __future__ import annotations

import base64
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from openclaw_sdk.core.constants import AgentStatus, EventType


class Attachment(BaseModel):
    """A file attachment sent with a query.

    OpenClaw supports image attachments only (JPEG, PNG, GIF, WebP, SVG).
    Maximum file size is 5 MB.

    Use :meth:`from_path` to create from a local file with auto-detected MIME type,
    or construct directly with ``content_base64`` to skip file I/O.
    """

    file_path: str
    mime_type: str | None = None
    name: str | None = None
    content_base64: str | None = None

    MAX_SIZE_BYTES: ClassVar[int] = 5 * 1024 * 1024
    ALLOWED_MIME_TYPES: ClassVar[frozenset[str]] = frozenset({
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
    })

    def to_gateway(self) -> dict[str, Any]:
        """Serialize this attachment to the gateway ``chat.send`` payload format.

        Validates file size (<= 5 MB) and MIME type (images only).
        If ``content_base64`` is set, uses it directly; otherwise reads
        ``file_path`` and base64-encodes its contents.

        Returns:
            Dict with keys ``type``, ``mimeType``, ``fileName``, ``content``.

        Raises:
            ValueError: If the file exceeds 5 MB or has a disallowed MIME type.
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

        if resolved_mime not in self.ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Unsupported mime type '{resolved_mime}'. "
                f"Allowed: {sorted(self.ALLOWED_MIME_TYPES)}"
            )

        # Resolve content
        if self.content_base64 is not None:
            b64_content = self.content_base64
        else:
            path = Path(self.file_path)
            raw = path.read_bytes()
            if len(raw) > self.MAX_SIZE_BYTES:
                raise ValueError(
                    f"File '{self.file_path}' is {len(raw)} bytes, "
                    f"exceeding the 5 MB limit ({self.MAX_SIZE_BYTES} bytes)."
                )
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
