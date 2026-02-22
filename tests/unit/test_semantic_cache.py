"""Tests for cache/semantic.py and cache/embeddings.py — SemanticCache with embeddings."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from openclaw_sdk.cache.embeddings import (
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    SimpleEmbeddingProvider,
)
from openclaw_sdk.cache.semantic import SemanticCache
from openclaw_sdk.core.types import ExecutionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(content: str = "hello") -> ExecutionResult:
    return ExecutionResult(success=True, content=content)


# ---------------------------------------------------------------------------
# SemanticCache tests
# ---------------------------------------------------------------------------


async def test_cache_miss_on_empty() -> None:
    """An empty cache should always return None."""
    provider = SimpleEmbeddingProvider()
    cache = SemanticCache(embedding_provider=provider)

    result = await cache.get("agent-1", "what is the weather?")
    assert result is None


async def test_exact_match_hit() -> None:
    """The exact same query should always be a cache hit."""
    provider = SimpleEmbeddingProvider()
    cache = SemanticCache(embedding_provider=provider, similarity_threshold=0.99)

    expected = _make_result("sunny and warm")
    await cache.set("agent-1", "what is the weather?", expected)

    result = await cache.get("agent-1", "what is the weather?")
    assert result is not None
    assert result.content == "sunny and warm"


async def test_similar_query_hit() -> None:
    """Queries that are close (same text, different case) should hit."""
    provider = SimpleEmbeddingProvider()
    # SimpleEmbeddingProvider normalizes to lowercase+strip, so these should match.
    cache = SemanticCache(embedding_provider=provider, similarity_threshold=0.99)

    await cache.set("agent-1", "hello world", _make_result("greeting"))

    # Same text but with different casing and whitespace.
    result = await cache.get("agent-1", "  HELLO WORLD  ")
    assert result is not None
    assert result.content == "greeting"


async def test_dissimilar_query_miss() -> None:
    """Completely different queries should not match."""
    provider = SimpleEmbeddingProvider()
    cache = SemanticCache(embedding_provider=provider, similarity_threshold=0.85)

    await cache.set("agent-1", "what is the weather?", _make_result("sunny"))

    result = await cache.get("agent-1", "explain quantum entanglement")
    assert result is None


async def test_agent_isolation() -> None:
    """Agent-a cache should never be returned for agent-b."""
    provider = SimpleEmbeddingProvider()
    cache = SemanticCache(embedding_provider=provider, similarity_threshold=0.5)

    await cache.set("agent-a", "hello", _make_result("response-a"))

    # Same query, different agent — should miss.
    result = await cache.get("agent-b", "hello")
    assert result is None

    # Original agent should still hit.
    result = await cache.get("agent-a", "hello")
    assert result is not None
    assert result.content == "response-a"


async def test_ttl_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entries should expire after the TTL."""
    provider = SimpleEmbeddingProvider()
    cache = SemanticCache(
        embedding_provider=provider,
        ttl_seconds=10.0,
        similarity_threshold=0.99,
    )

    # Use a controllable monotonic clock.
    current_time = 1000.0

    def mock_monotonic() -> float:
        return current_time

    monkeypatch.setattr(time, "monotonic", mock_monotonic)

    await cache.set("agent-1", "hello", _make_result("world"))

    # Still within TTL.
    result = await cache.get("agent-1", "hello")
    assert result is not None

    # Advance past TTL.
    current_time = 1011.0
    result = await cache.get("agent-1", "hello")
    assert result is None


async def test_max_size_eviction() -> None:
    """Oldest entries should be evicted when max_size is exceeded."""
    provider = SimpleEmbeddingProvider()
    cache = SemanticCache(
        embedding_provider=provider,
        max_size=2,
        similarity_threshold=0.99,
    )

    await cache.set("agent-1", "query-1", _make_result("result-1"))
    await cache.set("agent-1", "query-2", _make_result("result-2"))
    await cache.set("agent-1", "query-3", _make_result("result-3"))

    # query-1 should have been evicted (oldest).
    assert await cache.get("agent-1", "query-1") is None

    # query-2 and query-3 should still be present.
    r2 = await cache.get("agent-1", "query-2")
    r3 = await cache.get("agent-1", "query-3")
    assert r2 is not None
    assert r2.content == "result-2"
    assert r3 is not None
    assert r3.content == "result-3"


async def test_configurable_threshold() -> None:
    """A very high threshold should reject even moderately similar queries."""
    provider = SimpleEmbeddingProvider()

    # With threshold=1.0, only exact matches should hit.
    cache_strict = SemanticCache(
        embedding_provider=provider,
        similarity_threshold=1.0,
    )
    await cache_strict.set("agent-1", "hello", _make_result("world"))

    # Even case differences won't produce similarity=1.0 exactly (floating point),
    # so a completely different query definitely misses.
    result = await cache_strict.get("agent-1", "completely unrelated query")
    assert result is None

    # With threshold=0.0, everything should hit (as long as same agent).
    cache_lenient = SemanticCache(
        embedding_provider=provider,
        similarity_threshold=0.0,
    )
    await cache_lenient.set("agent-1", "hello", _make_result("world"))
    result = await cache_lenient.get("agent-1", "anything at all")
    assert result is not None
    assert result.content == "world"


async def test_clear() -> None:
    """Clearing the cache should remove all entries."""
    provider = SimpleEmbeddingProvider()
    cache = SemanticCache(embedding_provider=provider, similarity_threshold=0.99)

    await cache.set("agent-1", "q1", _make_result("r1"))
    await cache.set("agent-1", "q2", _make_result("r2"))

    await cache.clear()

    assert await cache.get("agent-1", "q1") is None
    assert await cache.get("agent-1", "q2") is None


# ---------------------------------------------------------------------------
# EmbeddingProvider.cosine_similarity tests
# ---------------------------------------------------------------------------


async def test_cosine_similarity_identical_vectors() -> None:
    """Identical vectors should have similarity of 1.0."""
    vec = [1.0, 2.0, 3.0]
    sim = EmbeddingProvider.cosine_similarity(vec, vec)
    assert abs(sim - 1.0) < 1e-9


async def test_cosine_similarity_orthogonal_vectors() -> None:
    """Orthogonal vectors should have similarity of 0.0."""
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    sim = EmbeddingProvider.cosine_similarity(a, b)
    assert abs(sim) < 1e-9


async def test_cosine_similarity_zero_vector() -> None:
    """A zero vector should return 0.0 similarity."""
    zero = [0.0, 0.0, 0.0]
    other = [1.0, 2.0, 3.0]

    assert EmbeddingProvider.cosine_similarity(zero, other) == 0.0
    assert EmbeddingProvider.cosine_similarity(other, zero) == 0.0
    assert EmbeddingProvider.cosine_similarity(zero, zero) == 0.0


# ---------------------------------------------------------------------------
# SimpleEmbeddingProvider tests
# ---------------------------------------------------------------------------


async def test_simple_embedding_deterministic() -> None:
    """Same input should always produce the same embedding."""
    provider = SimpleEmbeddingProvider(dimensions=64)

    emb1 = await provider.embed("hello world")
    emb2 = await provider.embed("hello world")

    assert emb1 == emb2
    assert len(emb1) == 64


async def test_simple_embedding_different_texts_differ() -> None:
    """Different texts should produce different embeddings."""
    provider = SimpleEmbeddingProvider(dimensions=128)

    emb1 = await provider.embed("hello world")
    emb2 = await provider.embed("goodbye mars")

    assert emb1 != emb2

    # Both should be unit vectors.
    from math import sqrt

    mag1 = sqrt(sum(x * x for x in emb1))
    mag2 = sqrt(sum(x * x for x in emb2))
    assert abs(mag1 - 1.0) < 1e-9
    assert abs(mag2 - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# OpenAIEmbeddingProvider test (mocked)
# ---------------------------------------------------------------------------


async def test_openai_embedding_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAIEmbeddingProvider should call the API and return the embedding."""
    expected_embedding = [0.1, 0.2, 0.3, 0.4]

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(return_value=None)
    mock_response.json.return_value = {
        "data": [{"embedding": expected_embedding}],
        "model": "text-embedding-3-small",
        "usage": {"prompt_tokens": 5, "total_tokens": 5},
    }

    mock_post = AsyncMock(return_value=mock_response)

    # Patch httpx.AsyncClient to return our mock.
    class MockAsyncClient:
        async def __aenter__(self) -> MockAsyncClient:
            return self

        async def __aexit__(self, *args: Any) -> None:
            pass

        post = mock_post

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = OpenAIEmbeddingProvider(api_key="sk-test-key")
    result = await provider.embed("hello world")

    assert result == expected_embedding
    mock_post.assert_called_once()

    # Verify the request was made with correct parameters.
    call_kwargs = mock_post.call_args
    assert call_kwargs[1]["json"]["input"] == "hello world"
    assert call_kwargs[1]["json"]["model"] == "text-embedding-3-small"
    assert "Bearer sk-test-key" in call_kwargs[1]["headers"]["Authorization"]
