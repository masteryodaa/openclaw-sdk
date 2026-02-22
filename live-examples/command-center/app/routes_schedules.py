"""Schedule / cron management endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from openclaw_sdk import ScheduleConfig

from . import gateway

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


class CreateScheduleBody(BaseModel):
    name: str
    cron: str
    agent_id: str
    message: str
    session_name: str = "main"
    enabled: bool = True


class UpdateScheduleBody(BaseModel):
    patch: dict


@router.get("")
async def list_schedules():
    """List all cron jobs."""
    client = await gateway.get_client()
    jobs = await client.scheduling.list_schedules()
    return {"schedules": [j.model_dump() for j in jobs]}


@router.get("/status")
async def cron_status():
    """Get cron scheduler status."""
    client = await gateway.get_client()
    return await client.scheduling.cron_status()


@router.post("")
async def create_schedule(body: CreateScheduleBody):
    """Create a new cron job."""
    client = await gateway.get_client()
    config = ScheduleConfig(
        name=body.name,
        cron=body.cron,
        agent_id=body.agent_id,
        message=body.message,
        session_name=body.session_name,
        enabled=body.enabled,
    )
    job = await client.scheduling.create_schedule(config)
    return {"success": True, "job": job.model_dump()}


@router.patch("/{job_id}")
async def update_schedule(job_id: str, body: UpdateScheduleBody):
    """Update a cron job."""
    client = await gateway.get_client()
    result = await client.scheduling.update_schedule(job_id, body.patch)
    return {"success": True, "result": result}


@router.delete("/{job_id}")
async def delete_schedule(job_id: str):
    """Delete a cron job."""
    client = await gateway.get_client()
    result = await client.scheduling.delete_schedule(job_id)
    return {"success": result}


@router.post("/{job_id}/run")
async def run_now(job_id: str):
    """Trigger a cron job immediately."""
    client = await gateway.get_client()
    result = await client.scheduling.run_now(job_id)
    return {"success": True, "result": result}


@router.get("/{job_id}/runs")
async def get_runs(job_id: str):
    """Get run history for a cron job."""
    client = await gateway.get_client()
    return {"runs": await client.scheduling.get_runs(job_id)}
