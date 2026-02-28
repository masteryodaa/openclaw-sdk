from __future__ import annotations

from unittest.mock import AsyncMock, patch

from openclaw_sdk.core.agent import Agent
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.constants import AgentStatus
from openclaw_sdk.gateway.mock import MockGateway


def _make_connected_gateway() -> MockGateway:
    mock = MockGateway()
    mock._connected = True
    return mock


def _make_client(mock: MockGateway) -> OpenClawClient:
    return OpenClawClient(config=ClientConfig(), gateway=mock)


def _make_agent(mock: MockGateway, agent_id: str = "test-bot") -> Agent:
    client = _make_client(mock)
    return Agent(client, agent_id)


async def test_execute_structured_delegates_to_structured_output() -> None:
    from pydantic import BaseModel

    class MyModel(BaseModel):
        name: str
        value: int

    mock = _make_connected_gateway()
    agent = _make_agent(mock)
    fake_result = MyModel(name="hello", value=42)

    with patch(
        "openclaw_sdk.output.structured.StructuredOutput.execute",
        new_callable=AsyncMock,
        return_value=fake_result,
    ) as mock_execute:
        result = await agent.execute_structured("What is the answer?", MyModel)

    assert result is fake_result
    mock_execute.assert_called_once()


async def test_execute_structured_passes_max_retries() -> None:
    from pydantic import BaseModel

    class SimpleModel(BaseModel):
        text: str

    mock = _make_connected_gateway()
    agent = _make_agent(mock)
    fake_result = SimpleModel(text="ok")

    with patch(
        "openclaw_sdk.output.structured.StructuredOutput.execute",
        new_callable=AsyncMock,
        return_value=fake_result,
    ) as mock_execute:
        await agent.execute_structured("query", SimpleModel, max_retries=5)

    _, kwargs = mock_execute.call_args
    assert kwargs.get("max_retries") == 5


async def test_execute_structured_passes_agent_self() -> None:
    from pydantic import BaseModel

    class Mdl(BaseModel):
        x: int

    mock = _make_connected_gateway()
    agent = _make_agent(mock)

    with patch(
        "openclaw_sdk.output.structured.StructuredOutput.execute",
        new_callable=AsyncMock,
        return_value=Mdl(x=1),
    ) as mock_execute:
        await agent.execute_structured("q", Mdl)

    args, _ = mock_execute.call_args
    assert args[0] is agent


async def test_get_file_calls_agents_files_get() -> None:
    mock = _make_connected_gateway()
    mock.register(
        "agents.files.get",
        {
            "agentId": "test-bot",
            "file": {"name": "report.csv", "content": "a,b,c"},
        },
    )
    agent = _make_agent(mock)

    result = await agent.get_file("report.csv")

    mock.assert_called_with(
        "agents.files.get",
        {"agentId": "test-bot", "name": "report.csv"},
    )
    assert result["file"]["content"] == "a,b,c"


async def test_get_file_returns_dict() -> None:
    mock = _make_connected_gateway()
    mock.register(
        "agents.files.get",
        {
            "agentId": "test-bot",
            "file": {"name": "file.txt", "content": "plain text", "size": 10},
        },
    )
    agent = _make_agent(mock)

    result = await agent.get_file("file.txt")

    assert isinstance(result, dict)
    assert result["file"]["name"] == "file.txt"


async def test_get_file_uses_agent_id() -> None:
    mock = _make_connected_gateway()
    mock.register(
        "agents.files.get",
        {"agentId": "mybot", "file": {"name": "x.bin", "content": ""}},
    )
    client = _make_client(mock)
    agent = Agent(client, "mybot", "alpha")

    await agent.get_file("x.bin")

    mock.assert_called_with(
        "agents.files.get",
        {"agentId": "mybot", "name": "x.bin"},
    )


# ------------------------------------------------------------------ #
# reset_memory — uses {key} (verified)
# ------------------------------------------------------------------ #


async def test_reset_memory_calls_sessions_reset() -> None:
    mock = _make_connected_gateway()
    mock.register("sessions.reset", {})
    agent = _make_agent(mock)

    await agent.reset_memory()

    mock.assert_called_with("sessions.reset", {"key": "agent:test-bot:main"})


async def test_reset_memory_returns_true() -> None:
    mock = _make_connected_gateway()
    mock.register("sessions.reset", {})
    agent = _make_agent(mock)

    result = await agent.reset_memory()

    assert result is True


# ------------------------------------------------------------------ #
# get_memory_status — uses {keys: [key]} (verified)
# ------------------------------------------------------------------ #


async def test_get_memory_status_calls_sessions_preview() -> None:
    mock = _make_connected_gateway()
    mock.register("sessions.preview", {"tokens": 500})
    agent = _make_agent(mock)

    await agent.get_memory_status()

    mock.assert_called_with("sessions.preview", {"keys": ["agent:test-bot:main"]})


async def test_get_memory_status_returns_dict() -> None:
    mock = _make_connected_gateway()
    mock.register("sessions.preview", {"tokens": 500, "messages": 10})
    agent = _make_agent(mock)

    result = await agent.get_memory_status()

    assert result == {"tokens": 500, "messages": 10}


# ------------------------------------------------------------------ #
# get_status — uses {key} (verified)
# ------------------------------------------------------------------ #


async def test_get_status_calls_sessions_resolve() -> None:
    mock = _make_connected_gateway()
    mock.register("sessions.resolve", {"status": "idle"})
    agent = _make_agent(mock)

    await agent.get_status()

    mock.assert_called_with("sessions.resolve", {"key": "agent:test-bot:main"})


async def test_get_status_returns_agent_status_enum() -> None:
    mock = _make_connected_gateway()
    mock.register("sessions.resolve", {"status": "running"})
    agent = _make_agent(mock)

    status = await agent.get_status()

    assert status is AgentStatus.RUNNING


async def test_get_status_maps_idle() -> None:
    mock = _make_connected_gateway()
    mock.register("sessions.resolve", {"status": "idle"})
    agent = _make_agent(mock)

    status = await agent.get_status()

    assert status is AgentStatus.IDLE


async def test_get_status_maps_error() -> None:
    mock = _make_connected_gateway()
    mock.register("sessions.resolve", {"status": "error"})
    agent = _make_agent(mock)

    status = await agent.get_status()

    assert status is AgentStatus.ERROR


async def test_get_status_unknown_string_falls_back_to_idle() -> None:
    mock = _make_connected_gateway()
    mock.register("sessions.resolve", {"status": "unknown-state"})
    agent = _make_agent(mock)

    status = await agent.get_status()

    assert status is AgentStatus.IDLE


async def test_get_status_missing_status_key_falls_back_to_idle() -> None:
    mock = _make_connected_gateway()
    mock.register("sessions.resolve", {})
    agent = _make_agent(mock)

    status = await agent.get_status()

    assert status is AgentStatus.IDLE
