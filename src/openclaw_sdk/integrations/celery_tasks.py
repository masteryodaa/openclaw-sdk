"""Celery integration for OpenClaw SDK.

Requires: ``pip install openclaw-sdk[celery]``

Usage::

    from openclaw_sdk.integrations.celery_tasks import create_execute_task

    execute_agent = create_execute_task(app, client)
    execute_agent.delay("research-bot", "Find AI trends")
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openclaw_sdk.core.client import OpenClawClient


def create_execute_task(celery_app: Any, client: OpenClawClient) -> Any:
    """Create a Celery task for agent execution.

    Returns a Celery task that can be called with .delay() or .apply_async().
    """
    try:
        import celery  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Celery is required. Install with: pip install openclaw-sdk[celery]"
        ) from exc

    import asyncio

    @celery_app.task(name="openclaw.execute")
    def execute_agent(agent_id: str, query: str) -> dict[str, Any]:
        """Execute an agent query as a Celery task."""
        loop = asyncio.new_event_loop()
        try:
            agent = client.get_agent(agent_id)
            result = loop.run_until_complete(agent.execute(query))
            return {
                "success": result.success,
                "content": result.content,
                "latency_ms": result.latency_ms,
                "token_usage": {
                    "input": result.token_usage.input,
                    "output": result.token_usage.output,
                },
            }
        finally:
            loop.close()

    return execute_agent


def create_batch_task(celery_app: Any, client: OpenClawClient) -> Any:
    """Create a Celery task for batch agent execution."""
    try:
        import celery  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Celery is required. Install with: pip install openclaw-sdk[celery]"
        ) from exc

    import asyncio

    @celery_app.task(name="openclaw.batch")
    def batch_execute(agent_id: str, queries: list[str]) -> list[dict[str, Any]]:
        """Execute multiple queries as a Celery task."""
        loop = asyncio.new_event_loop()
        try:
            agent = client.get_agent(agent_id)
            results = loop.run_until_complete(agent.batch(queries))
            return [
                {
                    "success": r.success,
                    "content": r.content,
                    "latency_ms": r.latency_ms,
                }
                for r in results
            ]
        finally:
            loop.close()

    return batch_execute
