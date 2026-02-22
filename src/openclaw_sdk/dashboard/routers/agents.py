"""Agent endpoints — execute queries and check status."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from openclaw_sdk.core.exceptions import OpenClawError

router = APIRouter(tags=["agents"])


class _ExecuteBody(BaseModel):
    query: str
    session_name: str = "main"
    timeout_seconds: int = 300


@router.post("/api/agents/{agent_id}/execute")
async def execute_agent(agent_id: str, body: _ExecuteBody, request: Request) -> JSONResponse:
    """Execute a query against an agent."""
    client = request.app.state.client
    agent = client.get_agent(agent_id, body.session_name)
    try:
        from openclaw_sdk.core.config import ExecutionOptions

        options = ExecutionOptions(timeout_seconds=body.timeout_seconds)
        result = await agent.execute(body.query, options=options)
    except OpenClawError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content={
        "success": result.success,
        "content": result.content,
        "latency_ms": result.latency_ms,
    })


@router.get("/api/agents/{agent_id}/status")
async def agent_status(agent_id: str, request: Request) -> JSONResponse:
    """Get current agent status."""
    client = request.app.state.client
    agent = client.get_agent(agent_id)
    try:
        status = await agent.get_status()
    except OpenClawError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content={"agent_id": agent_id, "status": status.value})
