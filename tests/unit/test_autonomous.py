"""Tests for autonomous/ — Goal, Budget, GoalLoop, Orchestrator, Watchdog."""

from __future__ import annotations

import pytest

from openclaw_sdk.autonomous.goal_loop import GoalLoop
from openclaw_sdk.autonomous.models import Budget, Goal, GoalStatus
from openclaw_sdk.autonomous.orchestrator import AgentCapability, Orchestrator
from openclaw_sdk.autonomous.watchdog import Watchdog, WatchdogAction
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.types import ExecutionResult, StreamEvent
from openclaw_sdk.gateway.mock import MockGateway

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_client_and_mock() -> tuple[OpenClawClient, MockGateway]:
    mock = MockGateway()
    await mock.connect()
    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    return client, mock


def _emit_done(mock: MockGateway, content: str = "done") -> None:
    """Emit a DONE event on the mock gateway."""
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"content": content, "state": "final"}},
        )
    )


def _emit_error(mock: MockGateway, message: str = "error") -> None:
    """Emit an ERROR event on the mock gateway."""
    mock.emit_event(
        StreamEvent(
            event_type=EventType.ERROR,
            data={"payload": {"message": message}},
        )
    )


# ===========================================================================
# Goal model tests
# ===========================================================================


class TestGoal:
    def test_default_status(self) -> None:
        goal = Goal(description="Write a report")
        assert goal.status == GoalStatus.PENDING

    def test_sub_goals_default_empty(self) -> None:
        goal = Goal(description="Root goal")
        assert goal.sub_goals == []

    def test_sub_goals(self) -> None:
        child = Goal(description="Sub-task A")
        goal = Goal(description="Parent", sub_goals=[child])
        assert len(goal.sub_goals) == 1
        assert goal.sub_goals[0].description == "Sub-task A"

    def test_max_steps_default(self) -> None:
        goal = Goal(description="Test")
        assert goal.max_steps == 10

    def test_max_steps_custom(self) -> None:
        goal = Goal(description="Test", max_steps=5)
        assert goal.max_steps == 5

    def test_result_default_none(self) -> None:
        goal = Goal(description="Test")
        assert goal.result is None

    def test_metadata_default_empty(self) -> None:
        goal = Goal(description="Test")
        assert goal.metadata == {}

    def test_metadata_custom(self) -> None:
        goal = Goal(description="Test", metadata={"priority": "high"})
        assert goal.metadata["priority"] == "high"


# ===========================================================================
# Budget model tests
# ===========================================================================


class TestBudget:
    def test_is_exhausted_cost(self) -> None:
        budget = Budget(max_cost_usd=1.0, cost_spent=1.0)
        assert budget.is_exhausted is True

    def test_is_exhausted_tokens(self) -> None:
        budget = Budget(max_tokens=100, tokens_spent=100)
        assert budget.is_exhausted is True

    def test_is_exhausted_duration(self) -> None:
        budget = Budget(max_duration_seconds=60.0, duration_spent=60.0)
        assert budget.is_exhausted is True

    def test_is_exhausted_tool_calls(self) -> None:
        budget = Budget(max_tool_calls=5, tool_calls_spent=5)
        assert budget.is_exhausted is True

    def test_is_exhausted_over_limit(self) -> None:
        budget = Budget(max_cost_usd=1.0, cost_spent=1.5)
        assert budget.is_exhausted is True

    def test_not_exhausted_under_limit(self) -> None:
        budget = Budget(max_cost_usd=1.0, cost_spent=0.5)
        assert budget.is_exhausted is False

    def test_not_exhausted_no_limits(self) -> None:
        """Unlimited budget is never exhausted."""
        budget = Budget()
        assert budget.is_exhausted is False

    def test_remaining_cost(self) -> None:
        budget = Budget(max_cost_usd=10.0, cost_spent=3.0)
        assert budget.remaining_cost == 7.0

    def test_remaining_cost_none_when_unlimited(self) -> None:
        budget = Budget()
        assert budget.remaining_cost is None

    def test_remaining_cost_floor_zero(self) -> None:
        budget = Budget(max_cost_usd=1.0, cost_spent=5.0)
        assert budget.remaining_cost == 0.0

    def test_remaining_tokens(self) -> None:
        budget = Budget(max_tokens=1000, tokens_spent=400)
        assert budget.remaining_tokens == 600

    def test_remaining_tokens_none_when_unlimited(self) -> None:
        budget = Budget()
        assert budget.remaining_tokens is None

    def test_remaining_tokens_floor_zero(self) -> None:
        budget = Budget(max_tokens=100, tokens_spent=200)
        assert budget.remaining_tokens == 0


# ===========================================================================
# Watchdog tests
# ===========================================================================


class TestWatchdog:
    def test_continue_under_limits(self) -> None:
        budget = Budget(max_cost_usd=10.0, cost_spent=1.0)
        watchdog = Watchdog(budget)
        assert watchdog.check() == WatchdogAction.CONTINUE

    def test_continue_no_limits(self) -> None:
        budget = Budget()
        watchdog = Watchdog(budget)
        assert watchdog.check() == WatchdogAction.CONTINUE

    def test_warn_at_80_percent_cost(self) -> None:
        budget = Budget(max_cost_usd=10.0, cost_spent=8.0)
        watchdog = Watchdog(budget)
        assert watchdog.check() == WatchdogAction.WARN

    def test_warn_at_80_percent_tokens(self) -> None:
        budget = Budget(max_tokens=1000, tokens_spent=800)
        watchdog = Watchdog(budget)
        assert watchdog.check() == WatchdogAction.WARN

    def test_warn_at_80_percent_duration(self) -> None:
        budget = Budget(max_duration_seconds=100.0, duration_spent=80.0)
        watchdog = Watchdog(budget)
        assert watchdog.check() == WatchdogAction.WARN

    def test_warn_at_80_percent_tool_calls(self) -> None:
        budget = Budget(max_tool_calls=10, tool_calls_spent=8)
        watchdog = Watchdog(budget)
        assert watchdog.check() == WatchdogAction.WARN

    def test_stop_when_exhausted(self) -> None:
        budget = Budget(max_cost_usd=1.0, cost_spent=1.0)
        watchdog = Watchdog(budget)
        assert watchdog.check() == WatchdogAction.STOP

    def test_stop_takes_priority_over_warn(self) -> None:
        """When both exhausted and over threshold, STOP wins."""
        budget = Budget(max_cost_usd=1.0, cost_spent=1.5)
        watchdog = Watchdog(budget)
        assert watchdog.check() == WatchdogAction.STOP


# ===========================================================================
# GoalLoop tests
# ===========================================================================


class TestGoalLoop:
    async def test_successful_single_step(self) -> None:
        """GoalLoop completes on first successful execution (no predicate)."""
        client, mock = await _make_client_and_mock()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        _emit_done(mock, "answer")

        agent = client.get_agent("test")
        goal = Goal(description="Say hello", max_steps=5)
        budget = Budget(max_tokens=10000)

        loop = GoalLoop(agent, goal, budget)
        result_goal = await loop.run()

        assert result_goal.status == GoalStatus.COMPLETED
        assert result_goal.result == "answer"
        await client.close()

    async def test_multi_step_with_predicate(self) -> None:
        """GoalLoop retries until predicate passes."""
        client, mock = await _make_client_and_mock()

        call_count = 0

        def _dynamic_response(params: dict[str, object] | None) -> dict[str, object]:
            nonlocal call_count
            call_count += 1
            return {"runId": f"r{call_count}", "status": "started"}

        mock.register("chat.send", _dynamic_response)

        # First call: content does not satisfy predicate
        _emit_done(mock, "not yet")
        # Second call: content satisfies predicate
        _emit_done(mock, "DONE: result found")

        agent = client.get_agent("test")
        goal = Goal(description="Find result", max_steps=5)
        budget = Budget(max_tokens=100000)

        def predicate(r: ExecutionResult) -> bool:
            return "DONE" in r.content

        loop = GoalLoop(agent, goal, budget, success_predicate=predicate)
        result_goal = await loop.run()

        assert result_goal.status == GoalStatus.COMPLETED
        assert result_goal.result == "DONE: result found"
        assert call_count == 2
        await client.close()

    async def test_budget_exhaustion_stops_loop(self) -> None:
        """GoalLoop stops when budget is exhausted before execution."""
        client, mock = await _make_client_and_mock()
        mock.register("chat.send", {"runId": "r1", "status": "started"})

        agent = client.get_agent("test")
        goal = Goal(description="Expensive task", max_steps=5)
        # Budget already exhausted
        budget = Budget(max_cost_usd=1.0, cost_spent=2.0)

        loop = GoalLoop(agent, goal, budget)
        result_goal = await loop.run()

        assert result_goal.status == GoalStatus.FAILED
        assert result_goal.result == "Budget exhausted"
        # No chat.send calls should have been made
        assert mock.call_count("chat.send") == 0
        await client.close()

    async def test_failed_execution(self) -> None:
        """GoalLoop marks goal as FAILED when agent raises an error."""
        client, mock = await _make_client_and_mock()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        _emit_error(mock, "LLM error")

        agent = client.get_agent("test")
        goal = Goal(description="Will fail", max_steps=3)
        budget = Budget(max_tokens=10000)

        loop = GoalLoop(agent, goal, budget)
        result_goal = await loop.run()

        assert result_goal.status == GoalStatus.FAILED
        assert "error" in (result_goal.result or "").lower()
        await client.close()

    async def test_on_step_callback_called(self) -> None:
        """on_step callback is invoked after each step."""
        client, mock = await _make_client_and_mock()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        _emit_done(mock, "step-result")

        agent = client.get_agent("test")
        goal = Goal(description="Track steps", max_steps=5)
        budget = Budget()

        steps_seen: list[int] = []

        def on_step(step: int, result: ExecutionResult) -> None:
            steps_seen.append(step)

        loop = GoalLoop(agent, goal, budget, on_step=on_step)
        await loop.run()

        assert steps_seen == [1]
        await client.close()

    async def test_max_steps_reached(self) -> None:
        """GoalLoop fails after exhausting max_steps when predicate never passes."""
        client, mock = await _make_client_and_mock()

        call_count = 0

        def _dynamic_response(params: dict[str, object] | None) -> dict[str, object]:
            nonlocal call_count
            call_count += 1
            return {"runId": f"r{call_count}", "status": "started"}

        mock.register("chat.send", _dynamic_response)

        # All 3 steps return content that doesn't satisfy predicate
        _emit_done(mock, "nope1")
        _emit_done(mock, "nope2")
        _emit_done(mock, "nope3")

        agent = client.get_agent("test")
        goal = Goal(description="Never satisfied", max_steps=3)
        budget = Budget()

        def never_true(r: ExecutionResult) -> bool:
            return False

        loop = GoalLoop(agent, goal, budget, success_predicate=never_true)
        result_goal = await loop.run()

        assert result_goal.status == GoalStatus.FAILED
        assert "Max steps" in (result_goal.result or "")
        assert call_count == 3
        await client.close()


# ===========================================================================
# Orchestrator tests
# ===========================================================================


class TestOrchestrator:
    async def test_register_and_route(self) -> None:
        client, _mock = await _make_client_and_mock()
        orch = Orchestrator(client)
        orch.register_agent("researcher", "Research agent", ["research", "analysis"])
        orch.register_agent("writer", "Writing agent", ["writing", "editing"])

        goal = Goal(description="Research AI safety trends")
        agent_id = orch.route_goal(goal)
        assert agent_id == "researcher"
        await client.close()

    async def test_route_no_match(self) -> None:
        client, _mock = await _make_client_and_mock()
        orch = Orchestrator(client)
        orch.register_agent("writer", "Writing agent", ["writing"])

        goal = Goal(description="Deploy to production")
        agent_id = orch.route_goal(goal)
        assert agent_id is None
        await client.close()

    async def test_route_empty_registry(self) -> None:
        client, _mock = await _make_client_and_mock()
        orch = Orchestrator(client)

        goal = Goal(description="anything")
        agent_id = orch.route_goal(goal)
        assert agent_id is None
        await client.close()

    async def test_route_best_skill_overlap(self) -> None:
        """Agent with more matching skills wins."""
        client, _mock = await _make_client_and_mock()
        orch = Orchestrator(client)
        orch.register_agent("a1", skills=["research"])
        orch.register_agent("a2", skills=["research", "analysis"])

        goal = Goal(description="Do research and analysis")
        agent_id = orch.route_goal(goal)
        assert agent_id == "a2"
        await client.close()

    async def test_execute_with_override(self) -> None:
        client, mock = await _make_client_and_mock()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        _emit_done(mock, "overridden result")

        orch = Orchestrator(client)
        # No agents registered — override bypasses routing
        goal = Goal(description="Any task", max_steps=1)
        budget = Budget()

        result_goal = await orch.execute_goal(
            goal, budget, agent_override="custom-agent"
        )
        assert result_goal.status == GoalStatus.COMPLETED
        assert result_goal.result == "overridden result"
        await client.close()

    async def test_execute_with_routing(self) -> None:
        client, mock = await _make_client_and_mock()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        _emit_done(mock, "routed result")

        orch = Orchestrator(client)
        orch.register_agent("coder", "Coding agent", ["code", "python"])

        goal = Goal(description="Write python code", max_steps=1)
        budget = Budget()

        result_goal = await orch.execute_goal(goal, budget)
        assert result_goal.status == GoalStatus.COMPLETED
        assert result_goal.result == "routed result"
        await client.close()

    async def test_execute_no_agent_raises(self) -> None:
        """execute_goal raises ValueError when no agent can be found."""
        client, _mock = await _make_client_and_mock()
        orch = Orchestrator(client)

        goal = Goal(description="No match possible")
        budget = Budget()

        with pytest.raises(ValueError, match="No agent found"):
            await orch.execute_goal(goal, budget)
        await client.close()


# ===========================================================================
# AgentCapability model tests
# ===========================================================================


class TestAgentCapability:
    def test_defaults(self) -> None:
        cap = AgentCapability(agent_id="bot")
        assert cap.agent_id == "bot"
        assert cap.description == ""
        assert cap.skills == []

    def test_with_skills(self) -> None:
        cap = AgentCapability(
            agent_id="researcher",
            description="A research bot",
            skills=["research", "summarize"],
        )
        assert cap.skills == ["research", "summarize"]
