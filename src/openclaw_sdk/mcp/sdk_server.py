"""MCP server for interacting with a live OpenClaw gateway through the SDK.

Exposes OpenClaw SDK operations as MCP tools so that Claude (or any MCP client)
can connect to a running OpenClaw instance, execute agents, manage sessions,
and inspect configuration.

Run with::

    python -m openclaw_sdk.mcp.sdk_server

With custom gateway URL::

    OPENCLAW_URL=ws://10.0.0.42:18789 python -m openclaw_sdk.mcp.sdk_server

Configure in Claude Code::

    claude mcp add openclaw-sdk -- python -m openclaw_sdk.mcp.sdk_server

Configure in Claude Desktop (claude_desktop_config.json)::

    {
      "mcpServers": {
        "openclaw-sdk": {
          "command": "python",
          "args": ["-m", "openclaw_sdk.mcp.sdk_server"],
          "env": {
            "OPENCLAW_URL": "ws://127.0.0.1:18789"
          }
        }
      }
    }
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from openclaw_sdk import OpenClawClient
from openclaw_sdk.core.types import ExecutionResult

# ---------------------------------------------------------------------------
# Lifespan: manage OpenClawClient connection
# ---------------------------------------------------------------------------


@dataclass
class AppContext:
    """Application context holding the OpenClaw client."""

    client: OpenClawClient


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Connect to OpenClaw gateway on startup, disconnect on shutdown."""
    url = os.environ.get("OPENCLAW_URL", "ws://127.0.0.1:18789")
    token = os.environ.get("OPENCLAW_TOKEN", "")

    client = await OpenClawClient.connect(
        gateway_ws_url=url,
        api_key=token or None,
    )
    try:
        yield AppContext(client=client)
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "OpenClaw SDK",
    instructions=(
        "Interact with a live OpenClaw autonomous AI agent framework. "
        "Execute agents, manage sessions, inspect configuration, and more."
    ),
    lifespan=app_lifespan,
)


def _get_client(ctx: Context[ServerSession, AppContext]) -> OpenClawClient:
    """Extract the OpenClaw client from the MCP context."""
    result: OpenClawClient = ctx.request_context.lifespan_context.client  # type: ignore[no-any-return]
    return result


def _format_result(result: ExecutionResult) -> str:
    """Format an ExecutionResult for display."""
    parts = [f"**Status**: {'Success' if result.success else 'Failed'}"]
    parts.append(f"**Content**: {result.content}")
    if result.thinking:
        parts.append(f"**Thinking**: {result.thinking}")
    if result.tool_calls:
        parts.append(f"**Tool Calls**: {len(result.tool_calls)}")
        for tc in result.tool_calls:
            parts.append(f"  - {tc.tool}: {tc.input[:100]}")
    if result.files:
        parts.append(f"**Files Generated**: {len(result.files)}")
        for f in result.files:
            parts.append(f"  - {f.name} ({f.size_bytes} bytes)")
    if result.token_usage:
        parts.append(
            f"**Tokens**: input={result.token_usage.input}, output={result.token_usage.output}"
        )
    if result.latency_ms:
        parts.append(f"**Latency**: {result.latency_ms}ms")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Tools: Agent Execution
# ---------------------------------------------------------------------------


@mcp.tool()
async def execute_agent(
    ctx: Context[ServerSession, AppContext],
    agent_id: str,
    query: str,
) -> str:
    """Execute an OpenClaw agent with a query.

    Args:
        agent_id: The agent ID to execute (e.g., 'my-assistant').
        query: The message/query to send to the agent.

    Returns:
        The agent's response including content, tool calls, and files.
    """
    client = _get_client(ctx)
    agent = client.get_agent(agent_id)
    result = await agent.execute(query)
    return _format_result(result)


@mcp.tool()
async def list_sessions(
    ctx: Context[ServerSession, AppContext],
) -> str:
    """List all active sessions on the OpenClaw gateway.

    Returns:
        A formatted list of active sessions with their keys and metadata.
    """
    client = _get_client(ctx)
    gateway = client._gateway
    response = await gateway.call("sessions.list", {})
    sessions = response.get("sessions", [])
    if not sessions:
        return "No active sessions."

    lines = [f"**Active Sessions** ({len(sessions)})\n"]
    for s in sessions:
        key = s.get("key", "unknown")
        lines.append(f"- `{key}`")
        if s.get("lastMessage"):
            lines.append(f"  Last message: {s['lastMessage'][:80]}")
    return "\n".join(lines)


@mcp.tool()
async def get_session(
    ctx: Context[ServerSession, AppContext],
    session_key: str,
) -> str:
    """Get details of a specific session.

    Args:
        session_key: The session key (e.g., 'agent:my-assistant:default').

    Returns:
        Session details including messages and metadata.
    """
    client = _get_client(ctx)
    gateway = client._gateway
    response = await gateway.call("sessions.get", {"key": session_key})
    return json.dumps(response, indent=2, default=str)


@mcp.tool()
async def preview_sessions(
    ctx: Context[ServerSession, AppContext],
    session_keys: list[str],
) -> str:
    """Preview multiple sessions at once.

    Args:
        session_keys: List of session keys to preview.

    Returns:
        Preview data for the requested sessions.
    """
    client = _get_client(ctx)
    gateway = client._gateway
    response = await gateway.call("sessions.preview", {"keys": session_keys})
    return json.dumps(response, indent=2, default=str)


# ---------------------------------------------------------------------------
# Tools: Configuration
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_config(
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Get the current OpenClaw gateway configuration.

    Returns:
        The full gateway configuration as JSON.
    """
    client = _get_client(ctx)
    gateway = client._gateway
    response = await gateway.call("config.get", {})
    return json.dumps(response, indent=2, default=str)


@mcp.tool()
async def gateway_health(
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Check the health status of the OpenClaw gateway.

    Returns:
        Health status information.
    """
    client = _get_client(ctx)
    gateway = client._gateway
    healthy = await gateway.health()
    return f"Gateway is {'healthy' if healthy else 'unhealthy'}"


# ---------------------------------------------------------------------------
# Tools: Session Management
# ---------------------------------------------------------------------------


@mcp.tool()
async def clear_session(
    ctx: Context[ServerSession, AppContext],
    session_key: str,
) -> str:
    """Clear/reset a session's conversation history.

    Args:
        session_key: The session key to clear.

    Returns:
        Confirmation of the session clear operation.
    """
    client = _get_client(ctx)
    gateway = client._gateway
    await gateway.call("sessions.clear", {"key": session_key})
    return f"Session `{session_key}` cleared."


@mcp.tool()
async def inject_message(
    ctx: Context[ServerSession, AppContext],
    session_key: str,
    message: str,
) -> str:
    """Inject a system/context message into a session without triggering execution.

    Args:
        session_key: The session key to inject into.
        message: The message to inject.

    Returns:
        Confirmation of the injection.
    """
    client = _get_client(ctx)
    gateway = client._gateway
    await gateway.call(
        "chat.inject", {"sessionKey": session_key, "message": message}
    )
    return f"Message injected into `{session_key}`."


@mcp.tool()
async def abort_agent(
    ctx: Context[ServerSession, AppContext],
    session_key: str,
) -> str:
    """Abort a currently running agent execution.

    Args:
        session_key: The session key of the running agent.

    Returns:
        Confirmation of the abort.
    """
    client = _get_client(ctx)
    gateway = client._gateway
    await gateway.call("chat.abort", {"sessionKey": session_key})
    return f"Agent execution aborted for `{session_key}`."


# ---------------------------------------------------------------------------
# Tools: Logs
# ---------------------------------------------------------------------------


@mcp.tool()
async def tail_logs(
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Get recent logs from the OpenClaw gateway.

    Returns:
        Recent log entries.
    """
    client = _get_client(ctx)
    gateway = client._gateway
    response = await gateway.call("logs.tail", {})
    return json.dumps(response, indent=2, default=str)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("openclaw://status")
def server_status() -> str:
    """Get the MCP server status and configuration."""
    url = os.environ.get("OPENCLAW_URL", "ws://127.0.0.1:18789")
    return (
        f"OpenClaw SDK MCP Server\n"
        f"Gateway URL: {url}\n"
        f"Transport: stdio\n"
        f"SDK Version: 1.0.0"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
