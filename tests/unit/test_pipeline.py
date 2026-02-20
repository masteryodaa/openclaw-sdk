"""Tests for pipeline/pipeline.py."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from openclaw_sdk.core.types import ExecutionResult, GeneratedFile
from openclaw_sdk.pipeline.pipeline import Pipeline, PipelineResult


# ---------------------------------------------------------------------------
# Helpers / mock client
# ---------------------------------------------------------------------------


def _make_result(
    content: str = "result content",
    success: bool = True,
    files: list[GeneratedFile] | None = None,
) -> ExecutionResult:
    return ExecutionResult(
        success=success,
        content=content,
        files=files or [],
        latency_ms=100,
    )


class MockAgent:
    """Fake agent that returns a fixed result."""

    def __init__(self, result: ExecutionResult) -> None:
        self._result = result
        self.execute = AsyncMock(return_value=result)


class MockClient:
    """Fake client with registered agents."""

    def __init__(self) -> None:
        self._agents: dict[str, MockAgent] = {}

    def register(self, agent_id: str, result: ExecutionResult) -> MockAgent:
        agent = MockAgent(result)
        self._agents[agent_id] = agent
        return agent

    def get_agent(self, agent_id: str) -> MockAgent:
        return self._agents[agent_id]


# ---------------------------------------------------------------------------
# add_step() — method chaining
# ---------------------------------------------------------------------------


def test_add_step_returns_self() -> None:
    client = MockClient()
    pipeline = Pipeline(client)
    returned = pipeline.add_step("step1", "agent1", "hello")
    assert returned is pipeline


def test_add_step_chaining_multiple() -> None:
    client = MockClient()
    pipeline = (
        Pipeline(client)
        .add_step("step1", "agent1", "first")
        .add_step("step2", "agent2", "second")
        .add_step("step3", "agent3", "third")
    )
    assert len(pipeline._steps) == 3


def test_add_step_records_output_key() -> None:
    client = MockClient()
    pipeline = Pipeline(client)
    pipeline.add_step("s1", "a1", "p", output_key="thinking")
    assert pipeline._steps[0].output_key == "thinking"


# ---------------------------------------------------------------------------
# run() — single step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_single_step() -> None:
    client = MockClient()
    agent = client.register("agent1", _make_result(content="hello world"))
    pipeline = Pipeline(client).add_step("step1", "agent1", "Say hello")

    result = await pipeline.run()

    assert result.success is True
    assert result.final_result.content == "hello world"
    assert "step1" in result.steps
    agent.execute.assert_called_once_with("Say hello")


@pytest.mark.asyncio
async def test_run_returns_pipeline_result() -> None:
    client = MockClient()
    client.register("agent1", _make_result())
    pipeline = Pipeline(client).add_step("step1", "agent1", "prompt")
    result = await pipeline.run()
    assert isinstance(result, PipelineResult)


@pytest.mark.asyncio
async def test_run_total_latency_ms_is_set() -> None:
    client = MockClient()
    client.register("agent1", _make_result())
    pipeline = Pipeline(client).add_step("step1", "agent1", "prompt")
    result = await pipeline.run()
    assert result.total_latency_ms >= 0


# ---------------------------------------------------------------------------
# run() — variable substitution from initial kwargs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_variable_substitution_from_initial_kwargs() -> None:
    client = MockClient()
    agent = client.register("agent1", _make_result(content="done"))
    pipeline = Pipeline(client).add_step("step1", "agent1", "Write about {topic}")

    await pipeline.run(topic="Python")

    agent.execute.assert_called_once_with("Write about Python")


@pytest.mark.asyncio
async def test_run_multiple_variables_in_prompt() -> None:
    client = MockClient()
    agent = client.register("agent1", _make_result())
    pipeline = Pipeline(client).add_step("step1", "agent1", "{greeting} {name}!")

    await pipeline.run(greeting="Hello", name="World")

    agent.execute.assert_called_once_with("Hello World!")


# ---------------------------------------------------------------------------
# run() — step output feeds next step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_step_output_feeds_next_step() -> None:
    client = MockClient()
    agent1 = client.register("agent1", _make_result(content="topic: AI"))
    agent2 = client.register("agent2", _make_result(content="article about AI"))

    pipeline = (
        Pipeline(client)
        .add_step("researcher", "agent1", "Research AI")
        .add_step("writer", "agent2", "Write based on: {researcher}")
    )

    result = await pipeline.run()

    assert result.success is True
    agent2.execute.assert_called_once_with("Write based on: topic: AI")
    assert result.final_result.content == "article about AI"


@pytest.mark.asyncio
async def test_run_three_step_chain() -> None:
    client = MockClient()
    client.register("a1", _make_result(content="research output"))
    client.register("a2", _make_result(content="draft output"))
    agent3 = client.register("a3", _make_result(content="final output"))

    pipeline = (
        Pipeline(client)
        .add_step("step1", "a1", "Do research")
        .add_step("step2", "a2", "Write draft from {step1}")
        .add_step("step3", "a3", "Review {step2} using {step1}")
    )

    result = await pipeline.run()

    assert result.success is True
    agent3.execute.assert_called_once_with("Review draft output using research output")
    assert result.final_result.content == "final output"


@pytest.mark.asyncio
async def test_run_initial_variable_and_step_output_together() -> None:
    client = MockClient()
    agent1 = client.register("a1", _make_result(content="expanded topic"))
    agent2 = client.register("a2", _make_result(content="final answer"))

    pipeline = (
        Pipeline(client)
        .add_step("expand", "a1", "Expand on {topic}")
        .add_step("answer", "a2", "Answer {topic} using {expand}")
    )

    result = await pipeline.run(topic="Python")

    agent1.execute.assert_called_once_with("Expand on Python")
    agent2.execute.assert_called_once_with("Answer Python using expanded topic")
    assert result.success is True


# ---------------------------------------------------------------------------
# run() — stops on failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_stops_on_failure() -> None:
    client = MockClient()
    client.register("a1", _make_result(content="ok", success=False))
    agent2 = client.register("a2", _make_result(content="should not run"))

    pipeline = (
        Pipeline(client)
        .add_step("step1", "a1", "do something")
        .add_step("step2", "a2", "do more")
    )

    result = await pipeline.run()

    assert result.success is False
    assert "step1" in result.steps
    assert "step2" not in result.steps
    # Second agent must NOT have been called
    agent2.execute.assert_not_called()


@pytest.mark.asyncio
async def test_run_failure_result_has_failed_step_as_final() -> None:
    client = MockClient()
    failed_result = _make_result(content="error occurred", success=False)
    client.register("a1", failed_result)
    client.register("a2", _make_result())

    pipeline = (
        Pipeline(client)
        .add_step("step1", "a1", "prompt")
        .add_step("step2", "a2", "prompt2")
    )

    result = await pipeline.run()

    assert result.final_result.content == "error occurred"


# ---------------------------------------------------------------------------
# run() — collected files
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_collects_files_from_all_steps() -> None:
    file1 = GeneratedFile(name="a.txt", path="/tmp/a.txt", size_bytes=10, mime_type="text/plain")
    file2 = GeneratedFile(name="b.txt", path="/tmp/b.txt", size_bytes=20, mime_type="text/plain")

    client = MockClient()
    client.register("a1", _make_result(content="step1", files=[file1]))
    client.register("a2", _make_result(content="step2", files=[file2]))

    pipeline = (
        Pipeline(client)
        .add_step("step1", "a1", "prompt1")
        .add_step("step2", "a2", "prompt2")
    )

    result = await pipeline.run()

    assert result.success is True
    assert len(result.all_files) == 2
    assert file1 in result.all_files
    assert file2 in result.all_files
