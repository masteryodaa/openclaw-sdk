"""Audit log query endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["audit"])


@router.get("/api/audit")
async def query_audit(
    request: Request,
    event_type: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> JSONResponse:
    """Query audit log entries with optional filters."""
    audit_logger = request.app.state.audit_logger
    if audit_logger is None:
        raise HTTPException(status_code=404, detail="AuditLogger not configured")
    events = await audit_logger.query(
        event_type=event_type,
        agent_id=agent_id,
        limit=limit,
    )
    return JSONResponse(content=[e.model_dump(mode="json") for e in events])
