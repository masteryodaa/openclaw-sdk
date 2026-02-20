"""Tests for cache/base.py — InMemoryCache with TTL + LRU eviction."""

from __future__ import annotations

import asyncio

import pytest

from openclaw_sdk.cache.base import InMemoryCache, ResponseCache
from openclaw_sdk.callbacks.handler import CallbackHandler
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.types import ExecutionResult, StreamEvent
from openclaw_sdk.gateway.mock import MockGateway


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(content: str = "hello") -> ExecutionResult:
    return ExecutionResult(success=True, content=content)


# ---------------------------------------------------------------------------
# InMemoryCache unit tests
# ---------------------------------------------------------------------------


async def test_cache_miss_returns_none() -> None:
    cache = InMemoryCache()
    result = await cache.get("agent1", "what is 2+2?")
    assert result is None


async def test_cache_hit_returns_result() -> None:
    cache = InMemoryCache()
    expected = _make_result("four")
    await cache.set("agent1", "what is 2+2?", expected)

    result = await cache.get("agent1", "what is 2+2?")
    assert result is not None
    assert result.content == "four"
    assert result.success is True


async def test_cache_ttl_expiry() -> None:
    cache = InMemoryCache(ttl_seconds=0)
    await cache.set("agent1", "query", _make_result())

    # Even a tiny sleep should cause expiry with ttl_seconds=0.
    await asyncio.sleep(0.01)

    result = await cache.get("agent1", "query")
    assert result is None


async def test_cache_clear() -> None:
    cache = InMemoryCache()
    await cache.set("a", "q1", _make_result("r1"))
    await cache.set("a", "q2", _make_result("r2"))

    await cache.clear()

    assert await cache.get("a", "q1") is None
    assert await cache.get("a", "q2") is None


async def test_cache_max_size_eviction() -> None:
    cache = InMemoryCache(max_size=2)

    await cache.set("a", "q1", _make_result("r1"))
    await cache.set("a", "q2", _make_result("r2"))
    await cache.set("a", "q3", _make_result("r3"))  # should evict q1

    # q1 was evicted (oldest)
    assert await cache.get("a", "q1") is None
    # q2 and q3 remain
    assert (await cache.get("a", "q2")) is not None
    assert (await cache.get("a", "q3")) is not None


async def test_cache_key_includes_agent_id() -> None:
    """Same query on different agents should produce different cache keys."""
    cache = InMemoryCache()

    await cache.set("agent-a", "shared query", _make_result("answer-a"))
    await cache.set("agent-b", "shared query", _make_result("answer-b"))

    result_a = await cache.get("agent-a", "shared query")
    result_b = await cache.get("agent-b", "shared query")

    assert result_a is not None
    assert result_b is not None
    assert result_a.content == "answer-a"
    assert result_b.content == "answer-b"


async def test_cache_key_deterministic() -> None:
    """_cache_key should produce consistent hashes."""
    key1 = ResponseCache._cache_key("agent1", "hello")
    key2 = ResponseCache._cache_key("agent1", "hello")
    key3 = ResponseCache._cache_key("agent2", "hello")

    assert key1 == key2
    assert key1 != key3


async def test_cache_lru_ordering() -> None:
    """Accessing an entry should move it to the end, preventing eviction."""
    cache = InMemoryCache(max_size=2)

    await cache.set("a", "q1", _make_result("r1"))
    await cache.set("a", "q2", _make_result("r2"))

    # Access q1 — it moves to end, so q2 is now the oldest.
    await cache.get("a", "q1")

    # Adding q3 should evict q2 (oldest), not q1 (recently accessed).
    await cache.set("a", "q3", _make_result("r3"))

    assert await cache.get("a", "q1") is not None  # survived
    assert await cache.get("a", "q2") is None       # evicted
    assert await cache.get("a", "q3") is not None   # just added


# ---------------------------------------------------------------------------
# Agent.execute() integration with cache
# ---------------------------------------------------------------------------


class _RecordingCallback(CallbackHandler):
    def __init__(self) -> None:
        self.started: list[str] = []
        self.ended: list[str] = []

    async def on_execution_start(self, agent_id: str, query: str) -> None:
        self.started.append(agent_id)

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        self.ended.append(agent_id)


async def test_agent_execute_uses_cache() -> None:
    """First call hits gateway and populates cache; second call returns cached."""
    mock = MockGateway()
    await mock.connect()

    mock.register("chat.send", {"runId": "run1", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"runId": "run1", "content": "hello"}},
        )
    )

    cache = InMemoryCache()
    cb = _RecordingCallback()
    client = OpenClawClient(config=ClientConfig(), gateway=mock, cache=cache)

    agent = client.get_agent("test-bot")

    # First execution — gateway is called.
    result1 = await agent.execute("say hello", callbacks=[cb])
    assert result1.success is True
    assert result1.content == "hello"
    assert mock.call_count("chat.send") == 1

    # Second execution — served from cache, gateway NOT called again.
    result2 = await agent.execute("say hello", callbacks=[cb])
    assert result2.success is True
    assert result2.content == "hello"
    assert mock.call_count("chat.send") == 1  # still 1 — no second gateway call

    # Callbacks should have fired for both calls.
    assert cb.started.count("test-bot") == 2
    assert cb.ended.count("test-bot") == 2

    await client.close()


async def test_agent_execute_no_cache_by_default() -> None:
    """Without a cache, every execute() hits the gateway."""
    mock = MockGateway()
    await mock.connect()
    client = OpenClawClient(config=ClientConfig(), gateway=mock)

    mock.register("chat.send", {"runId": "r1", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"runId": "r1", "content": "hi"}},
        )
    )

    agent = client.get_agent("bot")
    result = await agent.execute("hello")
    assert result.content == "hi"
    assert mock.call_count("chat.send") == 1

    # Second call also needs events since there's no cache.
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"runId": "r1", "content": "hi again"}},
        )
    )
    result2 = await agent.execute("hello")
    assert mock.call_count("chat.send") == 2

    await client.close()
