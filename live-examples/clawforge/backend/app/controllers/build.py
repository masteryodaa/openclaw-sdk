"""Build controller — Pipeline and Supervisor orchestration."""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from openclaw_sdk import OpenClawClient
from openclaw_sdk.coordination.supervisor import Supervisor
from openclaw_sdk.pipeline.pipeline import Pipeline

from app.helpers import database

log = logging.getLogger(__name__)


async def stream_build(
    client: OpenClawClient,
    project_id: str,
    mode: str = "pipeline",
    agent_id: str = "main",
    max_steps: int = 5,
    max_cost_usd: float = 2.0,
) -> AsyncIterator[dict[str, str]]:
    """Stream build execution via SSE events."""
    log.info("stream_build project=%s mode=%s agent=%s", project_id[:8], mode, agent_id)

    project = await database.get_project(project_id)
    if not project:
        log.error("Project %s not found", project_id[:8])
        yield {
            "event": "build_error",
            "data": json.dumps({"message": "Project not found"}),
        }
        return

    description = project["description"]
    log.info("Build starting for %r (desc len=%d)", project["name"], len(description))
    yield {
        "event": "build_start",
        "data": json.dumps({"mode": mode, "project_id": project_id}),
    }

    try:
        if mode == "supervisor":
            log.info("Running supervisor mode")
            async for event in _run_supervisor(
                client, project_id, description, agent_id
            ):
                yield event
        else:
            log.info("Running pipeline mode")
            # Default to pipeline
            async for event in _run_pipeline(
                client, project_id, description, agent_id
            ):
                yield event

        await database.update_project(project_id, status="completed")
        log.info("Build complete project=%s", project_id[:8])
        yield {
            "event": "build_complete",
            "data": json.dumps({"project_id": project_id}),
        }

    except Exception as exc:
        log.error("Build failed project=%s: %s", project_id[:8], exc, exc_info=True)
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
    log.info("Pipeline: plan -> build -> review (agent=%s)", agent_id)
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

    log.info("Running pipeline.run()...")
    result = await pipeline.run(description=description)
    log.info(
        "Pipeline complete success=%s latency=%sms steps=%d",
        result.success, result.total_latency_ms, len(result.steps),
    )

    # Yield each step result
    for step_name, step_result in result.steps.items():
        content = step_result.content
        log.info(
            "Pipeline step=%s success=%s latency=%sms content_len=%d",
            step_name, step_result.success, step_result.latency_ms,
            len(content) if content else 0,
        )
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
            log.debug("Step %s tokens=%d", step_name, step_result.token_usage.total)
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
    log.info("Supervisor: agent=%s", agent_id)
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
    log.info("Delegating to supervisor...")
    result = await supervisor.delegate(task, strategy="sequential", max_rounds=1)
    log.info(
        "Supervisor complete success=%s delegations=%d latency=%sms",
        result.success, result.delegations, result.latency_ms,
    )

    # Save worker results
    for worker_id, worker_result in result.worker_results.items():
        content = worker_result.content
        log.info(
            "Supervisor worker=%s success=%s content_len=%d",
            worker_id, worker_result.success, len(content) if content else 0,
        )
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
