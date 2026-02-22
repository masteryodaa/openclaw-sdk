"""Tests for core/conversation.py — Conversation multi-turn helper."""
from __future__ import annotations

from openclaw_sdk.core.agent import Agent
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.conversation import Conversation
from openclaw_sdk.core.types import ExecutionResult, StreamEvent
from openclaw_sdk.gateway.mock import MockGateway


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_client_and_agent(
    agent_id: str = "bot",
) -> tuple[OpenClawClient, Agent, MockGateway]:
    mock = MockGateway()
    await mock.connect()
    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    agent = client.get_agent(agent_id)
    return client, agent, mock


def _setup_execute(mock: MockGateway, content: str = "Hello!") -> None:
    """Register the responses needed for a successful agent.execute() call.

    Re-registers chat.send and pre-emits a DONE event so the next
    execute() call completes.
    """
    mock.register("chat.send", {"runId": "r1", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"content": content, "runId": "r1"}},
        )
    )


# ---------------------------------------------------------------------------
# Tests: Conversation.say()
# ---------------------------------------------------------------------------


async def test_conversation_say() -> None:
    """say() sends a message and returns an ExecutionResult."""
    _client, agent, mock = await _make_client_and_agent()
    _setup_execute(mock, content="I am fine, thanks!")

    convo = Conversation(agent)
    result = await convo.say("How are you?")

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.content == "I am fine, thanks!"
    mock.assert_called("chat.send")


async def test_conversation_say_records_history() -> None:
    """say() appends (query, response) to local history."""
    _client, agent, mock = await _make_client_and_agent()
    _setup_execute(mock, content="Response 1")

    convo = Conversation(agent)
    await convo.say("Query 1")

    assert convo.turns == 1
    assert convo.history == [("Query 1", "Response 1")]


# ---------------------------------------------------------------------------
# Tests: Conversation.turns
# ---------------------------------------------------------------------------


async def test_conversation_turns_starts_at_zero() -> None:
    """turns is 0 for a fresh conversation."""
    _client, agent, _mock = await _make_client_and_agent()
    convo = Conversation(agent)
    assert convo.turns == 0


async def test_conversation_turns_increments() -> None:
    """turns increments after say()."""
    _client, agent, mock = await _make_client_and_agent()
    _setup_execute(mock, content="Hi")

    convo = Conversation(agent)
    await convo.say("Hello")
    assert convo.turns == 1


# ---------------------------------------------------------------------------
# Tests: Conversation.reset()
# ---------------------------------------------------------------------------


async def test_conversation_reset() -> None:
    """reset() clears local history and calls agent.reset_memory()."""
    _client, agent, mock = await _make_client_and_agent()
    mock.register("sessions.reset", {})
    _setup_execute(mock, content="Hi")

    convo = Conversation(agent)
    await convo.say("Hello")
    assert convo.turns == 1

    await convo.reset()

    assert convo.turns == 0
    assert convo.history == []
    mock.assert_called("sessions.reset")


# ---------------------------------------------------------------------------
# Tests: Conversation as async context manager
# ---------------------------------------------------------------------------


async def test_conversation_context_manager() -> None:
    """Conversation supports async with."""
    _client, agent, mock = await _make_client_and_agent()
    _setup_execute(mock, content="Greetings!")

    async with Conversation(agent) as convo:
        result = await convo.say("Hello")
        assert result.content == "Greetings!"
        assert convo.turns == 1


async def test_conversation_context_manager_via_agent() -> None:
    """Agent.conversation() returns a Conversation usable as async context manager."""
    _client, agent, mock = await _make_client_and_agent()
    _setup_execute(mock, content="Hey there!")

    async with agent.conversation("test-session") as convo:
        assert isinstance(convo, Conversation)
        result = await convo.say("Hi")
        assert result.content == "Hey there!"


# ---------------------------------------------------------------------------
# Tests: Conversation.get_history()
# ---------------------------------------------------------------------------


async def test_conversation_get_history() -> None:
    """get_history() delegates to gateway.chat_history()."""
    _client, agent, mock = await _make_client_and_agent()
    mock.register(
        "chat.history",
        {"messages": [{"role": "user", "content": "hi"}]},
    )

    convo = Conversation(agent)
    history = await convo.get_history()

    assert history == [{"role": "user", "content": "hi"}]
    mock.assert_called("chat.history")


# ---------------------------------------------------------------------------
# Tests: Agent.conversation() factory
# ---------------------------------------------------------------------------


async def test_agent_conversation_factory() -> None:
    """Agent.conversation() returns a Conversation instance."""
    _client, agent, _mock = await _make_client_and_agent()
    convo = agent.conversation("my-session")
    assert isinstance(convo, Conversation)
    assert convo._session_name == "my-session"


async def test_agent_conversation_default_session() -> None:
    """Agent.conversation() defaults to session_name='main'."""
    _client, agent, _mock = await _make_client_and_agent()
    convo = agent.conversation()
    assert convo._session_name == "main"


# ---------------------------------------------------------------------------
# Tests: history property returns a copy
# ---------------------------------------------------------------------------


async def test_conversation_history_is_copy() -> None:
    """The history property returns a copy, not the internal list."""
    _client, agent, mock = await _make_client_and_agent()
    _setup_execute(mock, content="Hi")

    convo = Conversation(agent)
    await convo.say("Hello")

    h1 = convo.history
    h2 = convo.history
    assert h1 == h2
    assert h1 is not h2  # different list objects
