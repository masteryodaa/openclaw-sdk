"""Schedule management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from openclaw_sdk.core.exceptions import OpenClawError

router = APIRouter(tags=["schedules"])


@router.get("/api/schedules")
async def list_schedules(request: Request) -> JSONResponse:
    """List all scheduled cron jobs."""
    client = request.app.state.client
    try:
        jobs = await client.scheduling.list_schedules()
    except OpenClawError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content=[j.model_dump() for j in jobs])


@router.delete("/api/schedules/{job_id}")
async def delete_schedule(job_id: str, request: Request) -> JSONResponse:
    """Delete a schedule by job ID."""
    client = request.app.state.client
    try:
        await client.scheduling.delete_schedule(job_id)
    except OpenClawError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content={"deleted": True})
