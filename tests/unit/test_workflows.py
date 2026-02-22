"""Tests for workflows/ — Workflow engine, models, and presets."""
from __future__ import annotations

from typing import Any

from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.types import ExecutionResult, StreamEvent
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.workflows.engine import Workflow
from openclaw_sdk.workflows.models import (
    StepStatus,
    StepType,
    WorkflowResult,
    WorkflowStep,
)
from openclaw_sdk.workflows.presets import (
    research_workflow,
    review_workflow,
    support_workflow,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeAgent:
    """Minimal agent-like object for tests that don't need the full gateway."""

    def __init__(self, content: str = "result", success: bool = True) -> None:
        self._content = content
        self._success = success

    async def execute(self, query: str) -> ExecutionResult:
        return ExecutionResult(success=self._success, content=self._content)


def _fake_factory(
    responses: dict[str, str] | None = None,
    success: bool = True,
) -> Any:
    """Return an agent_factory that maps agent_id -> _FakeAgent."""
    _responses = responses or {}

    def factory(agent_id: str) -> _FakeAgent:
        content = _responses.get(agent_id, f"response from {agent_id}")
        return _FakeAgent(content=content, success=success)

    return factory


async def _make_mock_factory(
    responses: dict[str, str] | None = None,
) -> Any:
    """Create a factory using real MockGateway + OpenClawClient for realistic tests."""
    _responses = responses or {}
    gateways: dict[str, tuple[MockGateway, OpenClawClient]] = {}

    for agent_id, content in _responses.items():
        mock = MockGateway()
        mock.register("chat.send", {"runId": f"r-{agent_id}", "status": "started"})
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"content": content}},
            )
        )
        client = OpenClawClient(config=ClientConfig(), gateway=mock)
        await mock.connect()
        gateways[agent_id] = (mock, client)

    def factory(agent_id: str) -> Any:
        if agent_id in gateways:
            _, client = gateways[agent_id]
            return client.get_agent(agent_id)
        # Fallback for unknown agents
        return _FakeAgent(content=f"response from {agent_id}")

    return factory


# ---------------------------------------------------------------------------
# WorkflowStep model tests
# ---------------------------------------------------------------------------


class TestWorkflowStepModel:
    """Tests for WorkflowStep Pydantic model."""

    def test_defaults(self) -> None:
        step = WorkflowStep(name="s1", step_type=StepType.AGENT)
        assert step.name == "s1"
        assert step.step_type == StepType.AGENT
        assert step.config == {}
        assert step.status == StepStatus.PENDING
        assert step.result is None
        assert step.next_on_success is None
        assert step.next_on_failure is None

    def test_full_construction(self) -> None:
        step = WorkflowStep(
            name="review",
            step_type=StepType.CONDITION,
            config={"key": "score", "operator": "gt", "value": 0.5},
            status=StepStatus.COMPLETED,
            result="passed",
            next_on_success="done",
            next_on_failure="retry",
        )
        assert step.name == "review"
        assert step.step_type == StepType.CONDITION
        assert step.config["key"] == "score"
        assert step.status == StepStatus.COMPLETED
        assert step.result == "passed"
        assert step.next_on_success == "done"
        assert step.next_on_failure == "retry"

    def test_step_type_enum_values(self) -> None:
        assert StepType.AGENT == "agent"
        assert StepType.CONDITION == "condition"
        assert StepType.APPROVAL == "approval"
        assert StepType.TRANSFORM == "transform"

    def test_step_status_enum_values(self) -> None:
        assert StepStatus.PENDING == "pending"
        assert StepStatus.RUNNING == "running"
        assert StepStatus.COMPLETED == "completed"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.SKIPPED == "skipped"


# ---------------------------------------------------------------------------
# WorkflowResult model tests
# ---------------------------------------------------------------------------


class TestWorkflowResultModel:
    """Tests for WorkflowResult Pydantic model."""

    def test_defaults(self) -> None:
        result = WorkflowResult(success=True, steps=[])
        assert result.success is True
        assert result.steps == []
        assert result.final_output is None
        assert result.latency_ms == 0

    def test_full_construction(self) -> None:
        step = WorkflowStep(name="s1", step_type=StepType.AGENT, status=StepStatus.COMPLETED)
        result = WorkflowResult(
            success=True,
            steps=[step],
            final_output="done",
            latency_ms=150,
        )
        assert result.success is True
        assert len(result.steps) == 1
        assert result.final_output == "done"
        assert result.latency_ms == 150


# ---------------------------------------------------------------------------
# Workflow engine tests
# ---------------------------------------------------------------------------


class TestWorkflowEngine:
    """Tests for the Workflow engine."""

    async def test_empty_workflow(self) -> None:
        wf = Workflow("empty", [])
        result = await wf.run({})
        assert result.success is True
        assert result.steps == []
        assert result.final_output is None

    async def test_repr(self) -> None:
        wf = Workflow("test", [
            WorkflowStep(name="s1", step_type=StepType.AGENT),
        ])
        assert "test" in repr(wf)
        assert "1" in repr(wf)

    async def test_steps_property(self) -> None:
        steps = [
            WorkflowStep(name="a", step_type=StepType.AGENT),
            WorkflowStep(name="b", step_type=StepType.TRANSFORM),
        ]
        wf = Workflow("test", steps)
        assert len(wf.steps) == 2
        assert wf.steps[0].name == "a"
        assert wf.steps[1].name == "b"

    async def test_linear_agent_workflow(self) -> None:
        """Three agent steps executed in order."""
        steps = [
            WorkflowStep(
                name="step1",
                step_type=StepType.AGENT,
                config={"agent_id": "a1", "query": "question 1"},
            ),
            WorkflowStep(
                name="step2",
                step_type=StepType.AGENT,
                config={"agent_id": "a2", "query": "question 2"},
            ),
            WorkflowStep(
                name="step3",
                step_type=StepType.AGENT,
                config={"agent_id": "a3", "query": "question 3"},
            ),
        ]
        factory = _fake_factory({
            "a1": "result1",
            "a2": "result2",
            "a3": "result3",
        })
        wf = Workflow("linear", steps)
        result = await wf.run({}, agent_factory=factory)

        assert result.success is True
        assert len(result.steps) == 3
        for step in result.steps:
            assert step.status == StepStatus.COMPLETED
        assert result.final_output == "result3"

    async def test_context_passing_between_steps(self) -> None:
        """Results from one step are available in the next step's context."""
        steps = [
            WorkflowStep(
                name="research",
                step_type=StepType.AGENT,
                config={"agent_id": "researcher", "query": "research {topic}"},
            ),
            WorkflowStep(
                name="summarize",
                step_type=StepType.AGENT,
                config={"agent_id": "summarizer", "query": "summarize {research}"},
            ),
        ]
        factory = _fake_factory({
            "researcher": "research findings",
            "summarizer": "summary of findings",
        })
        ctx: dict[str, Any] = {"topic": "AI"}
        wf = Workflow("pipeline", steps)
        result = await wf.run(ctx, agent_factory=factory)

        assert result.success is True
        # Context should contain results from both steps
        assert ctx["research"] == "research findings"
        assert ctx["summarize"] == "summary of findings"

    async def test_condition_success_branch(self) -> None:
        """Condition step evaluates to True, follows next_on_success."""
        steps = [
            WorkflowStep(
                name="check",
                step_type=StepType.CONDITION,
                config={"key": "score", "operator": "gt", "value": 0.5},
                next_on_success="success_step",
            ),
            WorkflowStep(
                name="fail_step",
                step_type=StepType.AGENT,
                config={"agent_id": "a1", "query": "fallback"},
            ),
            WorkflowStep(
                name="success_step",
                step_type=StepType.AGENT,
                config={"agent_id": "a2", "query": "success"},
            ),
        ]
        factory = _fake_factory({"a2": "success!"})
        wf = Workflow("cond", steps)
        result = await wf.run({"score": 0.8}, agent_factory=factory)

        assert result.success is True
        # Should have jumped from check to success_step, skipping fail_step
        check_step = result.steps[0]
        assert check_step.status == StepStatus.COMPLETED

        success_step = result.steps[2]
        assert success_step.status == StepStatus.COMPLETED
        assert result.final_output == "success!"

    async def test_condition_failure_branch(self) -> None:
        """Condition step evaluates to False, follows next_on_failure."""
        steps = [
            WorkflowStep(
                name="check",
                step_type=StepType.CONDITION,
                config={"key": "score", "operator": "gt", "value": 0.5},
                next_on_failure="fail_handler",
            ),
            WorkflowStep(
                name="normal_step",
                step_type=StepType.AGENT,
                config={"agent_id": "a1", "query": "normal"},
            ),
            WorkflowStep(
                name="fail_handler",
                step_type=StepType.AGENT,
                config={"agent_id": "a2", "query": "handle failure"},
            ),
        ]
        factory = _fake_factory({"a2": "handled"})
        wf = Workflow("cond-fail", steps)
        result = await wf.run({"score": 0.2}, agent_factory=factory)

        # Condition failed -> jumped to fail_handler
        check_step = result.steps[0]
        assert check_step.status == StepStatus.FAILED

        fail_handler = result.steps[2]
        assert fail_handler.status == StepStatus.COMPLETED
        assert result.final_output == "handled"

    async def test_condition_operators(self) -> None:
        """Test various condition operators."""
        operators_and_results = [
            ("eq", 5, 5, True),
            ("eq", 5, 6, False),
            ("ne", 5, 6, True),
            ("ne", 5, 5, False),
            ("gt", 10, 5, True),
            ("gt", 5, 10, False),
            ("gte", 5, 5, True),
            ("gte", 4, 5, False),
            ("lt", 3, 5, True),
            ("lt", 5, 3, False),
            ("lte", 5, 5, True),
            ("lte", 6, 5, False),
            ("contains", "hello world", "world", True),
            ("contains", "hello", "xyz", False),
        ]
        for operator, actual, expected, should_pass in operators_and_results:
            steps = [
                WorkflowStep(
                    name="check",
                    step_type=StepType.CONDITION,
                    config={"key": "val", "operator": operator, "value": expected},
                ),
            ]
            wf = Workflow("op-test", steps)
            result = await wf.run({"val": actual})
            assert result.success is should_pass, (
                f"operator={operator}, actual={actual}, expected={expected}: "
                f"got success={result.success}, want {should_pass}"
            )

    async def test_transform_with_callable(self) -> None:
        """TRANSFORM step applies a callable to the context."""
        def my_transform(ctx: dict[str, Any]) -> dict[str, Any]:
            return {"upper_topic": ctx.get("topic", "").upper()}

        steps = [
            WorkflowStep(
                name="transform",
                step_type=StepType.TRANSFORM,
                config={"transform": my_transform},
            ),
        ]
        ctx: dict[str, Any] = {"topic": "hello"}
        wf = Workflow("transform-test", steps)
        result = await wf.run(ctx)

        assert result.success is True
        assert ctx["upper_topic"] == "HELLO"
        assert result.steps[0].status == StepStatus.COMPLETED

    async def test_transform_with_mapping(self) -> None:
        """TRANSFORM step applies a key mapping to the context."""
        steps = [
            WorkflowStep(
                name="rename",
                step_type=StepType.TRANSFORM,
                config={"mapping": {"old_key": "new_key"}},
            ),
        ]
        ctx: dict[str, Any] = {"old_key": "value123"}
        wf = Workflow("mapping-test", steps)
        result = await wf.run(ctx)

        assert result.success is True
        assert ctx["new_key"] == "value123"
        # Original key is preserved
        assert ctx["old_key"] == "value123"

    async def test_transform_no_config(self) -> None:
        """TRANSFORM step with no transform/mapping passes through."""
        steps = [
            WorkflowStep(
                name="passthrough",
                step_type=StepType.TRANSFORM,
                config={},
            ),
        ]
        wf = Workflow("pass", steps)
        result = await wf.run({"x": 1})

        assert result.success is True
        assert result.steps[0].status == StepStatus.COMPLETED

    async def test_approval_auto_approve(self) -> None:
        """APPROVAL step with auto_approve=True succeeds."""
        steps = [
            WorkflowStep(
                name="approve",
                step_type=StepType.APPROVAL,
                config={"auto_approve": True},
            ),
        ]
        wf = Workflow("approval", steps)
        result = await wf.run({})

        assert result.success is True
        assert result.steps[0].status == StepStatus.COMPLETED
        assert result.steps[0].result is True

    async def test_approval_not_approved(self) -> None:
        """APPROVAL step with auto_approve=False fails."""
        steps = [
            WorkflowStep(
                name="approve",
                step_type=StepType.APPROVAL,
                config={"auto_approve": False},
            ),
        ]
        wf = Workflow("approval-denied", steps)
        result = await wf.run({})

        assert result.success is False
        assert result.steps[0].status == StepStatus.FAILED
        assert result.steps[0].result is False

    async def test_approval_default_not_approved(self) -> None:
        """APPROVAL step without auto_approve defaults to not approved."""
        steps = [
            WorkflowStep(
                name="approve",
                step_type=StepType.APPROVAL,
                config={},
            ),
        ]
        wf = Workflow("approval-default", steps)
        result = await wf.run({})

        assert result.success is False
        assert result.steps[0].status == StepStatus.FAILED

    async def test_agent_step_failure(self) -> None:
        """Agent step returning success=False marks step as FAILED."""
        steps = [
            WorkflowStep(
                name="failing",
                step_type=StepType.AGENT,
                config={"agent_id": "fail-bot", "query": "do something"},
            ),
        ]
        factory = _fake_factory(success=False)
        wf = Workflow("fail", steps)
        result = await wf.run({}, agent_factory=factory)

        assert result.success is False
        assert result.steps[0].status == StepStatus.FAILED

    async def test_agent_step_exception(self) -> None:
        """Agent step that raises an exception marks step as FAILED."""

        class _ErrorAgent:
            async def execute(self, query: str) -> ExecutionResult:
                raise RuntimeError("agent crashed")

        def error_factory(agent_id: str) -> _ErrorAgent:
            return _ErrorAgent()

        steps = [
            WorkflowStep(
                name="crash",
                step_type=StepType.AGENT,
                config={"agent_id": "crasher", "query": "go"},
            ),
        ]
        wf = Workflow("error", steps)
        result = await wf.run({}, agent_factory=error_factory)

        assert result.success is False
        assert result.steps[0].status == StepStatus.FAILED
        assert "agent crashed" in str(result.steps[0].result)

    async def test_no_agent_factory_for_agent_step(self) -> None:
        """AGENT step without agent_factory fails gracefully."""
        steps = [
            WorkflowStep(
                name="agent",
                step_type=StepType.AGENT,
                config={"agent_id": "bot", "query": "hello"},
            ),
        ]
        wf = Workflow("no-factory", steps)
        result = await wf.run({})

        assert result.success is False
        assert result.steps[0].status == StepStatus.FAILED

    async def test_latency_tracked(self) -> None:
        """WorkflowResult.latency_ms is non-negative."""
        wf = Workflow("empty", [])
        result = await wf.run({})
        assert result.latency_ms >= 0

    async def test_workflow_with_mock_gateway(self) -> None:
        """Integration test using real MockGateway + OpenClawClient."""
        factory = await _make_mock_factory({
            "bot1": "hello from bot1",
        })
        steps = [
            WorkflowStep(
                name="greet",
                step_type=StepType.AGENT,
                config={"agent_id": "bot1", "query": "say hello"},
            ),
        ]
        wf = Workflow("mock-test", steps)
        result = await wf.run({}, agent_factory=factory)

        assert result.success is True
        assert result.final_output == "hello from bot1"


# ---------------------------------------------------------------------------
# Preset workflow tests
# ---------------------------------------------------------------------------


class TestPresetWorkflows:
    """Tests for pre-built workflow configurations."""

    def test_review_workflow_structure(self) -> None:
        wf = review_workflow("reviewer-1", "author-1")
        assert wf.name == "review"
        assert len(wf.steps) == 3
        assert wf.steps[0].step_type == StepType.AGENT
        assert wf.steps[0].name == "review"
        assert wf.steps[1].step_type == StepType.CONDITION
        assert wf.steps[1].name == "check_pass"
        assert wf.steps[2].step_type == StepType.AGENT
        assert wf.steps[2].name == "revise"
        assert wf.steps[0].config["agent_id"] == "reviewer-1"
        assert wf.steps[2].config["agent_id"] == "author-1"

    def test_research_workflow_structure(self) -> None:
        wf = research_workflow("researcher-1", "summarizer-1")
        assert wf.name == "research"
        assert len(wf.steps) == 3
        assert wf.steps[0].step_type == StepType.AGENT
        assert wf.steps[0].name == "research"
        assert wf.steps[1].step_type == StepType.TRANSFORM
        assert wf.steps[1].name == "extract"
        assert wf.steps[2].step_type == StepType.AGENT
        assert wf.steps[2].name == "summarize"
        assert wf.steps[0].config["agent_id"] == "researcher-1"
        assert wf.steps[2].config["agent_id"] == "summarizer-1"

    def test_support_workflow_structure(self) -> None:
        wf = support_workflow("triage-1", "support-1")
        assert wf.name == "support"
        assert len(wf.steps) == 3
        assert wf.steps[0].step_type == StepType.AGENT
        assert wf.steps[0].name == "triage"
        assert wf.steps[1].step_type == StepType.CONDITION
        assert wf.steps[1].name == "check_priority"
        assert wf.steps[2].step_type == StepType.AGENT
        assert wf.steps[2].name == "detailed_support"
        assert wf.steps[0].config["agent_id"] == "triage-1"
        assert wf.steps[2].config["agent_id"] == "support-1"

    async def test_review_workflow_runs(self) -> None:
        """Review workflow completes when review_passed=True."""
        factory = _fake_factory({"reviewer-1": "LGTM!", "author-1": "revised"})
        wf = review_workflow("reviewer-1", "author-1")
        ctx: dict[str, Any] = {"document": "my code", "review_passed": True}
        result = await wf.run(ctx, agent_factory=factory)

        # review step completes, condition passes, workflow ends
        assert result.steps[0].status == StepStatus.COMPLETED

    async def test_research_workflow_runs(self) -> None:
        """Research workflow completes all three steps."""
        factory = _fake_factory({
            "researcher-1": "found interesting data",
            "summarizer-1": "summary: interesting data",
        })
        wf = research_workflow("researcher-1", "summarizer-1")
        ctx: dict[str, Any] = {"topic": "quantum computing"}
        result = await wf.run(ctx, agent_factory=factory)

        assert result.success is True
        # All 3 steps should complete
        for step in result.steps:
            assert step.status == StepStatus.COMPLETED
        # Transform should have created 'findings' key
        assert ctx.get("findings") is not None

    async def test_support_workflow_runs(self) -> None:
        """Support workflow with high priority triggers detailed support."""
        factory = _fake_factory({
            "triage-1": "urgent issue",
            "support-1": "detailed help",
        })
        wf = support_workflow("triage-1", "support-1")
        ctx: dict[str, Any] = {"request": "my account is locked", "priority": "high"}
        result = await wf.run(ctx, agent_factory=factory)

        # triage completes, condition passes (priority == high),
        # then detailed_support should also run
        assert result.steps[0].status == StepStatus.COMPLETED
