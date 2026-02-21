"""Flask integration for OpenClaw SDK.

Requires: ``pip install openclaw-sdk[flask]``
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openclaw_sdk.core.client import OpenClawClient


def create_agent_blueprint(
    client: OpenClawClient,
    *,
    url_prefix: str = "/agents",
) -> Any:
    """Create a Flask Blueprint with agent endpoints.

    Provides:
    - GET {prefix}/health — gateway health check
    - POST {prefix}/<agent_id>/execute — execute a query
    """
    try:
        from flask import Blueprint, jsonify, request
    except ImportError as exc:
        raise ImportError(
            "Flask is required for this integration. "
            "Install with: pip install openclaw-sdk[flask]"
        ) from exc

    import asyncio

    bp = Blueprint("openclaw_agents", __name__, url_prefix=url_prefix)

    @bp.route("/health", methods=["GET"])
    def health() -> Any:
        loop = asyncio.new_event_loop()
        try:
            status = loop.run_until_complete(client.health())
            return jsonify({"healthy": status.healthy, "version": status.version})
        finally:
            loop.close()

    @bp.route("/<agent_id>/execute", methods=["POST"])
    def execute(agent_id: str) -> Any:
        data = request.get_json() or {}
        query = data.get("query", "")
        loop = asyncio.new_event_loop()
        try:
            agent = client.get_agent(agent_id)
            result = loop.run_until_complete(agent.execute(query))
            return jsonify({
                "success": result.success,
                "content": result.content,
                "latency_ms": result.latency_ms,
            })
        finally:
            loop.close()

    return bp


def create_channel_blueprint(
    client: OpenClawClient,
    *,
    url_prefix: str = "/channels",
) -> Any:
    """Create a Flask Blueprint with channel endpoints."""
    try:
        from flask import Blueprint, jsonify  # noqa: F811
    except ImportError as exc:
        raise ImportError(
            "Flask is required. Install with: pip install openclaw-sdk[flask]"
        ) from exc

    import asyncio

    bp = Blueprint("openclaw_channels", __name__, url_prefix=url_prefix)

    @bp.route("/status", methods=["GET"])
    def status() -> Any:
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(client.channels.status())
            return jsonify(result)
        finally:
            loop.close()

    return bp
