"""Audit event data models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """An immutable record of a notable action within the SDK.

    Every gateway call, config change, authentication attempt, or other
    auditable operation can be captured as an :class:`AuditEvent` and
    dispatched to one or more :class:`~openclaw_sdk.audit.sinks.AuditSink`
    implementations.
    """

    event_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    event_type: str
    """Category of the event, e.g. ``"execute"``, ``"config_change"``, ``"auth"``."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: str | None = None
    user_id: str | None = None
    tenant_id: str | None = None
    action: str = ""
    resource: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error: str | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
