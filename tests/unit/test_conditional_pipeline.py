"""Tests for ConditionalPipeline in pipeline/pipeline.py."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from openclaw_sdk.core.exceptions import PipelineError
from openclaw_sdk.core.types import ExecutionResult, GeneratedFile
from openclaw_sdk.pipeline.pipeline import ConditionalPipeline, PipelineResult


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


class MockFailAgent:
    """Fake agent whose execute() raises an exception."""

    def __init__(self, error: Exception) -> None:
        self._error = error
        self.execute = AsyncMock(side_effect=error)


class MockClient:
    """Fake client with registered agents."""

    def __init__(self) -> None:
        self._agents: dict[str, MockAgent | MockFailAgent] = {}

    def register(self, agent_id: str, result: ExecutionResult) -> MockAgent:
        agent = MockAgent(result)
        self._agents[agent_id] = agent
        return agent

    def register_failing(self, agent_id: str, error: Exception) -> MockFailAgent:
        agent = MockFailAgent(error)
        self._agents[agent_id] = agent
        return agent

    def get_agent(self, agent_id: str) -> MockAgent | MockFailAgent:
        return self._agents[agent_id]


# ---------------------------------------------------------------------------
# test_sequential_steps — basic linear flow still works
# ---------------------------------------------------------------------------


async def test_sequential_steps() -> None:
    """ConditionalPipeline with only sequential steps behaves like linear Pipeline."""
    client = MockClient()
    client.register("a1", _make_result(content="step1 output"))
    agent2 = client.register("a2", _make_result(content="step2 output"))

    pipeline = (
        ConditionalPipeline(client)
        .add_step("step1", "a1", "Do research")
        .add_step("step2", "a2", "Expand on {step1}")
    )

    result = await pipeline.run()

    assert result.success is True
    assert isinstance(result, PipelineResult)
    assert "step1" in result.steps
    assert "step2" in result.steps
    assert result.final_result.content == "step2 output"
    agent2.execute.assert_called_once_with("Expand on step1 output")


async def test_sequential_single_step() -> None:
    """A single step runs and returns successfully."""
    client = MockClient()
    agent = client.register("agent1", _make_result(content="hello"))
    pipeline = ConditionalPipeline(client).add_step("s1", "agent1", "Say {greeting}")

    result = await pipeline.run(greeting="hi")

    assert result.success is True
    assert result.final_result.content == "hello"
    agent.execute.assert_called_once_with("Say hi")


async def test_sequential_empty_pipeline_raises() -> None:
    """Running a pipeline with no steps raises PipelineError."""
    client = MockClient()
    pipeline = ConditionalPipeline(client)
    with pytest.raises(PipelineError, match="no steps"):
        await pipeline.run()


async def test_sequential_method_chaining() -> None:
    """All builder methods return self for chaining."""
    client = MockClient()
    pipeline = ConditionalPipeline(client)
    returned = pipeline.add_step("s1", "a1", "prompt")
    assert returned is pipeline


# ---------------------------------------------------------------------------
# test_branch_true_path
# ---------------------------------------------------------------------------


async def test_branch_true_path() -> None:
    """When the branch condition is True, the if_true step is executed."""
    client = MockClient()
    client.register("classifier", _make_result(content="This is a complaint"))
    support_agent = client.register("support", _make_result(content="I will help you"))
    client.register("faq", _make_result(content="Here is the FAQ"))

    pipeline = (
        ConditionalPipeline(client)
        .add_step("classify", "classifier", "Classify: {input}")
        .add_branch(
            "classify",
            condition=lambda r: "complaint" in r.content.lower(),
            if_true=("handle_complaint", "support", "Handle complaint: {input}"),
            if_false=("answer_faq", "faq", "Answer FAQ: {input}"),
        )
    )

    result = await pipeline.run(input="I want a refund")

    assert result.success is True
    assert "handle_complaint" in result.steps
    assert "answer_faq" not in result.steps
    assert result.final_result.content == "I will help you"
    support_agent.execute.assert_called_once_with("Handle complaint: I want a refund")


# ---------------------------------------------------------------------------
# test_branch_false_path
# ---------------------------------------------------------------------------


async def test_branch_false_path() -> None:
    """When the branch condition is False, the if_false step is executed."""
    client = MockClient()
    client.register("classifier", _make_result(content="This is a question"))
    client.register("support", _make_result(content="I will help you"))
    faq_agent = client.register("faq", _make_result(content="Here is the FAQ"))

    pipeline = (
        ConditionalPipeline(client)
        .add_step("classify", "classifier", "Classify: {input}")
        .add_branch(
            "classify",
            condition=lambda r: "complaint" in r.content.lower(),
            if_true=("handle_complaint", "support", "Handle: {input}"),
            if_false=("answer_faq", "faq", "Answer: {input}"),
        )
    )

    result = await pipeline.run(input="What are your hours?")

    assert result.success is True
    assert "answer_faq" in result.steps
    assert "handle_complaint" not in result.steps
    assert result.final_result.content == "Here is the FAQ"
    faq_agent.execute.assert_called_once_with("Answer: What are your hours?")


async def test_branch_uses_prior_step_result() -> None:
    """Branch can use the prior step output in prompt templates."""
    client = MockClient()
    client.register("classifier", _make_result(content="category: urgent"))
    agent_urgent = client.register("urgent-handler", _make_result(content="urgent handled"))
    client.register("normal-handler", _make_result(content="normal handled"))

    pipeline = (
        ConditionalPipeline(client)
        .add_step("classify", "classifier", "Classify: {input}")
        .add_branch(
            "classify",
            condition=lambda r: "urgent" in r.content.lower(),
            if_true=("urgent", "urgent-handler", "Urgent! Classification: {classify}"),
            if_false=("normal", "normal-handler", "Normal: {classify}"),
        )
    )

    result = await pipeline.run(input="server is down")

    assert result.success is True
    agent_urgent.execute.assert_called_once_with("Urgent! Classification: category: urgent")


async def test_branch_missing_after_step_returns_failure() -> None:
    """Referencing a non-existent step in a branch returns failure."""
    client = MockClient()
    client.register("agent1", _make_result(content="ok"))

    pipeline = (
        ConditionalPipeline(client)
        .add_branch(
            "nonexistent",
            condition=lambda r: True,
            if_true=("a", "agent1", "prompt"),
            if_false=("b", "agent1", "prompt"),
        )
    )

    result = await pipeline.run()

    assert result.success is False
    assert "nonexistent" in result.final_result.content


# ---------------------------------------------------------------------------
# test_parallel_execution
# ---------------------------------------------------------------------------


async def test_parallel_execution() -> None:
    """Parallel steps run concurrently and all results are captured."""
    client = MockClient()
    agent_a = client.register("agent-a", _make_result(content="result A"))
    agent_b = client.register("agent-b", _make_result(content="result B"))
    agent_c = client.register("agent-c", _make_result(content="result C"))

    pipeline = ConditionalPipeline(client).add_parallel(
        [
            ("task_a", "agent-a", "Do task A for {topic}"),
            ("task_b", "agent-b", "Do task B for {topic}"),
            ("task_c", "agent-c", "Do task C for {topic}"),
        ]
    )

    result = await pipeline.run(topic="AI")

    assert result.success is True
    assert "task_a" in result.steps
    assert "task_b" in result.steps
    assert "task_c" in result.steps
    assert result.steps["task_a"].content == "result A"
    assert result.steps["task_b"].content == "result B"
    assert result.steps["task_c"].content == "result C"

    agent_a.execute.assert_called_once_with("Do task A for AI")
    agent_b.execute.assert_called_once_with("Do task B for AI")
    agent_c.execute.assert_called_once_with("Do task C for AI")


async def test_parallel_results_available_to_subsequent_steps() -> None:
    """Parallel step outputs become variables for subsequent steps."""
    client = MockClient()
    client.register("agent-a", _make_result(content="parallel A"))
    client.register("agent-b", _make_result(content="parallel B"))
    summarizer = client.register("summarizer", _make_result(content="summary"))

    pipeline = (
        ConditionalPipeline(client)
        .add_parallel(
            [
                ("research", "agent-a", "Research {topic}"),
                ("analysis", "agent-b", "Analyze {topic}"),
            ]
        )
        .add_step("summary", "summarizer", "Summarize: {research} and {analysis}")
    )

    result = await pipeline.run(topic="AI")

    assert result.success is True
    summarizer.execute.assert_called_once_with("Summarize: parallel A and parallel B")


async def test_parallel_collects_files() -> None:
    """Files from parallel steps are collected in all_files."""
    file1 = GeneratedFile(name="a.txt", path="/tmp/a.txt", size_bytes=10, mime_type="text/plain")
    file2 = GeneratedFile(name="b.txt", path="/tmp/b.txt", size_bytes=20, mime_type="text/plain")

    client = MockClient()
    client.register("a1", _make_result(content="r1", files=[file1]))
    client.register("a2", _make_result(content="r2", files=[file2]))

    pipeline = ConditionalPipeline(client).add_parallel(
        [("s1", "a1", "go"), ("s2", "a2", "go")]
    )

    result = await pipeline.run()

    assert result.success is True
    assert len(result.all_files) == 2
    assert file1 in result.all_files
    assert file2 in result.all_files


# ---------------------------------------------------------------------------
# test_fallback_primary_succeeds — fallback not used
# ---------------------------------------------------------------------------


async def test_fallback_primary_succeeds() -> None:
    """When the primary step succeeds, the fallback is NOT used."""
    client = MockClient()
    primary_agent = client.register("primary", _make_result(content="primary result"))
    fallback_agent = client.register("fallback", _make_result(content="fallback result"))

    pipeline = ConditionalPipeline(client).add_fallback(
        "step1",
        "primary",
        "Do the thing",
        fallback_agent_id="fallback",
        fallback_prompt="Fallback for the thing",
    )

    result = await pipeline.run()

    assert result.success is True
    assert result.final_result.content == "primary result"
    assert "step1" in result.steps
    assert "step1_fallback" not in result.steps
    primary_agent.execute.assert_called_once_with("Do the thing")
    fallback_agent.execute.assert_not_called()


# ---------------------------------------------------------------------------
# test_fallback_primary_fails — fallback runs
# ---------------------------------------------------------------------------


async def test_fallback_primary_fails_exception() -> None:
    """When the primary step raises an exception, the fallback runs."""
    client = MockClient()
    client.register_failing("primary", RuntimeError("primary exploded"))
    fallback_agent = client.register("fallback", _make_result(content="fallback saved it"))

    pipeline = ConditionalPipeline(client).add_fallback(
        "step1",
        "primary",
        "Do the thing",
        fallback_agent_id="fallback",
        fallback_prompt="Fallback for the thing",
    )

    result = await pipeline.run()

    assert result.success is True
    assert result.final_result.content == "fallback saved it"
    assert "step1_fallback" in result.steps
    fallback_agent.execute.assert_called_once_with("Fallback for the thing")


async def test_fallback_primary_returns_failure() -> None:
    """When the primary step returns success=False, the fallback runs."""
    client = MockClient()
    client.register("primary", _make_result(content="failed", success=False))
    fallback_agent = client.register("fallback", _make_result(content="fallback result"))

    pipeline = ConditionalPipeline(client).add_fallback(
        "step1",
        "primary",
        "Do the thing",
        fallback_agent_id="fallback",
        fallback_prompt="Fallback prompt",
    )

    result = await pipeline.run()

    assert result.success is True
    assert result.final_result.content == "fallback result"
    assert "step1_fallback" in result.steps
    fallback_agent.execute.assert_called_once_with("Fallback prompt")


async def test_fallback_output_available_to_subsequent_steps() -> None:
    """After a fallback runs, its output is available as a variable under the primary name."""
    client = MockClient()
    client.register_failing("primary", RuntimeError("boom"))
    client.register("fallback", _make_result(content="fallback data"))
    summarizer = client.register("summarizer", _make_result(content="final"))

    pipeline = (
        ConditionalPipeline(client)
        .add_fallback(
            "fetch",
            "primary",
            "Fetch data",
            fallback_agent_id="fallback",
            fallback_prompt="Use cached data",
        )
        .add_step("summarize", "summarizer", "Summarize: {fetch}")
    )

    result = await pipeline.run()

    assert result.success is True
    summarizer.execute.assert_called_once_with("Summarize: fallback data")


# ---------------------------------------------------------------------------
# test_mixed_pipeline — sequential + branch + parallel
# ---------------------------------------------------------------------------


async def test_mixed_pipeline() -> None:
    """A pipeline combining sequential, branch, and parallel steps."""
    client = MockClient()

    # Step 1: classify
    client.register("classifier", _make_result(content="This is a technical question"))

    # Branch: technical path
    client.register("tech-agent", _make_result(content="technical answer"))
    client.register("general-agent", _make_result(content="general answer"))

    # Parallel: two enrichment steps
    client.register("enricher-a", _make_result(content="enrichment A"))
    client.register("enricher-b", _make_result(content="enrichment B"))

    # Final summary step
    summary_agent = client.register("summarizer", _make_result(content="final summary"))

    pipeline = (
        ConditionalPipeline(client)
        .add_step("classify", "classifier", "Classify: {input}")
        .add_branch(
            "classify",
            condition=lambda r: "technical" in r.content.lower(),
            if_true=("answer", "tech-agent", "Tech answer for: {input}"),
            if_false=("answer", "general-agent", "General answer for: {input}"),
        )
        .add_parallel(
            [
                ("enrich_a", "enricher-a", "Enrich A: {answer}"),
                ("enrich_b", "enricher-b", "Enrich B: {answer}"),
            ]
        )
        .add_step("summary", "summarizer", "Summarize {enrich_a} and {enrich_b}")
    )

    result = await pipeline.run(input="How does async work?")

    assert result.success is True
    assert "classify" in result.steps
    assert "answer" in result.steps
    assert "enrich_a" in result.steps
    assert "enrich_b" in result.steps
    assert "summary" in result.steps
    assert result.final_result.content == "final summary"
    summary_agent.execute.assert_called_once_with(
        "Summarize enrichment A and enrichment B"
    )


async def test_mixed_sequential_then_fallback_then_sequential() -> None:
    """Sequential -> Fallback -> Sequential works end-to-end."""
    client = MockClient()
    client.register("agent1", _make_result(content="step1 output"))
    client.register_failing("risky", RuntimeError("failed"))
    client.register("safe", _make_result(content="safe output"))
    final_agent = client.register("final", _make_result(content="done"))

    pipeline = (
        ConditionalPipeline(client)
        .add_step("prep", "agent1", "Prepare {topic}")
        .add_fallback(
            "fetch",
            "risky",
            "Risky fetch for {prep}",
            fallback_agent_id="safe",
            fallback_prompt="Safe fetch for {prep}",
        )
        .add_step("finish", "final", "Finish with {fetch}")
    )

    result = await pipeline.run(topic="data")

    assert result.success is True
    assert result.final_result.content == "done"
    final_agent.execute.assert_called_once_with("Finish with safe output")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


async def test_total_latency_is_tracked() -> None:
    """PipelineResult.total_latency_ms is a non-negative integer."""
    client = MockClient()
    client.register("a1", _make_result(content="ok"))
    pipeline = ConditionalPipeline(client).add_step("s1", "a1", "go")

    result = await pipeline.run()

    assert result.total_latency_ms >= 0


async def test_add_parallel_returns_self() -> None:
    """add_parallel returns self for method chaining."""
    client = MockClient()
    pipeline = ConditionalPipeline(client)
    returned = pipeline.add_parallel([("s1", "a1", "p1")])
    assert returned is pipeline


async def test_add_branch_returns_self() -> None:
    """add_branch returns self for method chaining."""
    client = MockClient()
    pipeline = ConditionalPipeline(client)
    returned = pipeline.add_branch(
        "x",
        condition=lambda r: True,
        if_true=("a", "a1", "p"),
        if_false=("b", "a2", "p"),
    )
    assert returned is pipeline


async def test_add_fallback_returns_self() -> None:
    """add_fallback returns self for method chaining."""
    client = MockClient()
    pipeline = ConditionalPipeline(client)
    returned = pipeline.add_fallback(
        "s1", "a1", "p",
        fallback_agent_id="a2",
        fallback_prompt="fp",
    )
    assert returned is pipeline
