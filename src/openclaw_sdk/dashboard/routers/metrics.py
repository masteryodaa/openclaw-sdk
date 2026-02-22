"""Metrics endpoints — cost tracking summary."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["metrics"])


@router.get("/api/metrics/costs")
async def cost_summary(request: Request) -> JSONResponse:
    """Return cost summary from the CostTracker (if provided)."""
    cost_tracker = request.app.state.cost_tracker
    if cost_tracker is None:
        raise HTTPException(status_code=404, detail="CostTracker not configured")
    summary = cost_tracker.get_summary()
    return JSONResponse(content=summary.model_dump())
