"""Tests for Phase 6A: Agent CRUD & Files gateway methods.

Covers:
- Gateway facade methods (agents_list, agents_create, agents_update,
  agents_delete, agents_files_list, agents_files_get, agents_files_set,
  agent_identity_get)
- Client methods (create_agent, list_agents, delete_agent) using new gateway RPC
- Agent methods (get_file, list_files, set_file, get_identity)
- Pydantic model parsing for all new types
"""

from __future__ import annotations

from openclaw_sdk.core.agent import Agent
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import AgentConfig, ClientConfig
from openclaw_sdk.core.constants import AgentStatus
from openclaw_sdk.core.types import (
    AgentFileContent,
    AgentFileInfo,
    AgentIdentity,
    AgentListItem,
    AgentListResponse,
    AgentSummary,
)
from openclaw_sdk.gateway.mock import MockGateway

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _make_gateway() -> MockGateway:
    mock = MockGateway()
    mock._connected = True
    return mock


def _make_client(mock: MockGateway) -> OpenClawClient:
    return OpenClawClient(config=ClientConfig(), gateway=mock)


def _make_agent(mock: MockGateway, agent_id: str = "test-bot") -> Agent:
    client = _make_client(mock)
    return Agent(client, agent_id)


# ================================================================== #
# 1. Gateway facade methods
# ================================================================== #


async def test_agents_list_facade() -> None:
    gw = _make_gateway()
    gw.register(
        "agents.list",
        {
            "defaultId": "main",
            "mainKey": "agent:main:main",
            "scope": "local",
            "agents": [{"id": "bot-a"}, {"id": "bot-b"}],
        },
    )

    result = await gw.agents_list()

    method, params = gw.calls[-1]
    assert method == "agents.list"
    assert params == {}
    assert len(result["agents"]) == 2
    assert result["defaultId"] == "main"


async def test_agents_create_facade() -> None:
    gw = _make_gateway()
    gw.register("agents.create", {"id": "new-bot", "name": "New Bot"})

    result = await gw.agents_create("New Bot")

    method, params = gw.calls[-1]
    assert method == "agents.create"
    assert params == {"name": "New Bot"}
    assert result["id"] == "new-bot"


async def test_agents_create_with_workspace() -> None:
    gw = _make_gateway()
    gw.register("agents.create", {"id": "new-bot"})

    await gw.agents_create("New Bot", workspace="/home/agent/ws")

    _, params = gw.calls[-1]
    assert params["name"] == "New Bot"
    assert params["workspace"] == "/home/agent/ws"


async def test_agents_create_without_workspace_omits_param() -> None:
    gw = _make_gateway()
    gw.register("agents.create", {"id": "new-bot"})

    await gw.agents_create("New Bot")

    _, params = gw.calls[-1]
    assert "workspace" not in params


async def test_agents_update_facade() -> None:
    gw = _make_gateway()
    gw.register("agents.update", {"ok": True})

    result = await gw.agents_update("bot-a", name="Updated Bot")

    method, params = gw.calls[-1]
    assert method == "agents.update"
    assert params["agentId"] == "bot-a"
    assert params["name"] == "Updated Bot"
    assert result["ok"] is True


async def test_agents_update_with_multiple_fields() -> None:
    gw = _make_gateway()
    gw.register("agents.update", {"ok": True})

    await gw.agents_update("bot-a", name="X", workspace="/tmp/ws")

    _, params = gw.calls[-1]
    assert params["agentId"] == "bot-a"
    assert params["name"] == "X"
    assert params["workspace"] == "/tmp/ws"


async def test_agents_delete_facade() -> None:
    gw = _make_gateway()
    gw.register("agents.delete", {"ok": True})

    result = await gw.agents_delete("bot-a")

    method, params = gw.calls[-1]
    assert method == "agents.delete"
    assert params == {"agentId": "bot-a"}
    assert result["ok"] is True


async def test_agents_files_list_facade() -> None:
    gw = _make_gateway()
    gw.register(
        "agents.files.list",
        {
            "agentId": "bot-a",
            "workspace": "/home/ws",
            "files": [
                {"name": "SOUL.md", "path": "/home/ws/SOUL.md", "size": 100},
            ],
        },
    )

    result = await gw.agents_files_list("bot-a")

    method, params = gw.calls[-1]
    assert method == "agents.files.list"
    assert params == {"agentId": "bot-a"}
    assert len(result["files"]) == 1
    assert result["files"][0]["name"] == "SOUL.md"


async def test_agents_files_get_facade() -> None:
    gw = _make_gateway()
    gw.register(
        "agents.files.get",
        {
            "agentId": "bot-a",
            "workspace": "/home/ws",
            "file": {
                "name": "SOUL.md",
                "path": "/home/ws/SOUL.md",
                "size": 42,
                "content": "# Soul\nHello",
            },
        },
    )

    result = await gw.agents_files_get("bot-a", "SOUL.md")

    method, params = gw.calls[-1]
    assert method == "agents.files.get"
    assert params == {"agentId": "bot-a", "name": "SOUL.md"}
    assert result["file"]["content"] == "# Soul\nHello"


async def test_agents_files_set_facade() -> None:
    gw = _make_gateway()
    gw.register("agents.files.set", {"ok": True})

    result = await gw.agents_files_set("bot-a", "SOUL.md", "# New Soul")

    method, params = gw.calls[-1]
    assert method == "agents.files.set"
    assert params == {
        "agentId": "bot-a",
        "name": "SOUL.md",
        "content": "# New Soul",
    }
    assert result["ok"] is True


async def test_agent_identity_get_facade() -> None:
    gw = _make_gateway()
    gw.register(
        "agent.identity.get",
        {
            "agentId": "bot-a",
            "name": "Bot Alpha",
            "avatar": "https://example.com/avatar.png",
            "emoji": "🤖",
        },
    )

    result = await gw.agent_identity_get()

    method, params = gw.calls[-1]
    assert method == "agent.identity.get"
    assert params == {}
    assert result["agentId"] == "bot-a"
    assert result["name"] == "Bot Alpha"


# ================================================================== #
# 2. Client methods using new gateway RPC
# ================================================================== #


async def test_client_list_agents_uses_agents_list() -> None:
    gw = _make_gateway()
    gw.register(
        "agents.list",
        {
            "defaultId": "main",
            "agents": [{"id": "alpha"}, {"id": "beta"}],
        },
    )
    client = _make_client(gw)

    summaries = await client.list_agents()

    gw.assert_called("agents.list")
    assert len(summaries) == 2
    assert isinstance(summaries[0], AgentSummary)
    assert summaries[0].agent_id == "alpha"
    assert summaries[1].agent_id == "beta"
    # Default status is IDLE when agents.list doesn't provide status
    assert summaries[0].status == AgentStatus.IDLE


async def test_client_list_agents_empty() -> None:
    gw = _make_gateway()
    gw.register("agents.list", {"agents": []})
    client = _make_client(gw)

    summaries = await client.list_agents()

    assert summaries == []


async def test_client_create_agent_uses_agents_create() -> None:
    gw = _make_gateway()
    gw.register("agents.create", {"id": "new-agent", "name": "new-agent"})
    client = _make_client(gw)

    config = AgentConfig(agent_id="new-agent")
    agent = await client.create_agent(config)

    gw.assert_called("agents.create")
    _, params = gw.calls[-1]
    assert params["name"] == "new-agent"
    assert isinstance(agent, Agent)
    assert agent.agent_id == "new-agent"


async def test_client_delete_agent_uses_agents_delete() -> None:
    gw = _make_gateway()
    gw.register("agents.delete", {"ok": True})
    client = _make_client(gw)

    result = await client.delete_agent("bot-a")

    gw.assert_called("agents.delete")
    _, params = gw.calls[-1]
    assert params == {"agentId": "bot-a"}
    assert result is True


# ================================================================== #
# 3. Agent instance methods
# ================================================================== #


async def test_agent_get_file() -> None:
    gw = _make_gateway()
    gw.register(
        "agents.files.get",
        {
            "agentId": "test-bot",
            "file": {
                "name": "SOUL.md",
                "content": "# Soul Content",
                "size": 15,
            },
        },
    )
    agent = _make_agent(gw)

    result = await agent.get_file("SOUL.md")

    gw.assert_called("agents.files.get")
    _, params = gw.calls[-1]
    assert params == {"agentId": "test-bot", "name": "SOUL.md"}
    assert result["file"]["content"] == "# Soul Content"


async def test_agent_list_files() -> None:
    gw = _make_gateway()
    gw.register(
        "agents.files.list",
        {
            "agentId": "test-bot",
            "files": [
                {"name": "SOUL.md", "size": 100},
                {"name": "README.md", "size": 200},
            ],
        },
    )
    agent = _make_agent(gw)

    result = await agent.list_files()

    gw.assert_called("agents.files.list")
    _, params = gw.calls[-1]
    assert params == {"agentId": "test-bot"}
    assert len(result["files"]) == 2


async def test_agent_set_file() -> None:
    gw = _make_gateway()
    gw.register("agents.files.set", {"ok": True})
    agent = _make_agent(gw)

    result = await agent.set_file("SOUL.md", "# Updated Soul")

    gw.assert_called("agents.files.set")
    _, params = gw.calls[-1]
    assert params == {
        "agentId": "test-bot",
        "name": "SOUL.md",
        "content": "# Updated Soul",
    }
    assert result["ok"] is True


async def test_agent_get_identity() -> None:
    gw = _make_gateway()
    gw.register(
        "agent.identity.get",
        {
            "agentId": "test-bot",
            "name": "Test Bot",
            "avatar": "https://example.com/avatar.png",
        },
    )
    agent = _make_agent(gw)

    result = await agent.get_identity()

    gw.assert_called("agent.identity.get")
    assert result["agentId"] == "test-bot"
    assert result["name"] == "Test Bot"


# ================================================================== #
# 4. Pydantic model parsing
# ================================================================== #


def test_agent_list_item_model() -> None:
    item = AgentListItem(id="bot-a")
    assert item.id == "bot-a"


def test_agent_list_response_model() -> None:
    data = {
        "defaultId": "main",
        "mainKey": "agent:main:main",
        "scope": "local",
        "agents": [{"id": "bot-a"}, {"id": "bot-b"}],
    }
    resp = AgentListResponse.model_validate(data)
    assert resp.default_id == "main"
    assert resp.main_key == "agent:main:main"
    assert resp.scope == "local"
    assert len(resp.agents) == 2
    assert resp.agents[0].id == "bot-a"
    assert resp.agents[1].id == "bot-b"


def test_agent_list_response_defaults() -> None:
    resp = AgentListResponse.model_validate({})
    assert resp.default_id is None
    assert resp.main_key is None
    assert resp.scope is None
    assert resp.agents == []


def test_agent_list_response_populate_by_name() -> None:
    resp = AgentListResponse(default_id="x", main_key="y")
    assert resp.default_id == "x"
    assert resp.main_key == "y"


def test_agent_identity_model() -> None:
    data = {
        "agentId": "bot-a",
        "name": "Bot Alpha",
        "avatar": "https://example.com/a.png",
        "emoji": "🤖",
    }
    ident = AgentIdentity.model_validate(data)
    assert ident.agent_id == "bot-a"
    assert ident.name == "Bot Alpha"
    assert ident.avatar == "https://example.com/a.png"
    assert ident.emoji == "🤖"


def test_agent_identity_minimal() -> None:
    data = {"agentId": "bot-b"}
    ident = AgentIdentity.model_validate(data)
    assert ident.agent_id == "bot-b"
    assert ident.name is None
    assert ident.avatar is None
    assert ident.emoji is None


def test_agent_identity_populate_by_name() -> None:
    ident = AgentIdentity(agent_id="bot-c")
    assert ident.agent_id == "bot-c"


def test_agent_file_info_model() -> None:
    data = {
        "name": "SOUL.md",
        "path": "/home/ws/SOUL.md",
        "missing": False,
        "size": 1024,
        "updatedAtMs": 1709123456000,
    }
    info = AgentFileInfo.model_validate(data)
    assert info.name == "SOUL.md"
    assert info.path == "/home/ws/SOUL.md"
    assert info.missing is False
    assert info.size == 1024
    assert info.updated_at_ms == 1709123456000


def test_agent_file_info_defaults() -> None:
    info = AgentFileInfo(name="test.txt")
    assert info.name == "test.txt"
    assert info.path is None
    assert info.missing is False
    assert info.size is None
    assert info.updated_at_ms is None


def test_agent_file_info_missing_file() -> None:
    data = {"name": "gone.txt", "missing": True}
    info = AgentFileInfo.model_validate(data)
    assert info.missing is True


def test_agent_file_content_model() -> None:
    data = {
        "name": "SOUL.md",
        "path": "/home/ws/SOUL.md",
        "missing": False,
        "size": 42,
        "updatedAtMs": 1709123456000,
        "content": "# Hello World",
    }
    fc = AgentFileContent.model_validate(data)
    assert fc.name == "SOUL.md"
    assert fc.path == "/home/ws/SOUL.md"
    assert fc.missing is False
    assert fc.size == 42
    assert fc.updated_at_ms == 1709123456000
    assert fc.content == "# Hello World"


def test_agent_file_content_defaults() -> None:
    fc = AgentFileContent(name="test.txt")
    assert fc.content is None
    assert fc.missing is False


def test_agent_file_content_populate_by_name() -> None:
    fc = AgentFileContent(name="x.txt", updated_at_ms=12345)
    assert fc.updated_at_ms == 12345
