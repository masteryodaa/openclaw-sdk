"""Workflow endpoints — preset workflows and workflow execution."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from openclaw_sdk.workflows import (
    Workflow,
    WorkflowStep,
    StepType,
    review_workflow,
    research_workflow,
    support_workflow,
)

from . import gateway

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

# Track running workflow status
_workflow_status: dict[str, dict[str, Any]] = {}

# Preset registry
WORKFLOW_PRESETS = {
    "review": {
        "name": "Code Review",
        "description": "Review code/documents with automated feedback and revision cycle",
        "required_params": ["reviewer_agent_id", "author_agent_id"],
        "context_keys": ["document"],
    },
    "research": {
        "name": "Research & Summarize",
        "description": "Research a topic, extract findings, and produce a summary",
        "required_params": ["researcher_agent_id", "summarizer_agent_id"],
        "context_keys": ["topic"],
    },
    "support": {
        "name": "Customer Support Triage",
        "description": "Triage support requests by priority with detailed follow-up",
        "required_params": ["triage_agent_id", "support_agent_id"],
        "context_keys": ["request"],
    },
}


# -- Request models --


class RunWorkflowBody(BaseModel):
    preset: str
    agent_ids: dict[str, str]  # Maps param name to agent_id
    context: dict[str, Any] = {}


# -- Endpoints --


@router.get("/presets")
async def list_presets():
    """List available preset workflows."""
    presets = []
    for key, info in WORKFLOW_PRESETS.items():
        presets.append({
            "key": key,
            "name": info["name"],
            "description": info["description"],
            "required_params": info["required_params"],
            "context_keys": info["context_keys"],
        })
    return {"presets": presets}


@router.post("/run")
async def run_workflow(body: RunWorkflowBody):
    """Run a preset workflow with the given agent IDs and context."""
    if body.preset not in WORKFLOW_PRESETS:
        available = ", ".join(sorted(WORKFLOW_PRESETS))
        return {"error": f"Unknown preset '{body.preset}'. Available: {available}"}

    client = await gateway.get_client()

    # Build the workflow from preset
    if body.preset == "review":
        reviewer = body.agent_ids.get("reviewer_agent_id", "")
        author = body.agent_ids.get("author_agent_id", "")
        if not reviewer or not author:
            return {"error": "reviewer_agent_id and author_agent_id are required"}
        wf = review_workflow(reviewer, author)
    elif body.preset == "research":
        researcher = body.agent_ids.get("researcher_agent_id", "")
        summarizer = body.agent_ids.get("summarizer_agent_id", "")
        if not researcher or not summarizer:
            return {"error": "researcher_agent_id and summarizer_agent_id are required"}
        wf = research_workflow(researcher, summarizer)
    elif body.preset == "support":
        triage = body.agent_ids.get("triage_agent_id", "")
        support = body.agent_ids.get("support_agent_id", "")
        if not triage or not support:
            return {"error": "triage_agent_id and support_agent_id are required"}
        wf = support_workflow(triage, support)
    else:
        return {"error": f"Unhandled preset: {body.preset}"}

    # Factory to create agents
    def agent_factory(agent_id: str):
        return client.get_agent(agent_id)

    _workflow_status[body.preset] = {"status": "running", "workflow": wf.name}

    try:
        result = await wf.run(dict(body.context), agent_factory=agent_factory)
        _workflow_status[body.preset] = {
            "status": "completed" if result.success else "failed",
            "workflow": wf.name,
        }
        return {
            "success": result.success,
            "workflow": wf.name,
            "final_output": result.final_output,
            "latency_ms": result.latency_ms,
            "steps": [
                {
                    "name": s.name,
                    "step_type": s.step_type,
                    "status": s.status,
                    "result": s.result,
                }
                for s in result.steps
            ],
        }
    except Exception as exc:
        _workflow_status[body.preset] = {
            "status": "error",
            "workflow": wf.name,
            "error": str(exc),
        }
        return {"error": str(exc)}


@router.get("/status")
async def get_workflow_status():
    """Get the status of recently run workflows."""
    return {"workflows": _workflow_status}
