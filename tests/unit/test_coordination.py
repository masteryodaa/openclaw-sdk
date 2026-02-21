"""Tests for coordination module — Supervisor, ConsensusGroup, AgentRouter."""
from __future__ import annotations

import pytest

from openclaw_sdk.coordination.consensus import ConsensusGroup, ConsensusResult
from openclaw_sdk.coordination.router import AgentRouter
from openclaw_sdk.coordination.supervisor import Supervisor, SupervisorResult
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.gateway.mock import MockGateway


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _done_event(content: str) -> StreamEvent:
    """Create a DONE StreamEvent with given content (no run_id filtering)."""
    return StreamEvent(
        event_type=EventType.DONE,
        data={"payload": {"content": content}},
    )


def _aborted_event() -> StreamEvent:
    """Create a DONE StreamEvent with aborted state (success=False)."""
    return StreamEvent(
        event_type=EventType.DONE,
        data={"payload": {"content": "", "state": "aborted"}},
    )


async def _make_client_and_mock() -> tuple[OpenClawClient, MockGateway]:
    """Create a connected OpenClawClient backed by a MockGateway."""
    mock = MockGateway()
    await mock.connect()
    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    return client, mock


# ---------------------------------------------------------------------------
# Supervisor — sequential
# ---------------------------------------------------------------------------


async def test_supervisor_sequential() -> None:
    """Sequential strategy: workers execute in order, accumulating context."""
    client, mock = await _make_client_and_mock()

    call_count = 0

    def _send_handler(params: dict[str, object] | None) -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        return {"runId": f"run-{call_count}", "status": "started"}

    mock.register("chat.send", _send_handler)

    # Pre-emit DONE events — consumed in order (sequential, one at a time)
    mock.emit_event(_done_event("Research result"))
    mock.emit_event(_done_event("Written report"))

    supervisor = Supervisor(client, supervisor_agent_id="manager")
    supervisor.add_worker("researcher", description="Research tasks")
    supervisor.add_worker("writer", description="Writing tasks")

    result = await supervisor.delegate("Write a report on AI", strategy="sequential")

    assert isinstance(result, SupervisorResult)
    assert result.success is True
    assert result.delegations == ["researcher", "writer"]
    assert "researcher" in result.worker_results
    assert "writer" in result.worker_results
    assert result.worker_results["researcher"].content == "Research result"
    assert result.worker_results["writer"].content == "Written report"
    assert result.final_result is not None
    assert result.final_result.content == "Written report"
    assert result.latency_ms >= 0
    await client.close()


# ---------------------------------------------------------------------------
# Supervisor — parallel
# ---------------------------------------------------------------------------


async def test_supervisor_parallel() -> None:
    """Parallel strategy: all workers execute concurrently."""
    client, mock = await _make_client_and_mock()

    call_count = 0

    def _send_handler(params: dict[str, object] | None) -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        return {"runId": f"run-{call_count}", "status": "started"}

    mock.register("chat.send", _send_handler)

    # Pre-emit DONE events for 2 workers (no run_id → no filtering)
    mock.emit_event(_done_event("Result A"))
    mock.emit_event(_done_event("Result B"))

    supervisor = Supervisor(client)
    supervisor.add_worker("agent-a")
    supervisor.add_worker("agent-b")

    result = await supervisor.delegate("Do something", strategy="parallel")

    assert isinstance(result, SupervisorResult)
    assert result.success is True
    assert len(result.worker_results) == 2
    assert result.latency_ms >= 0
    # Both workers should be in results (order of content may vary)
    assert "agent-a" in result.worker_results
    assert "agent-b" in result.worker_results
    await client.close()


# ---------------------------------------------------------------------------
# Supervisor — round-robin (first success wins)
# ---------------------------------------------------------------------------


async def test_supervisor_round_robin_first_success() -> None:
    """Round-robin: first unsuccessful, second succeeds and wins."""
    client, mock = await _make_client_and_mock()

    call_count = 0

    def _send_handler(params: dict[str, object] | None) -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        return {"runId": f"run-{call_count}", "status": "started"}

    mock.register("chat.send", _send_handler)

    # First worker aborted (success=False), second worker succeeds
    mock.emit_event(_aborted_event())
    mock.emit_event(_done_event("Success!"))

    supervisor = Supervisor(client)
    supervisor.add_worker("failing-agent")
    supervisor.add_worker("good-agent")

    result = await supervisor.delegate("Try this", strategy="round-robin")

    assert result.success is True
    assert result.final_result is not None
    assert result.final_result.content == "Success!"
    assert result.delegations == ["failing-agent", "good-agent"]
    assert len(result.worker_results) == 2
    await client.close()


# ---------------------------------------------------------------------------
# Supervisor — add_worker fluent API
# ---------------------------------------------------------------------------


def test_supervisor_add_worker_fluent() -> None:
    """add_worker returns self for method chaining."""
    mock = MockGateway()
    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    supervisor = Supervisor(client)

    returned = supervisor.add_worker("a", "first").add_worker("b", "second")

    assert returned is supervisor
    assert "a" in supervisor._workers
    assert "b" in supervisor._workers


# ---------------------------------------------------------------------------
# ConsensusGroup — majority agrees
# ---------------------------------------------------------------------------


async def test_consensus_majority_agrees() -> None:
    """Majority vote: 2 out of 3 agents agree."""
    client, mock = await _make_client_and_mock()

    call_count = 0

    def _send_handler(params: dict[str, object] | None) -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        return {"runId": f"run-{call_count}", "status": "started"}

    mock.register("chat.send", _send_handler)

    # Pre-emit: two agents say "4", one says "5"
    mock.emit_event(_done_event("4"))
    mock.emit_event(_done_event("4"))
    mock.emit_event(_done_event("5"))

    group = ConsensusGroup(client, ["a1", "a2", "a3"])
    result = await group.vote("What is 2+2?", method="majority")

    assert isinstance(result, ConsensusResult)
    assert result.success is True
    assert result.chosen_result is not None
    assert result.chosen_result.content == "4"
    assert result.agreement_ratio == pytest.approx(2 / 3)
    assert len(result.all_results) == 3
    await client.close()


# ---------------------------------------------------------------------------
# ConsensusGroup — unanimous fails on disagreement
# ---------------------------------------------------------------------------


async def test_consensus_unanimous_fails_disagree() -> None:
    """Unanimous vote fails when agents disagree."""
    client, mock = await _make_client_and_mock()

    call_count = 0

    def _send_handler(params: dict[str, object] | None) -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        return {"runId": f"run-{call_count}", "status": "started"}

    mock.register("chat.send", _send_handler)

    # Two agents disagree
    mock.emit_event(_done_event("yes"))
    mock.emit_event(_done_event("no"))

    group = ConsensusGroup(client, ["voter-a", "voter-b"])
    result = await group.vote("Should we proceed?", method="unanimous")

    assert result.success is False
    assert len(result.all_results) == 2
    assert len(result.votes) == 2
    await client.close()


# ---------------------------------------------------------------------------
# ConsensusGroup — "any" passes when at least one succeeds
# ---------------------------------------------------------------------------


async def test_consensus_any_passes() -> None:
    """'any' method passes if at least one result has success=True."""
    client, mock = await _make_client_and_mock()

    call_count = 0

    def _send_handler(params: dict[str, object] | None) -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        return {"runId": f"run-{call_count}", "status": "started"}

    mock.register("chat.send", _send_handler)

    # Both agents produce DONE events with content -> success=True
    mock.emit_event(_done_event("answer-a"))
    mock.emit_event(_done_event("answer-b"))

    group = ConsensusGroup(client, ["x", "y"])
    result = await group.vote("Any question", method="any")

    assert result.success is True
    assert len(result.all_results) == 2
    await client.close()


# ---------------------------------------------------------------------------
# AgentRouter — matches first rule
# ---------------------------------------------------------------------------


async def test_router_matches_first_rule() -> None:
    """Router dispatches to the first matching route."""
    client, mock = await _make_client_and_mock()

    def _send_handler(params: dict[str, object] | None) -> dict[str, str]:
        session_key = (params or {}).get("sessionKey", "")
        mock.emit_event(_done_event(f"handled by {session_key}"))
        return {"runId": "run-1", "status": "started"}

    mock.register("chat.send", _send_handler)

    router = AgentRouter(client)
    router.add_route(lambda q: "code" in q.lower(), "code-reviewer")
    router.add_route(lambda q: "data" in q.lower(), "data-analyst")
    router.set_default("general")

    result = await router.route("Review this code snippet")

    assert result.success is True
    assert "code-reviewer" in result.content
    # Verify the correct agent was resolved
    assert router.resolve("Review this code snippet") == "code-reviewer"
    await client.close()


# ---------------------------------------------------------------------------
# AgentRouter — uses default
# ---------------------------------------------------------------------------


async def test_router_uses_default() -> None:
    """Router falls back to default agent when no rules match."""
    client, mock = await _make_client_and_mock()

    def _send_handler(params: dict[str, object] | None) -> dict[str, str]:
        session_key = (params or {}).get("sessionKey", "")
        mock.emit_event(_done_event(f"default: {session_key}"))
        return {"runId": "run-1", "status": "started"}

    mock.register("chat.send", _send_handler)

    router = AgentRouter(client)
    router.add_route(lambda q: "xyz123" in q, "niche-agent")
    router.set_default("fallback-agent")

    result = await router.route("Hello there!")

    assert result.success is True
    assert "fallback-agent" in result.content
    assert router.resolve("Hello there!") == "fallback-agent"
    await client.close()


# ---------------------------------------------------------------------------
# AgentRouter — no match and no default raises
# ---------------------------------------------------------------------------


def test_router_no_match_no_default_raises() -> None:
    """Router raises ValueError when no route matches and no default is set."""
    mock = MockGateway()
    client = OpenClawClient(config=ClientConfig(), gateway=mock)

    router = AgentRouter(client)
    router.add_route(lambda q: "specific" in q, "specific-agent")

    with pytest.raises(ValueError, match="No route matched"):
        router.resolve("unmatched query")
