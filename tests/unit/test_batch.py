"""Tests for Agent.batch() — parallel query execution."""
from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_batch_returns_multiple_results() -> None:
    """3 queries should return 3 results."""
    client, mock = await _make_client_and_mock()

    call_count = 0

    def _send_handler(params: dict[str, object] | None) -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        return {"runId": f"run-{call_count}", "status": "started"}

    mock.register("chat.send", _send_handler)

    # Pre-emit DONE events for each query (consumed sequentially with max_concurrency=1)
    for i in range(1, 4):
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"runId": f"run-{i}", "content": f"response {i}"}},
            )
        )

    agent = client.get_agent("batch-bot")
    results = await agent.batch(
        ["q1", "q2", "q3"],
        max_concurrency=1,
    )

    assert len(results) == 3
    assert all(isinstance(r, ExecutionResult) for r in results)
    assert all(r.success for r in results)
    assert mock.call_count("chat.send") == 3
    await client.close()


async def test_batch_with_max_concurrency() -> None:
    """batch() works with max_concurrency=1 (fully sequential)."""
    client, mock = await _make_client_and_mock()

    call_count = 0

    def _send_handler(params: dict[str, object] | None) -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        return {"runId": f"run-{call_count}", "status": "started"}

    mock.register("chat.send", _send_handler)

    for i in range(1, 3):
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"runId": f"run-{i}", "content": f"result {i}"}},
            )
        )

    agent = client.get_agent("seq-bot")
    results = await agent.batch(
        ["alpha", "beta"],
        max_concurrency=1,
    )

    assert len(results) == 2
    assert results[0].content == "result 1"
    assert results[1].content == "result 2"
    await client.close()


async def test_batch_empty_list() -> None:
    """Empty input returns empty output — no gateway calls."""
    client, mock = await _make_client_and_mock()

    agent = client.get_agent("empty-bot")
    results = await agent.batch([])

    assert results == []
    assert mock.call_count("chat.send") == 0
    await client.close()


async def test_batch_preserves_order() -> None:
    """Results must match the order of the input queries."""
    client, mock = await _make_client_and_mock()

    call_count = 0

    def _send_handler(params: dict[str, object] | None) -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        return {"runId": f"run-{call_count}", "status": "started"}

    mock.register("chat.send", _send_handler)

    queries = ["first", "second", "third", "fourth"]
    for i in range(1, len(queries) + 1):
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"runId": f"run-{i}", "content": f"answer-{i}"}},
            )
        )

    agent = client.get_agent("order-bot")
    results = await agent.batch(queries, max_concurrency=1)

    assert len(results) == len(queries)
    assert results[0].content == "answer-1"
    assert results[1].content == "answer-2"
    assert results[2].content == "answer-3"
    assert results[3].content == "answer-4"
    await client.close()
