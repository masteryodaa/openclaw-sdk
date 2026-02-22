"""Audit logging endpoints — query, log, and manage audit events."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from openclaw_sdk.audit import AuditLogger, AuditEvent, InMemoryAuditSink

from . import gateway

router = APIRouter(prefix="/api/audit", tags=["audit"])

# Shared singleton instance (per-server lifetime)
_audit_sink = InMemoryAuditSink()
_audit_logger = AuditLogger(sinks=[_audit_sink])


# -- Request models --


class LogEventBody(BaseModel):
    event_type: str
    agent_id: str | None = None
    action: str = ""
    resource: str = ""
    details: dict[str, Any] = {}
    success: bool = True
    error: str | None = None


# -- Endpoints --


@router.get("/events")
async def query_events(
    agent_id: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
):
    """Query audit events with optional filters."""
    events = await _audit_logger.query(
        event_type=event_type,
        agent_id=agent_id,
        limit=limit,
    )
    return {
        "events": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "timestamp": e.timestamp.isoformat(),
                "agent_id": e.agent_id,
                "action": e.action,
                "resource": e.resource,
                "success": e.success,
                "error": e.error,
                "latency_ms": e.latency_ms,
                "cost_usd": e.cost_usd,
                "details": e.details,
            }
            for e in events
        ],
        "count": len(events),
    }


@router.get("/events/count")
async def count_events(
    agent_id: str | None = None,
    event_type: str | None = None,
):
    """Count audit events matching the given filters."""
    events = await _audit_logger.query(
        event_type=event_type,
        agent_id=agent_id,
        limit=10000,
    )
    return {"count": len(events)}


@router.post("/events")
async def log_event(body: LogEventBody):
    """Manually log an audit event."""
    event = AuditEvent(
        event_type=body.event_type,
        agent_id=body.agent_id,
        action=body.action,
        resource=body.resource,
        details=body.details,
        success=body.success,
        error=body.error,
    )
    await _audit_logger.log(event)
    return {
        "logged": True,
        "event_id": event.event_id,
        "timestamp": event.timestamp.isoformat(),
    }


@router.delete("/events")
async def clear_events():
    """Clear all in-memory audit events."""
    _audit_sink._events.clear()
    return {"cleared": True}


# -- Expose singleton for integration --


def get_audit_logger() -> AuditLogger:
    """Get the shared AuditLogger instance."""
    return _audit_logger
