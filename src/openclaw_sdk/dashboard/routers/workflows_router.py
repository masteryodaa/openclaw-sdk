"""Workflow preset endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["workflows"])

# Available preset names and their required arguments.
_PRESET_INFO: dict[str, dict[str, Any]] = {
    "review": {
        "description": "Code/document review workflow",
        "required_args": ["reviewer_agent_id", "author_agent_id"],
    },
    "research": {
        "description": "Research-and-summarize workflow",
        "required_args": ["researcher_agent_id", "summarizer_agent_id"],
    },
    "support": {
        "description": "Customer support triage workflow",
        "required_args": ["triage_agent_id", "support_agent_id"],
    },
}


class _RunPresetBody(BaseModel):
    args: dict[str, str] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


@router.get("/api/workflows/presets")
async def list_presets(request: Request) -> JSONResponse:
    """List available workflow presets."""
    return JSONResponse(content=_PRESET_INFO)


@router.post("/api/workflows/{preset}/run")
async def run_preset(preset: str, body: _RunPresetBody, request: Request) -> JSONResponse:
    """Run a preset workflow.

    Pass ``args`` to configure agent IDs and ``context`` for the initial
    workflow context (e.g. ``{"document": "..."}``).
    """
    if preset not in _PRESET_INFO:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown preset '{preset}'. Available: {list(_PRESET_INFO)}",
        )

    from openclaw_sdk.workflows.presets import (
        research_workflow,
        review_workflow,
        support_workflow,
    )

    info = _PRESET_INFO[preset]
    missing = [a for a in info["required_args"] if a not in body.args]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required args: {missing}",
        )

    if preset == "review":
        workflow = review_workflow(
            body.args["reviewer_agent_id"], body.args["author_agent_id"]
        )
    elif preset == "research":
        workflow = research_workflow(
            body.args["researcher_agent_id"], body.args["summarizer_agent_id"]
        )
    else:
        workflow = support_workflow(
            body.args["triage_agent_id"], body.args["support_agent_id"]
        )

    client = request.app.state.client
    result = await workflow.run(
        body.context,
        agent_factory=lambda agent_id: client.get_agent(agent_id),
    )
    steps_executed = sum(
        1 for s in result.steps if s.status.value in ("completed", "failed")
    )
    return JSONResponse(content={
        "success": result.success,
        "steps_executed": steps_executed,
        "final_output": str(result.final_output) if result.final_output else None,
        "latency_ms": result.latency_ms,
    })
