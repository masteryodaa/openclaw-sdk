from __future__ import annotations

from openclaw_sdk.core.agent import Agent
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.gateway.mock import MockGateway


def _make_connected_gateway() -> MockGateway:
    mock = MockGateway()
    mock._connected = True
    return mock


def _make_client(mock: MockGateway) -> OpenClawClient:
    return OpenClawClient(config=ClientConfig(), gateway=mock)


def _make_agent(mock: MockGateway, agent_id: str = "bot") -> Agent:
    client = _make_client(mock)
    return Agent(client, agent_id)


# ------------------------------------------------------------------ #
# Agent.wait_for_run()
# ------------------------------------------------------------------ #


async def test_wait_for_run_calls_agent_wait() -> None:
    mock = _make_connected_gateway()
    mock.register("agent.wait", {"status": "completed", "content": "Result"})
    agent = _make_agent(mock)

    await agent.wait_for_run("run_abc")

    mock.assert_called_with("agent.wait", {"runId": "run_abc"})


async def test_wait_for_run_returns_gateway_response() -> None:
    mock = _make_connected_gateway()
    expected = {"status": "completed", "content": "Result"}
    mock.register("agent.wait", expected)
    agent = _make_agent(mock)

    result = await agent.wait_for_run("run_abc")

    assert result == expected


async def test_wait_for_run_passes_run_id_correctly() -> None:
    mock = _make_connected_gateway()
    mock.register("agent.wait", {"status": "completed"})
    agent = _make_agent(mock)

    await agent.wait_for_run("run_xyz_123")

    method, params = mock.calls[-1]
    assert method == "agent.wait"
    assert params == {"runId": "run_xyz_123"}


# ------------------------------------------------------------------ #
# Gateway.agent_wait() facade
# ------------------------------------------------------------------ #


async def test_gateway_agent_wait_calls_correctly() -> None:
    mock = _make_connected_gateway()
    mock.register("agent.wait", {"status": "completed", "content": "Result"})

    result = await mock.agent_wait("run_abc")

    mock.assert_called_with("agent.wait", {"runId": "run_abc"})
    assert result == {"status": "completed", "content": "Result"}


async def test_gateway_agent_wait_returns_response() -> None:
    mock = _make_connected_gateway()
    expected = {"status": "done", "output": "42"}
    mock.register("agent.wait", expected)

    result = await mock.agent_wait("run_999")

    assert result == expected


async def test_gateway_agent_wait_records_call() -> None:
    mock = _make_connected_gateway()
    mock.register("agent.wait", {})

    await mock.agent_wait("r1")
    await mock.agent_wait("r2")

    assert mock.call_count("agent.wait") == 2
