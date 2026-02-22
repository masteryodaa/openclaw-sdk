"""Build controller — Pipeline and Supervisor orchestration."""

from __future__ import annotations

import json
from typing import AsyncIterator

from openclaw_sdk import OpenClawClient
from openclaw_sdk.coordination.supervisor import Supervisor
from openclaw_sdk.pipeline.pipeline import Pipeline

from app.helpers import database


async def stream_build(
    client: OpenClawClient,
    project_id: str,
    mode: str = "pipeline",
    agent_id: str = "main",
    max_steps: int = 5,
    max_cost_usd: float = 2.0,
) -> AsyncIterator[dict[str, str]]:
    """Stream build execution via SSE events."""
    project = await database.get_project(project_id)
    if not project:
        yield {
            "event": "build_error",
            "data": json.dumps({"message": "Project not found"}),
        }
        return

    description = project["description"]
    yield {
        "event": "build_start",
        "data": json.dumps({"mode": mode, "project_id": project_id}),
    }

    try:
        if mode == "supervisor":
            async for event in _run_supervisor(
                client, project_id, description, agent_id
            ):
                yield event
        else:
            # Default to pipeline
            async for event in _run_pipeline(
                client, project_id, description, agent_id
            ):
                yield event

        await database.update_project(project_id, status="completed")
        yield {
            "event": "build_complete",
            "data": json.dumps({"project_id": project_id}),
        }

    except Exception as exc:
        await database.update_project(project_id, status="error")
        yield {
            "event": "build_error",
            "data": json.dumps({"message": str(exc)}),
        }


async def _run_pipeline(
    client: OpenClawClient,
    project_id: str,
    description: str,
    agent_id: str,
) -> AsyncIterator[dict[str, str]]:
    """Run a 3-step Pipeline: plan -> build -> review."""
    await database.update_project(project_id, status="building")

    pipeline = Pipeline(client)
    pipeline.add_step(
        "plan",
        agent_id,
        "You are a project planner. Create a detailed implementation plan for: {description}",
    )
    pipeline.add_step(
        "build",
        agent_id,
        "You are a software developer. Implement the following plan:\n{plan}",
    )
    pipeline.add_step(
        "review",
        agent_id,
        "You are a code reviewer. Review and improve the following implementation:\n{build}",
    )

    yield {
        "event": "step_start",
        "data": json.dumps({"step": "pipeline", "total_steps": 3}),
    }

    result = await pipeline.run(description=description)

    # Yield each step result
    for step_name, step_result in result.steps.items():
        content = step_result.content
        yield {
            "event": "step_complete",
            "data": json.dumps({
                "step": step_name,
                "success": step_result.success,
                "content": content[:500] if content else "",
                "latency_ms": step_result.latency_ms,
            }),
        }
        await database.add_message(
            project_id,
            "assistant",
            f"[{step_name}]\n{content}",
            thinking=step_result.thinking,
        )

        # Track token usage per step
        if step_result.token_usage and step_result.token_usage.total > 0:
            project = await database.get_project(project_id)
            if project:
                await database.update_project(
                    project_id,
                    total_tokens=project["total_tokens"]
                    + step_result.token_usage.total,
                )

    # Save final summary
    final_content = result.final_result.content if result.final_result else ""
    await database.add_message(
        project_id,
        "assistant",
        f"[Build Complete] success={result.success}\n{final_content[:1000]}",
    )

    yield {
        "event": "pipeline_summary",
        "data": json.dumps({
            "success": result.success,
            "total_latency_ms": result.total_latency_ms,
            "files_generated": len(result.all_files),
        }),
    }


async def _run_supervisor(
    client: OpenClawClient,
    project_id: str,
    description: str,
    agent_id: str,
) -> AsyncIterator[dict[str, str]]:
    """Run a Supervisor-based multi-agent build.

    Uses the same agent_id as multiple workers with different roles
    since in a single-agent OpenClaw setup, the agent handles all tasks.
    The Supervisor pattern demonstrates SDK coordination capabilities.
    """
    await database.update_project(project_id, status="building")

    supervisor = Supervisor(client, supervisor_agent_id=agent_id)
    supervisor.add_worker(agent_id, description="General-purpose builder")

    yield {
        "event": "step_start",
        "data": json.dumps({"step": "supervisor", "strategy": "sequential"}),
    }

    task = (
        f"Build the following project. Plan it, implement the code, "
        f"and review the result:\n\n{description}"
    )
    result = await supervisor.delegate(task, strategy="sequential", max_rounds=1)

    # Save worker results
    for worker_id, worker_result in result.worker_results.items():
        content = worker_result.content
        yield {
            "event": "step_complete",
            "data": json.dumps({
                "step": f"worker-{worker_id}",
                "success": worker_result.success,
                "content": content[:500] if content else "",
            }),
        }
        await database.add_message(
            project_id,
            "assistant",
            f"[supervisor:{worker_id}]\n{content}",
            thinking=worker_result.thinking,
        )

    # Save final result
    if result.final_result:
        await database.add_message(
            project_id,
            "assistant",
            f"[Supervisor Complete] success={result.success}\n"
            f"{result.final_result.content[:1000]}",
        )

    yield {
        "event": "supervisor_summary",
        "data": json.dumps({
            "success": result.success,
            "delegations": result.delegations,
            "latency_ms": result.latency_ms,
        }),
    }
