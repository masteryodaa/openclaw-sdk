"""Response caching layer with TTL and LRU eviction.

Provides :class:`ResponseCache` (abstract base) and :class:`InMemoryCache`
(default implementation backed by :class:`collections.OrderedDict`).
"""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Tuple

from openclaw_sdk.core.types import ExecutionResult


class ResponseCache(ABC):
    """Abstract base class for response caches.

    Subclass this to plug in Redis, disk, or any other backend.
    """

    @staticmethod
    def _cache_key(agent_id: str, query: str) -> str:
        """Compute a deterministic cache key from *agent_id* and *query*."""
        raw = f"{agent_id}:{query}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @abstractmethod
    async def get(self, agent_id: str, query: str) -> ExecutionResult | None:
        """Return a cached result, or ``None`` on miss / expiry."""

    @abstractmethod
    async def set(self, agent_id: str, query: str, result: ExecutionResult) -> None:
        """Store *result* in the cache, keyed by *agent_id* + *query*."""

    @abstractmethod
    async def clear(self) -> None:
        """Remove all entries from the cache."""


class InMemoryCache(ResponseCache):
    """LRU cache with per-entry TTL, backed by :class:`collections.OrderedDict`.

    Args:
        ttl_seconds: Time-to-live for each entry in seconds (default 300).
        max_size: Maximum number of entries before the oldest is evicted (default 1000).
    """

    def __init__(self, ttl_seconds: float = 300, max_size: int = 1000) -> None:
        self._ttl = ttl_seconds
        self._max_size = max_size
        # Stores (timestamp, result) tuples, ordered by access time.
        self._store: OrderedDict[str, Tuple[float, ExecutionResult]] = OrderedDict()

    async def get(self, agent_id: str, query: str) -> ExecutionResult | None:
        """Return cached result or ``None`` on miss / expiry."""
        key = self._cache_key(agent_id, query)
        entry = self._store.get(key)
        if entry is None:
            return None

        ts, result = entry
        if time.monotonic() - ts > self._ttl:
            # Expired -- remove and report miss.
            del self._store[key]
            return None

        # Hit -- move to end (most-recently-used).
        self._store.move_to_end(key)
        return result

    async def set(self, agent_id: str, query: str, result: ExecutionResult) -> None:
        """Store *result*, evicting the oldest entry when *max_size* is exceeded."""
        key = self._cache_key(agent_id, query)

        # If key already exists, remove first so insertion goes to the end.
        if key in self._store:
            del self._store[key]

        self._store[key] = (time.monotonic(), result)

        # Evict oldest (first item) when over capacity.
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    async def clear(self) -> None:
        """Empty the cache."""
        self._store.clear()
