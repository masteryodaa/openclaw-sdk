"""Tests for new OpenClawClient methods and properties (MD7 additions)."""

from __future__ import annotations

import json

from openclaw_sdk.approvals.manager import ApprovalManager
from openclaw_sdk.channels.config import WhatsAppChannelConfig
from openclaw_sdk.config.manager import ConfigManager
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import AgentConfig, ClientConfig
from openclaw_sdk.core.constants import AgentStatus
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.nodes.manager import NodeManager
from openclaw_sdk.ops.manager import OpsManager
from openclaw_sdk.scheduling.manager import ScheduleManager
from openclaw_sdk.webhooks.manager import WebhookManager


def _make_client() -> tuple[MockGateway, OpenClawClient]:
    mock = MockGateway()
    mock._connected = True
    return mock, OpenClawClient(config=ClientConfig(), gateway=mock)


# ------------------------------------------------------------------ #
# New properties
# ------------------------------------------------------------------ #


async def test_schedules_property_returns_schedule_manager() -> None:
    _, client = _make_client()
    assert isinstance(client.schedules, ScheduleManager)


async def test_schedules_is_same_as_scheduling() -> None:
    _, client = _make_client()
    _ = client.scheduling  # force lazy init via the old property
    assert client.schedules is client.scheduling


async def test_webhooks_property_returns_webhook_manager() -> None:
    _, client = _make_client()
    assert isinstance(client.webhooks, WebhookManager)


async def test_config_mgr_property_returns_config_manager() -> None:
    _, client = _make_client()
    assert isinstance(client.config_mgr, ConfigManager)


async def test_approvals_property_returns_approval_manager() -> None:
    _, client = _make_client()
    assert isinstance(client.approvals, ApprovalManager)


async def test_nodes_property_returns_node_manager() -> None:
    _, client = _make_client()
    assert isinstance(client.nodes, NodeManager)


async def test_ops_property_returns_ops_manager() -> None:
    _, client = _make_client()
    assert isinstance(client.ops, OpsManager)


async def test_properties_are_lazy_singletons() -> None:
    _, client = _make_client()
    assert client.approvals is client.approvals
    assert client.nodes is client.nodes
    assert client.ops is client.ops
    assert client.config_mgr is client.config_mgr
    assert client.webhooks is client.webhooks


# ------------------------------------------------------------------ #
# create_agent — uses agents.create gateway RPC
# ------------------------------------------------------------------ #


async def test_create_agent_calls_agents_create() -> None:
    mock, client = _make_client()
    mock.register("agents.create", {"id": "new-bot", "name": "new-bot"})

    config = AgentConfig(agent_id="new-bot", system_prompt="You are a bot")
    agent = await client.create_agent(config)

    mock.assert_called("agents.create")
    _, params = mock.calls[-1]
    assert params["name"] == "new-bot"
    assert agent.agent_id == "new-bot"


async def test_create_agent_returns_agent_with_correct_id() -> None:
    mock, client = _make_client()
    mock.register("agents.create", {"id": "researcher"})

    config = AgentConfig(agent_id="researcher")
    agent = await client.create_agent(config)

    assert agent.agent_id == "researcher"
    assert agent.session_key == "agent:researcher:main"


# ------------------------------------------------------------------ #
# list_agents — uses agents.list gateway RPC
# ------------------------------------------------------------------ #


async def test_list_agents_calls_agents_list() -> None:
    mock, client = _make_client()
    mock.register(
        "agents.list",
        {
            "defaultId": "main",
            "agents": [
                {"id": "bot1"},
                {"id": "bot2"},
            ],
        },
    )

    result = await client.list_agents()

    mock.assert_called("agents.list")
    assert len(result) == 2
    assert result[0].agent_id == "bot1"
    assert result[0].status == AgentStatus.IDLE
    assert result[1].agent_id == "bot2"


async def test_list_agents_handles_empty_list() -> None:
    mock, client = _make_client()
    mock.register("agents.list", {"agents": []})

    result = await client.list_agents()

    assert result == []


# ------------------------------------------------------------------ #
# delete_agent — uses agents.delete gateway RPC
# ------------------------------------------------------------------ #


async def test_delete_agent_calls_agents_delete() -> None:
    mock, client = _make_client()
    mock.register("agents.delete", {"ok": True})

    result = await client.delete_agent("old-bot")

    method, params = mock.calls[-1]
    assert method == "agents.delete"
    assert params == {"agentId": "old-bot"}
    assert result is True


# ------------------------------------------------------------------ #
# configure_channel — read-modify-write via config.get + config.set
# ------------------------------------------------------------------ #


async def test_configure_channel_reads_then_writes_config() -> None:
    mock, client = _make_client()
    mock.register("config.get", {"raw": '{"channels": {}}', "parsed": {"channels": {}}})
    mock.register("config.set", {"ok": True})

    config = WhatsAppChannelConfig(dm_policy="allowlist")
    result = await client.configure_channel(config)

    assert mock.calls[0][0] == "config.get"
    assert mock.calls[1][0] == "config.set"
    written_raw = mock.calls[1][1]["raw"]
    parsed = json.loads(written_raw)
    assert "whatsapp" in parsed["channels"]
    assert result["ok"] is True


# ------------------------------------------------------------------ #
# list_channels
# ------------------------------------------------------------------ #


async def test_list_channels_calls_channels_status() -> None:
    mock, client = _make_client()
    mock.register(
        "channels.status",
        {
            "channels": {
                "whatsapp": {"connected": True},
                "telegram": {"connected": False},
            }
        },
    )

    result = await client.list_channels()

    mock.assert_called("channels.status")
    assert len(result) == 2
    names = {ch["name"] for ch in result}
    assert names == {"whatsapp", "telegram"}


async def test_list_channels_empty() -> None:
    mock, client = _make_client()
    mock.register("channels.status", {"channels": {}})

    result = await client.list_channels()

    assert result == []


# ------------------------------------------------------------------ #
# remove_channel
# ------------------------------------------------------------------ #


async def test_remove_channel_calls_channels_logout() -> None:
    mock, client = _make_client()
    mock.register("channels.logout", {})

    result = await client.remove_channel("whatsapp")

    method, params = mock.calls[-1]
    assert method == "channels.logout"
    assert params["channel"] == "whatsapp"
    assert result is True
