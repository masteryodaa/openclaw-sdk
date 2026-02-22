"""Pipeline & coordination endpoints — multi-step workflows and agent routing."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from openclaw_sdk.coordination.router import AgentRouter
from openclaw_sdk.coordination.supervisor import Supervisor
from openclaw_sdk.pipeline.pipeline import Pipeline
from openclaw_sdk.templates.registry import TEMPLATES, list_templates

from . import gateway

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


# ── Request models ──


class PipelineStep(BaseModel):
    name: str
    agent_id: str
    prompt: str
    output_key: str = ""


class RunPipelineBody(BaseModel):
    steps: list[PipelineStep]
    variables: dict[str, str] = {}


class SupervisorBody(BaseModel):
    task: str
    workers: list[dict[str, str]]  # [{agent_id, description}]
    strategy: str = "sequential"
    max_rounds: int = 3


class RouterBody(BaseModel):
    query: str
    routes: list[dict[str, str]]  # [{condition, agent_id}]
    default_agent_id: str | None = None


class BatchBody(BaseModel):
    agent_id: str
    queries: list[str]
    session: str = "batch"
    max_concurrency: int = 3


# ── Pipeline endpoints ──


@router.post("/run")
async def run_pipeline(body: RunPipelineBody):
    """Run a linear pipeline of agent steps."""
    client = await gateway.get_client()
    pipeline = Pipeline(client)
    for step in body.steps:
        pipeline.add_step(
            name=step.name,
            agent_id=step.agent_id,
            prompt=step.prompt,
            output_key=step.output_key or step.name,
        )
    result = await pipeline.run(**body.variables)
    outputs = {}
    for step_name, exec_result in result.steps.items():
        outputs[step_name] = exec_result.content
    return {
        "success": result.success,
        "outputs": outputs,
        "final": result.final_result.content if result.final_result else None,
        "total_latency_ms": result.total_latency_ms,
    }


# ── Coordination endpoints ──


@router.post("/supervisor")
async def run_supervisor(body: SupervisorBody):
    """Delegate a task to supervised workers."""
    client = await gateway.get_client()
    supervisor = Supervisor(client)
    for worker in body.workers:
        supervisor.add_worker(
            agent_id=worker["agent_id"],
            description=worker.get("description", ""),
        )
    result = await supervisor.delegate(
        task=body.task,
        strategy=body.strategy,
        max_rounds=body.max_rounds,
    )
    worker_data = {}
    for agent_id, exec_result in result.worker_results.items():
        worker_data[agent_id] = {
            "success": exec_result.success,
            "content": exec_result.content,
            "latency_ms": exec_result.latency_ms,
        }
    return {
        "success": result.success,
        "final_response": result.final_result.content if result.final_result else None,
        "workers": worker_data,
        "delegations": result.delegations,
        "latency_ms": result.latency_ms,
    }


@router.post("/router")
async def run_router(body: RouterBody):
    """Route a query to the best-matching agent.

    Each route's ``condition`` is a keyword string — if the keyword appears
    in the query (case-insensitive), that route matches.
    """
    client = await gateway.get_client()
    agent_router = AgentRouter(client)
    for route in body.routes:
        keyword = route["condition"].lower()
        agent_router.add_route(
            condition=lambda q, kw=keyword: kw in q.lower(),
            agent_id=route["agent_id"],
        )
    if body.default_agent_id:
        agent_router.set_default(body.default_agent_id)
    result = await agent_router.route(body.query)
    return {
        "success": result.success,
        "content": result.content,
        "latency_ms": result.latency_ms,
    }


# ── Batch execution ──


@router.post("/batch")
async def run_batch(body: BatchBody):
    """Execute multiple queries against an agent in parallel."""
    client = await gateway.get_client()
    agent = client.get_agent(body.agent_id, session_name=body.session)
    results = await agent.batch(
        queries=body.queries,
        max_concurrency=body.max_concurrency,
    )
    return {
        "results": [
            {
                "query": body.queries[i],
                "success": r.success,
                "content": r.content,
                "latency_ms": r.latency_ms,
            }
            for i, r in enumerate(results)
        ]
    }


# ── Templates ──


@router.get("/templates")
async def get_templates():
    """List available agent templates."""
    templates = list_templates()
    details = []
    for name in templates:
        tmpl = TEMPLATES[name]
        details.append({
            "name": name,
            "system_prompt": tmpl.get("system_prompt", "")[:120] + "...",
            "tool_policy": str(tmpl.get("tool_policy", "")),
            "channels": tmpl.get("channels", []),
        })
    return {"templates": details}


@router.post("/templates/create")
async def create_from_template(agent_id: str, template_name: str):
    """Create a new agent from a template."""
    client = await gateway.get_client()
    agent = await client.create_agent_from_template(template_name, agent_id)
    return {"agent_id": agent.agent_id, "template": template_name}
