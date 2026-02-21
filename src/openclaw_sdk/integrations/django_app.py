"""Django integration for OpenClaw SDK.

Requires: ``pip install openclaw-sdk[django]``
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openclaw_sdk.core.client import OpenClawClient


_client: OpenClawClient | None = None


def setup(client: OpenClawClient) -> None:
    """Initialize the Django integration with an OpenClawClient."""
    global _client  # noqa: PLW0603
    _client = client


def get_client() -> OpenClawClient:
    """Get the configured OpenClawClient instance."""
    if _client is None:
        raise RuntimeError(
            "OpenClaw Django integration not configured. "
            "Call openclaw_sdk.integrations.django_app.setup(client) first."
        )
    return _client


def get_urls() -> list[Any]:
    """Return Django URL patterns for OpenClaw endpoints.

    Usage in urls.py::

        from openclaw_sdk.integrations.django_app import get_urls
        urlpatterns += get_urls()
    """
    try:
        from django.http import JsonResponse
        from django.urls import path
        from django.views.decorators.csrf import csrf_exempt
        from django.views.decorators.http import require_GET, require_POST
    except ImportError as exc:
        raise ImportError(
            "Django is required. Install with: pip install openclaw-sdk[django]"
        ) from exc

    import asyncio
    import json

    @require_GET
    def health(request: Any) -> Any:
        client = get_client()
        loop = asyncio.new_event_loop()
        try:
            status = loop.run_until_complete(client.health())
            return JsonResponse({"healthy": status.healthy, "version": status.version})
        finally:
            loop.close()

    @csrf_exempt
    @require_POST
    def execute(request: Any, agent_id: str) -> Any:
        client = get_client()
        data = json.loads(request.body) if request.body else {}
        query = data.get("query", "")
        loop = asyncio.new_event_loop()
        try:
            agent = client.get_agent(agent_id)
            result = loop.run_until_complete(agent.execute(query))
            return JsonResponse({
                "success": result.success,
                "content": result.content,
                "latency_ms": result.latency_ms,
            })
        finally:
            loop.close()

    return [
        path("openclaw/health/", health, name="openclaw-health"),
        path("openclaw/agents/<str:agent_id>/execute/", execute, name="openclaw-execute"),
    ]
