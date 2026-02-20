"""Tests for output/structured.py."""
from __future__ import annotations

import pytest
from pydantic import BaseModel

from openclaw_sdk.core.exceptions import OutputParsingError
from openclaw_sdk.core.types import ExecutionResult
from openclaw_sdk.output.structured import StructuredOutput


# ---------------------------------------------------------------------------
# Test models
# ---------------------------------------------------------------------------


class SalesReport(BaseModel):
    title: str
    revenue: float
    units_sold: int


class SimpleModel(BaseModel):
    name: str
    value: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(content: str, success: bool = True) -> ExecutionResult:
    return ExecutionResult(success=success, content=content)


class MockAgent:
    """Agent that returns a fixed ExecutionResult for each call."""

    def __init__(self, *results: ExecutionResult) -> None:
        self._results = list(results)
        self._call_count = 0

    async def execute(self, query: str) -> ExecutionResult:
        result = self._results[self._call_count % len(self._results)]
        self._call_count += 1
        return result


# ---------------------------------------------------------------------------
# schema_prompt()
# ---------------------------------------------------------------------------


def test_schema_prompt_returns_string() -> None:
    prompt = StructuredOutput.schema_prompt(SalesReport)
    assert isinstance(prompt, str)


def test_schema_prompt_includes_field_names() -> None:
    prompt = StructuredOutput.schema_prompt(SalesReport)
    assert "title" in prompt
    assert "revenue" in prompt
    assert "units_sold" in prompt


def test_schema_prompt_contains_json_fence() -> None:
    prompt = StructuredOutput.schema_prompt(SimpleModel)
    assert "```json" in prompt
    assert "```" in prompt


def test_schema_prompt_contains_respond_instruction() -> None:
    prompt = StructuredOutput.schema_prompt(SimpleModel)
    assert "JSON" in prompt


# ---------------------------------------------------------------------------
# parse() — fenced ```json...``` block
# ---------------------------------------------------------------------------


def test_parse_fenced_json_block() -> None:
    response = """
Here is the result:
```json
{"name": "Alice", "value": 42}
```
Have a great day!
"""
    result = StructuredOutput.parse(response, SimpleModel)
    assert result.name == "Alice"
    assert result.value == 42


def test_parse_fenced_json_block_with_whitespace() -> None:
    response = "```json\n  {\"name\": \"Bob\", \"value\": 99}\n```"
    result = StructuredOutput.parse(response, SimpleModel)
    assert result.name == "Bob"
    assert result.value == 99


def test_parse_fenced_json_block_preferred_over_bare() -> None:
    """When both a fenced block and bare JSON are present, the fenced block wins."""
    response = (
        '{"name": "bare", "value": 0}\n'
        "```json\n"
        '{"name": "fenced", "value": 1}\n'
        "```"
    )
    result = StructuredOutput.parse(response, SimpleModel)
    assert result.name == "fenced"


# ---------------------------------------------------------------------------
# parse() — bare JSON object
# ---------------------------------------------------------------------------


def test_parse_bare_json_object() -> None:
    response = 'The answer is {"name": "Carol", "value": 7}.'
    result = StructuredOutput.parse(response, SimpleModel)
    assert result.name == "Carol"
    assert result.value == 7


def test_parse_bare_json_object_only() -> None:
    response = '{"name": "Dave", "value": 123}'
    result = StructuredOutput.parse(response, SimpleModel)
    assert result.name == "Dave"
    assert result.value == 123


# ---------------------------------------------------------------------------
# parse() — error cases
# ---------------------------------------------------------------------------


def test_parse_raises_output_parsing_error_if_no_json() -> None:
    with pytest.raises(OutputParsingError, match="No JSON found"):
        StructuredOutput.parse("There is no JSON here at all.", SimpleModel)


def test_parse_raises_output_parsing_error_if_invalid_json() -> None:
    with pytest.raises(OutputParsingError):
        StructuredOutput.parse("```json\n{invalid json}\n```", SimpleModel)


def test_parse_raises_output_parsing_error_if_schema_mismatch() -> None:
    # Valid JSON but missing required fields
    with pytest.raises(OutputParsingError):
        StructuredOutput.parse('{"unexpected_field": true}', SalesReport)


def test_parse_error_message_includes_model_name() -> None:
    try:
        StructuredOutput.parse('{"wrong": 1}', SalesReport)
    except OutputParsingError as exc:
        assert "SalesReport" in str(exc)
    else:
        pytest.fail("Expected OutputParsingError")


# ---------------------------------------------------------------------------
# execute() — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_returns_parsed_model() -> None:
    response_json = '{"name": "Eve", "value": 55}'
    agent = MockAgent(_make_result(content=f"```json\n{response_json}\n```"))
    result = await StructuredOutput.execute(agent, "Give me a SimpleModel", SimpleModel)
    assert result.name == "Eve"
    assert result.value == 55


@pytest.mark.asyncio
async def test_execute_appends_schema_to_query() -> None:
    captured_queries: list[str] = []

    class CapturingAgent:
        async def execute(self, query: str) -> ExecutionResult:
            captured_queries.append(query)
            return _make_result('{"name": "X", "value": 0}')

    agent = CapturingAgent()
    await StructuredOutput.execute(agent, "My query", SimpleModel)

    assert len(captured_queries) == 1
    assert "My query" in captured_queries[0]
    assert "JSON" in captured_queries[0]  # schema_prompt was appended


# ---------------------------------------------------------------------------
# execute() — retries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_retries_on_parse_failure() -> None:
    """First response is invalid, second is valid — should succeed after 1 retry."""
    bad_result = _make_result(content="no json here")
    good_result = _make_result(content='{"name": "Frank", "value": 7}')
    agent = MockAgent(bad_result, good_result)

    result = await StructuredOutput.execute(agent, "query", SimpleModel, max_retries=2)
    assert result.name == "Frank"
    assert agent._call_count == 2


@pytest.mark.asyncio
async def test_execute_raises_after_all_retries_exhausted() -> None:
    bad_result = _make_result(content="no json")
    agent = MockAgent(bad_result)  # always returns bad result

    with pytest.raises(OutputParsingError):
        await StructuredOutput.execute(agent, "query", SimpleModel, max_retries=2)

    # 1 initial attempt + 2 retries = 3 total
    assert agent._call_count == 3


@pytest.mark.asyncio
async def test_execute_no_retries_raises_immediately_on_failure() -> None:
    bad_result = _make_result(content="no json")
    agent = MockAgent(bad_result)

    with pytest.raises(OutputParsingError):
        await StructuredOutput.execute(agent, "query", SimpleModel, max_retries=0)

    assert agent._call_count == 1


@pytest.mark.asyncio
async def test_execute_succeeds_on_first_try_no_retry_needed() -> None:
    good_result = _make_result(content='{"name": "Gina", "value": 3}')
    agent = MockAgent(good_result)

    result = await StructuredOutput.execute(agent, "query", SimpleModel, max_retries=2)
    assert result.name == "Gina"
    assert agent._call_count == 1  # No unnecessary retries


@pytest.mark.asyncio
async def test_execute_complex_model() -> None:
    content = '{"title": "Q1 Report", "revenue": 123456.78, "units_sold": 999}'
    agent = MockAgent(_make_result(content=content))

    result = await StructuredOutput.execute(agent, "Get sales", SalesReport)
    assert result.title == "Q1 Report"
    assert abs(result.revenue - 123456.78) < 1e-6
    assert result.units_sold == 999
