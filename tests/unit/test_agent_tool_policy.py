"""Tests for ToolPolicy and MCP server integration in Agent and Client."""

from __future__ import annotations

import json
from typing import Any

from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import AgentConfig, ClientConfig
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.mcp.server import McpServer
from openclaw_sdk.tools.policy import ToolPolicy


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _make_config_get_response(
    agents: dict[str, Any] | None = None,
    *,
    base_hash: str | None = "abc123",
) -> dict[str, Any]:
    """Build a realistic ``config.get`` response."""
    raw = json.dumps({"agents": agents or {}})
    result: dict[str, Any] = {"raw": raw, "exists": True, "path": "/mock"}
    if base_hash is not None:
        result["hash"] = base_hash
    return result


def _last_call(mock: MockGateway, method: str) -> tuple[str, dict[str, Any] | None]:
    """Return the last call for *method* from the mock's call log."""
    for m, p in reversed(mock.calls):
        if m == method:
            return m, p
    raise AssertionError(f"No call to '{method}' found in {mock.calls}")


def _last_call_parsed(mock: MockGateway, method: str) -> dict[str, Any]:
    """Return the parsed ``raw`` from the last ``config.patch`` or ``config.set``."""
    _, params = _last_call(mock, method)
    assert params is not None
    return json.loads(params["raw"])


async def _setup(
    agents: dict[str, Any] | None = None,
    base_hash: str | None = "abc123",
) -> tuple[OpenClawClient, MockGateway]:
    """Create a connected mock client with standard registrations."""
    mock = MockGateway()
    await mock.connect()
    mock.register("config.get", _make_config_get_response(agents, base_hash=base_hash))
    mock.register("config.patch", {"ok": True})
    mock.register("config.set", {"ok": True})
    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    return client, mock


# ------------------------------------------------------------------ #
# set_tool_policy
# ------------------------------------------------------------------ #


class TestSetToolPolicy:
    async def test_calls_config_get_then_config_patch(self) -> None:
        client, mock = await _setup()
        agent = client.get_agent("test-agent")
        policy = ToolPolicy.coding()

        await agent.set_tool_policy(policy)

        mock.assert_called("config.get")
        mock.assert_called("config.patch")

    async def test_patch_contains_tool_policy_structure(self) -> None:
        client, mock = await _setup()
        agent = client.get_agent("test-agent")
        policy = ToolPolicy.coding().deny("browser")

        await agent.set_tool_policy(policy)

        parsed = _last_call_parsed(mock, "config.patch")
        tools = parsed["agents"]["test-agent"]["tools"]
        assert tools["profile"] == "coding"
        assert "browser" in tools["deny"]

    async def test_patch_includes_base_hash(self) -> None:
        client, mock = await _setup(base_hash="hash42")
        agent = client.get_agent("test-agent")

        await agent.set_tool_policy(ToolPolicy.minimal())

        _, params = _last_call(mock, "config.patch")
        assert params is not None
        assert params["baseHash"] == "hash42"


# ------------------------------------------------------------------ #
# deny_tools
# ------------------------------------------------------------------ #


class TestDenyTools:
    async def test_merges_with_existing_deny_list(self) -> None:
        existing = {"test-agent": {"tools": {"profile": "coding", "deny": ["shell"]}}}
        client, mock = await _setup(agents=existing)
        agent = client.get_agent("test-agent")

        await agent.deny_tools("browser", "sudo")

        parsed = _last_call_parsed(mock, "config.patch")
        deny = parsed["agents"]["test-agent"]["tools"]["deny"]
        assert "shell" in deny
        assert "browser" in deny
        assert "sudo" in deny

    async def test_deduplicates_deny_entries(self) -> None:
        existing = {"test-agent": {"tools": {"deny": ["browser"]}}}
        client, mock = await _setup(agents=existing)
        agent = client.get_agent("test-agent")

        await agent.deny_tools("browser", "shell")

        parsed = _last_call_parsed(mock, "config.patch")
        deny = parsed["agents"]["test-agent"]["tools"]["deny"]
        assert deny.count("browser") == 1


# ------------------------------------------------------------------ #
# allow_tools
# ------------------------------------------------------------------ #


class TestAllowTools:
    async def test_adds_to_also_allow(self) -> None:
        client, mock = await _setup()
        agent = client.get_agent("test-agent")

        await agent.allow_tools("custom-tool", "my-mcp")

        parsed = _last_call_parsed(mock, "config.patch")
        also = parsed["agents"]["test-agent"]["tools"]["alsoAllow"]
        assert "custom-tool" in also
        assert "my-mcp" in also

    async def test_merges_with_existing_also_allow(self) -> None:
        existing = {"test-agent": {"tools": {"alsoAllow": ["existing"]}}}
        client, mock = await _setup(agents=existing)
        agent = client.get_agent("test-agent")

        await agent.allow_tools("new-tool")

        parsed = _last_call_parsed(mock, "config.patch")
        also = parsed["agents"]["test-agent"]["tools"]["alsoAllow"]
        assert "existing" in also
        assert "new-tool" in also


# ------------------------------------------------------------------ #
# add_mcp_server
# ------------------------------------------------------------------ #


class TestAddMcpServer:
    async def test_adds_server_config(self) -> None:
        client, mock = await _setup()
        agent = client.get_agent("test-agent")
        server = McpServer.stdio("uvx", ["mcp-server-postgres"])

        await agent.add_mcp_server("postgres", server)

        parsed = _last_call_parsed(mock, "config.patch")
        mcp = parsed["agents"]["test-agent"]["mcpServers"]
        assert "postgres" in mcp
        assert mcp["postgres"]["command"] == "uvx"
        assert mcp["postgres"]["args"] == ["mcp-server-postgres"]

    async def test_preserves_existing_servers(self) -> None:
        existing = {
            "test-agent": {
                "mcpServers": {
                    "redis": {"command": "redis-mcp", "args": []},
                }
            }
        }
        client, mock = await _setup(agents=existing)
        agent = client.get_agent("test-agent")
        server = McpServer.http("http://10.0.0.42:3721/mcp")

        await agent.add_mcp_server("remote", server)

        parsed = _last_call_parsed(mock, "config.patch")
        mcp = parsed["agents"]["test-agent"]["mcpServers"]
        assert "redis" in mcp
        assert "remote" in mcp
        assert mcp["remote"]["url"] == "http://10.0.0.42:3721/mcp"

    async def test_http_server_with_headers(self) -> None:
        client, mock = await _setup()
        agent = client.get_agent("test-agent")
        server = McpServer.http(
            "http://example.com/mcp",
            headers={"Authorization": "Bearer xxx"},
        )

        await agent.add_mcp_server("auth-server", server)

        parsed = _last_call_parsed(mock, "config.patch")
        mcp = parsed["agents"]["test-agent"]["mcpServers"]["auth-server"]
        assert mcp["transport"] == "streamable-http"
        assert mcp["headers"]["Authorization"] == "Bearer xxx"


# ------------------------------------------------------------------ #
# remove_mcp_server
# ------------------------------------------------------------------ #


class TestRemoveMcpServer:
    async def test_removes_from_config(self) -> None:
        existing = {
            "test-agent": {
                "mcpServers": {
                    "postgres": {"command": "uvx", "args": []},
                    "redis": {"command": "redis-mcp", "args": []},
                }
            }
        }
        client, mock = await _setup(agents=existing)
        agent = client.get_agent("test-agent")

        await agent.remove_mcp_server("postgres")

        parsed = _last_call_parsed(mock, "config.patch")
        mcp = parsed["agents"]["test-agent"]["mcpServers"]
        assert "postgres" not in mcp
        assert "redis" in mcp

    async def test_noop_if_server_missing(self) -> None:
        existing = {"test-agent": {"mcpServers": {"redis": {"command": "redis-mcp", "args": []}}}}
        client, mock = await _setup(agents=existing)
        agent = client.get_agent("test-agent")

        # Should not raise
        await agent.remove_mcp_server("nonexistent")

        parsed = _last_call_parsed(mock, "config.patch")
        mcp = parsed["agents"]["test-agent"]["mcpServers"]
        assert "redis" in mcp


# ------------------------------------------------------------------ #
# _patch_agent_config internals
# ------------------------------------------------------------------ #


class TestPatchAgentConfig:
    async def test_creates_agents_key_if_missing(self) -> None:
        """When config has no ``agents`` key, _patch_agent_config creates it."""
        mock = MockGateway()
        await mock.connect()
        mock.register("config.get", {"raw": "{}", "exists": True, "path": "/mock", "hash": "h1"})
        mock.register("config.patch", {"ok": True})

        client = OpenClawClient(config=ClientConfig(), gateway=mock)
        agent = client.get_agent("new-agent")

        await agent._patch_agent_config({"tools": {"profile": "minimal"}})

        parsed = _last_call_parsed(mock, "config.patch")
        assert "agents" in parsed
        assert "new-agent" in parsed["agents"]
        assert parsed["agents"]["new-agent"]["tools"]["profile"] == "minimal"

    async def test_uses_base_hash_from_config_get(self) -> None:
        client, mock = await _setup(base_hash="specific-hash")
        agent = client.get_agent("test-agent")

        await agent._patch_agent_config({"tools": {"profile": "full"}})

        _, params = _last_call(mock, "config.patch")
        assert params is not None
        assert params["baseHash"] == "specific-hash"

    async def test_omits_base_hash_when_none(self) -> None:
        client, mock = await _setup(base_hash=None)
        # Re-register config.get without hash
        mock.register("config.get", {"raw": '{"agents": {}}', "exists": True, "path": "/mock"})
        agent = client.get_agent("test-agent")

        await agent._patch_agent_config({"tools": {"profile": "minimal"}})

        _, params = _last_call(mock, "config.patch")
        assert params is not None
        assert "baseHash" not in params


# ------------------------------------------------------------------ #
# create_agent (client)
# ------------------------------------------------------------------ #


class TestCreateAgentWithToolPolicy:
    async def test_with_tool_policy_uses_to_openclaw_agent(self) -> None:
        client, mock = await _setup()
        cfg = AgentConfig(
            agent_id="policy-agent",
            name="Policy Agent",
            tool_policy=ToolPolicy.coding().deny("browser"),
        )

        agent = await client.create_agent(cfg)

        assert agent.agent_id == "policy-agent"
        _, params = _last_call(mock, "config.set")
        assert params is not None
        parsed = json.loads(params["raw"])
        agent_data = parsed["agents"]["policy-agent"]
        # to_openclaw_agent serialization: "tools" is a dict, not a list
        assert isinstance(agent_data["tools"], dict)
        assert agent_data["tools"]["profile"] == "coding"
        assert "browser" in agent_data["tools"]["deny"]
        assert agent_data["name"] == "Policy Agent"

    async def test_with_mcp_servers_includes_mcp_servers(self) -> None:
        client, mock = await _setup()
        cfg = AgentConfig(
            agent_id="mcp-agent",
            mcp_servers={
                "postgres": McpServer.stdio("uvx", ["mcp-server-postgres"]),
                "remote": McpServer.http("http://example.com/mcp"),
            },
        )

        agent = await client.create_agent(cfg)

        assert agent.agent_id == "mcp-agent"
        _, params = _last_call(mock, "config.set")
        assert params is not None
        parsed = json.loads(params["raw"])
        mcp = parsed["agents"]["mcp-agent"]["mcpServers"]
        assert "postgres" in mcp
        assert mcp["postgres"]["command"] == "uvx"
        assert "remote" in mcp
        assert mcp["remote"]["url"] == "http://example.com/mcp"
        assert mcp["remote"]["transport"] == "streamable-http"

    async def test_minimal_agent_creates_empty_config(self) -> None:
        client, mock = await _setup()
        cfg = AgentConfig(agent_id="minimal-agent")

        agent = await client.create_agent(cfg)

        assert agent.agent_id == "minimal-agent"
        _, params = _last_call(mock, "config.set")
        assert params is not None
        parsed = json.loads(params["raw"])
        agent_data = parsed["agents"]["minimal-agent"]
        # Default system_prompt is not serialized, tools not set → empty
        assert "tools" not in agent_data

    async def test_with_both_tool_policy_and_mcp_servers(self) -> None:
        client, mock = await _setup()
        cfg = AgentConfig(
            agent_id="full-agent",
            name="Full Agent",
            system_prompt="Custom prompt",
            tool_policy=ToolPolicy.full(),
            mcp_servers={
                "pg": McpServer.stdio("uvx", ["mcp-server-postgres"]),
            },
        )

        await client.create_agent(cfg)

        _, params = _last_call(mock, "config.set")
        assert params is not None
        parsed = json.loads(params["raw"])
        agent_data = parsed["agents"]["full-agent"]
        assert agent_data["name"] == "Full Agent"
        assert agent_data["systemPrompt"] == "Custom prompt"
        assert agent_data["tools"]["profile"] == "full"
        assert "pg" in agent_data["mcpServers"]
