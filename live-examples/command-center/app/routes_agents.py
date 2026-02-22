"""Agent management endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from openclaw_sdk import AgentConfig, GatewayError

from . import gateway

router = APIRouter(prefix="/api/agents", tags=["agents"])


class CreateAgentBody(BaseModel):
    agent_id: str
    system_prompt: str = "You are a helpful assistant."


class ToolPolicyBody(BaseModel):
    tools: list[str]


class McpServerBody(BaseModel):
    name: str
    command: str
    args: list[str] = []
    env: dict[str, str] = {}


# ---- Agent CRUD ----

@router.get("")
async def list_agents():
    """List all agent sessions."""
    client = await gateway.get_client()
    agents = await client.list_agents()
    return {
        "agents": [
            {"agent_id": a.agent_id, "name": a.name, "status": a.status.value}
            for a in agents
        ]
    }


@router.post("/create")
async def create_agent(body: CreateAgentBody):
    """Create a new agent on the gateway."""
    client = await gateway.get_client()
    config = AgentConfig(agent_id=body.agent_id, system_prompt=body.system_prompt)
    agent = await client.create_agent(config)
    return {"success": True, "agent_id": agent.agent_id}


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent and all its sessions."""
    client = await gateway.get_client()
    result = await client.delete_agent(agent_id)
    return {"success": result}


# ---- Session management ----

@router.post("/{agent_id}/reset")
async def reset_session(agent_id: str, session_name: str = "main"):
    """Reset an agent's conversation memory."""
    client = await gateway.get_client()
    agent = client.get_agent(agent_id, session_name)
    await agent.reset_memory()
    return {"success": True, "agent_id": agent_id}


@router.get("/{agent_id}/preview")
async def session_preview(agent_id: str, session_name: str = "main"):
    """Get session preview for an agent."""
    client = await gateway.get_client()
    agent = client.get_agent(agent_id, session_name)
    return await agent.get_memory_status()


@router.get("/{agent_id}/status")
async def agent_status(agent_id: str):
    """Get current agent status."""
    client = await gateway.get_client()
    agent = client.get_agent(agent_id)
    status = await agent.get_status()
    return {"agent_id": agent_id, "status": status.value}


@router.post("/{agent_id}/wait/{run_id}")
async def wait_for_run(agent_id: str, run_id: str):
    """Wait for a specific run to complete."""
    client = await gateway.get_client()
    agent = client.get_agent(agent_id)
    result = await agent.wait_for_run(run_id)
    return result


# ---- Chat control ----

@router.post("/{agent_id}/abort")
async def abort_chat(agent_id: str, session_name: str = "main"):
    """Abort the current run in an agent session."""
    client = await gateway.get_client()
    session_key = f"agent:{agent_id}:{session_name}"
    result = await client.gateway.chat_abort(session_key)
    return {"success": True, "result": result}


@router.post("/{agent_id}/inject")
async def inject_message(agent_id: str, message: str, session_name: str = "main"):
    """Inject a synthetic message into agent conversation."""
    client = await gateway.get_client()
    session_key = f"agent:{agent_id}:{session_name}"
    result = await client.gateway.chat_inject(session_key, message)
    return {"success": True, "result": result}


# ---- Tool management ----

@router.post("/{agent_id}/tools/deny")
async def deny_tools(agent_id: str, body: ToolPolicyBody):
    """Add tools to the deny list."""
    client = await gateway.get_client()
    agent = client.get_agent(agent_id)
    result = await agent.deny_tools(*body.tools)
    return {"success": True, "result": result}


@router.post("/{agent_id}/tools/allow")
async def allow_tools(agent_id: str, body: ToolPolicyBody):
    """Add tools to the allow list."""
    client = await gateway.get_client()
    agent = client.get_agent(agent_id)
    result = await agent.allow_tools(*body.tools)
    return {"success": True, "result": result}


# ---- MCP servers ----

@router.post("/{agent_id}/mcp/add")
async def add_mcp_server(agent_id: str, body: McpServerBody):
    """Add or replace an MCP server on the agent."""
    from openclaw_sdk import StdioMcpServer

    client = await gateway.get_client()
    agent = client.get_agent(agent_id)
    server = StdioMcpServer(command=body.command, args=body.args, env=body.env)
    result = await agent.add_mcp_server(body.name, server)
    return {"success": True, "result": result}


@router.delete("/{agent_id}/mcp/{name}")
async def remove_mcp_server(agent_id: str, name: str):
    """Remove an MCP server from the agent."""
    client = await gateway.get_client()
    agent = client.get_agent(agent_id)
    result = await agent.remove_mcp_server(name)
    return {"success": True, "result": result}


# ---- Introspection ----

@router.get("/{agent_id}/details")
async def agent_details(agent_id: str, session_name: str = "main"):
    """Get comprehensive agent details: status, sessions, memory, model info."""
    client = await gateway.get_client()
    agent = client.get_agent(agent_id, session_name)
    details: dict = {"agent_id": agent_id}

    # Status
    try:
        status = await agent.get_status()
        details["status"] = status.value
    except Exception:
        details["status"] = "unknown"

    # Memory / session preview
    try:
        memory = await agent.get_memory_status()
        details["memory"] = memory
    except Exception:
        details["memory"] = None

    # Model info
    try:
        model_info = await client.config_mgr.get_agent_model(agent_id)
        details["model"] = model_info
    except Exception:
        details["model"] = None

    # Session keys from config
    try:
        sessions_result = await client.gateway.call("sessions.list", {})
        all_sessions = sessions_result.get("sessions", [])
        agent_sessions = [
            s for s in all_sessions
            if s.get("key", "").startswith(f"agent:{agent_id}:")
        ]
        details["sessions"] = [
            {
                "key": s.get("key"),
                "model": s.get("model"),
                "inputTokens": s.get("inputTokens", 0),
                "outputTokens": s.get("outputTokens", 0),
                "totalTokens": s.get("totalTokens", 0),
                "lastUpdated": s.get("lastUpdated"),
            }
            for s in agent_sessions
        ]
    except Exception:
        details["sessions"] = []

    return details


@router.get("/{agent_id}/history")
async def agent_history(agent_id: str, session_name: str = "main"):
    """Get conversation history for an agent session."""
    client = await gateway.get_client()
    session_key = f"agent:{agent_id}:{session_name}"
    try:
        result = await client.gateway.call("sessions.preview", {"keys": [session_key]})
        return {"agent_id": agent_id, "session": session_name, "preview": result}
    except Exception as exc:
        return {"agent_id": agent_id, "session": session_name, "error": str(exc)}


# ---- File download ----

@router.get("/{agent_id}/files/{file_path:path}")
async def get_file(agent_id: str, file_path: str):
    """Download a file generated by the agent."""
    client = await gateway.get_client()
    agent = client.get_agent(agent_id)
    try:
        data = await agent.get_file(file_path)
        return Response(content=data, media_type="application/octet-stream")
    except Exception as exc:
        raise HTTPException(404, str(exc)) from exc
