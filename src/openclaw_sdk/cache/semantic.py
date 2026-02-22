"""Semantic similarity cache using embedding vectors.

Provides :class:`SemanticCache`, a :class:`ResponseCache` implementation
that matches queries by cosine similarity of their embeddings rather than
exact string equality.
"""

from __future__ import annotations

import time

import structlog

from openclaw_sdk.cache.base import ResponseCache
from openclaw_sdk.cache.embeddings import EmbeddingProvider
from openclaw_sdk.core.types import ExecutionResult

logger = structlog.get_logger(__name__)


class SemanticCache(ResponseCache):
    """Cache that matches queries by semantic similarity using embeddings.

    Instead of requiring an exact query match (like :class:`InMemoryCache`),
    this cache computes embedding vectors for queries and returns cached
    results when cosine similarity exceeds a configurable threshold.

    **Agent isolation**: different agents never share cached results.  A query
    cached for ``agent-a`` will never be returned for ``agent-b``, even if the
    queries are semantically identical.

    Args:
        embedding_provider: Provider used to compute embedding vectors.
        similarity_threshold: Minimum cosine similarity for a cache hit
            (default ``0.85``).
        ttl_seconds: Time-to-live for each entry in seconds (default ``300.0``).
        max_size: Maximum number of entries before the oldest is evicted
            (default ``1000``).
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        similarity_threshold: float = 0.85,
        ttl_seconds: float = 300.0,
        max_size: int = 1000,
    ) -> None:
        self._provider = embedding_provider
        self._threshold = similarity_threshold
        self._ttl = ttl_seconds
        self._max_size = max_size
        # Store: list of (timestamp, agent_id, query, embedding, result)
        self._entries: list[
            tuple[float, str, str, list[float], ExecutionResult]
        ] = []

    async def get(self, agent_id: str, query: str) -> ExecutionResult | None:
        """Find a cached result by semantic similarity.

        Filters by *agent_id* first (different agents never return each
        other's cached results), then skips expired entries, and finally
        returns the result with the highest cosine similarity above the
        configured threshold.

        Args:
            agent_id: The agent to look up cached results for.
            query: The user query to match semantically.

        Returns:
            The best matching :class:`ExecutionResult`, or ``None`` on miss.
        """
        now = time.monotonic()
        embedding = await self._provider.embed(query)

        # Prune expired entries while we iterate.
        self._entries = [
            entry for entry in self._entries if now - entry[0] <= self._ttl
        ]

        best_score = 0.0
        best_result: ExecutionResult | None = None

        for _ts, aid, _q, emb, result in self._entries:
            if aid != agent_id:
                continue
            score = EmbeddingProvider.cosine_similarity(embedding, emb)
            if score > best_score and score >= self._threshold:
                best_score = score
                best_result = result

        if best_result is not None:
            logger.debug(
                "semantic cache hit",
                agent_id=agent_id,
                score=round(best_score, 4),
            )
        return best_result

    async def set(
        self, agent_id: str, query: str, result: ExecutionResult
    ) -> None:
        """Store a result in the semantic cache.

        Computes the embedding for *query* and stores it alongside the
        *result*.  If the cache exceeds *max_size*, the oldest entry is
        evicted.

        Args:
            agent_id: The agent this result belongs to.
            query: The original user query.
            result: The execution result to cache.
        """
        embedding = await self._provider.embed(query)
        now = time.monotonic()
        self._entries.append((now, agent_id, query, embedding, result))

        # Evict oldest entries when over capacity.
        while len(self._entries) > self._max_size:
            self._entries.pop(0)

        logger.debug(
            "semantic cache set",
            agent_id=agent_id,
            entries=len(self._entries),
        )

    async def clear(self) -> None:
        """Remove all entries from the cache."""
        self._entries.clear()
        logger.debug("semantic cache cleared")
