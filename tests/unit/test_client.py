"""Tests for core/client.py — OpenClawClient."""
from __future__ import annotations

import pytest

from openclaw_sdk.core.client import OpenClawClient, _openclaw_is_running
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.exceptions import ConfigurationError
from openclaw_sdk.core.types import HealthStatus
from openclaw_sdk.gateway.mock import MockGateway


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(mock: MockGateway) -> OpenClawClient:
    return OpenClawClient(config=ClientConfig(), gateway=mock)


# ---------------------------------------------------------------------------
# _openclaw_is_running
# ---------------------------------------------------------------------------


def test_openclaw_is_running_returns_bool() -> None:
    # We can't assert True/False (depends on env), just ensure it doesn't raise.
    result = _openclaw_is_running()
    assert isinstance(result, bool)


def test_openclaw_is_running_closed_port_returns_false() -> None:
    # Use an unlikely-to-be-open port.
    assert _openclaw_is_running(host="127.0.0.1", port=19999) is False


# ---------------------------------------------------------------------------
# Constructor and properties
# ---------------------------------------------------------------------------


def test_client_exposes_config() -> None:
    mock = MockGateway()
    config = ClientConfig()
    client = OpenClawClient(config=config, gateway=mock)
    assert client.config is config


def test_client_exposes_gateway() -> None:
    mock = MockGateway()
    client = _make_client(mock)
    assert client.gateway is mock


def test_client_callbacks_default_empty() -> None:
    mock = MockGateway()
    client = _make_client(mock)
    assert client._callbacks == []


# ---------------------------------------------------------------------------
# Lazy manager properties
# ---------------------------------------------------------------------------


def test_channels_manager_created_lazily() -> None:
    from openclaw_sdk.channels.manager import ChannelManager

    client = _make_client(MockGateway())
    mgr = client.channels
    assert isinstance(mgr, ChannelManager)
    # Second access returns the same instance.
    assert client.channels is mgr


def test_scheduling_manager_created_lazily() -> None:
    from openclaw_sdk.scheduling.manager import ScheduleManager

    client = _make_client(MockGateway())
    mgr = client.scheduling
    assert isinstance(mgr, ScheduleManager)
    assert client.scheduling is mgr


def test_skills_manager_created_lazily() -> None:
    from openclaw_sdk.skills.manager import SkillManager

    client = _make_client(MockGateway())
    mgr = client.skills
    assert isinstance(mgr, SkillManager)
    assert client.skills is mgr


def test_clawhub_created_lazily() -> None:
    from openclaw_sdk.skills.clawhub import ClawHub

    client = _make_client(MockGateway())
    hub = client.clawhub
    assert isinstance(hub, ClawHub)
    assert client.clawhub is hub


# ---------------------------------------------------------------------------
# get_agent
# ---------------------------------------------------------------------------


def test_get_agent_returns_agent() -> None:
    from openclaw_sdk.core.agent import Agent

    client = _make_client(MockGateway())
    agent = client.get_agent("my-bot")
    assert isinstance(agent, Agent)
    assert agent.agent_id == "my-bot"
    assert agent.session_name == "main"


def test_get_agent_custom_session_name() -> None:
    client = _make_client(MockGateway())
    agent = client.get_agent("bot", session_name="chat")
    assert agent.session_name == "chat"
    assert agent.session_key == "agent:bot:chat"


# ---------------------------------------------------------------------------
# pipeline()
# ---------------------------------------------------------------------------


def test_pipeline_returns_pipeline() -> None:
    from openclaw_sdk.pipeline.pipeline import Pipeline

    client = _make_client(MockGateway())
    p = client.pipeline()
    assert isinstance(p, Pipeline)


# ---------------------------------------------------------------------------
# health()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_delegates_to_gateway() -> None:
    mock = MockGateway()
    await mock.connect()
    client = _make_client(mock)
    status = await client.health()
    assert isinstance(status, HealthStatus)
    assert status.healthy is True
    await mock.close()


@pytest.mark.asyncio
async def test_health_false_when_disconnected() -> None:
    mock = MockGateway()
    client = _make_client(mock)
    status = await client.health()
    assert status.healthy is False


# ---------------------------------------------------------------------------
# close() and context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_disconnects_gateway() -> None:
    mock = MockGateway()
    await mock.connect()
    client = _make_client(mock)
    assert mock._connected is True
    await client.close()
    assert mock._connected is False


@pytest.mark.asyncio
async def test_context_manager() -> None:
    mock = MockGateway()
    await mock.connect()
    async with OpenClawClient(config=ClientConfig(), gateway=mock) as client:
        assert isinstance(client, OpenClawClient)
    assert mock._connected is False


# ---------------------------------------------------------------------------
# _build_gateway — ConfigurationError when no gateway available
# ---------------------------------------------------------------------------


def test_build_gateway_raises_when_no_gateway_configured() -> None:
    # mode="auto" with no ws_url/base_url falls back to _openclaw_is_running.
    # Patch it to False so no gateway can be detected → ConfigurationError.
    config = ClientConfig(mode="auto")
    import unittest.mock as mock_lib

    with mock_lib.patch(
        "openclaw_sdk.core.client._openclaw_is_running", return_value=False
    ):
        with pytest.raises(ConfigurationError):
            OpenClawClient._build_gateway(config)


def test_build_gateway_uses_protocol_when_ws_url_set() -> None:
    from openclaw_sdk.gateway.protocol import ProtocolGateway

    config = ClientConfig(gateway_ws_url="ws://localhost:9999/gw")
    gw = OpenClawClient._build_gateway(config)
    assert isinstance(gw, ProtocolGateway)


def test_build_gateway_uses_openai_compat_when_base_url_set() -> None:
    from openclaw_sdk.gateway.openai_compat import OpenAICompatGateway

    config = ClientConfig(openai_base_url="http://localhost:8080")
    gw = OpenClawClient._build_gateway(config)
    assert isinstance(gw, OpenAICompatGateway)


# ---------------------------------------------------------------------------
# connect() factory classmethod
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_factory_creates_connected_client() -> None:
    """connect() builds and connects a gateway, then returns an OpenClawClient."""
    import unittest.mock as mock_lib

    mock_gw = MockGateway()
    with mock_lib.patch.object(OpenClawClient, "_build_gateway", return_value=mock_gw):
        client = await OpenClawClient.connect(gateway_ws_url="ws://localhost:9999/gw")

    assert isinstance(client, OpenClawClient)
    assert mock_gw._connected is True
    await client.close()


@pytest.mark.asyncio
async def test_connect_factory_passes_callbacks() -> None:
    """connect() forwards callbacks= kwarg to the client instance."""
    import unittest.mock as mock_lib
    from openclaw_sdk.callbacks.handler import CallbackHandler

    class _CB(CallbackHandler):
        pass

    cb = _CB()
    mock_gw = MockGateway()
    with mock_lib.patch.object(OpenClawClient, "_build_gateway", return_value=mock_gw):
        client = await OpenClawClient.connect(
            gateway_ws_url="ws://localhost:9999/gw", callbacks=[cb]
        )

    assert cb in client._callbacks
    await client.close()
