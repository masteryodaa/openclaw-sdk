"""SHA-256 based request deduplication with TTL and LRU eviction.

Prevents duplicate gateway calls within a configurable time window.
Uses :class:`collections.OrderedDict` for O(1) LRU eviction and
:func:`time.monotonic` for monotonic TTL tracking.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class RequestDeduplicator:
    """SHA-256 based request deduplication with TTL and LRU eviction.

    Each unique ``(method, params)`` pair is hashed and stored with a
    monotonic timestamp.  Subsequent calls within ``ttl_seconds`` are
    reported as duplicates.  Once the cache exceeds ``max_size``, the
    oldest (least-recently-seen) entry is evicted.

    Args:
        ttl_seconds: Time-to-live for each dedup entry in seconds.
        max_size: Maximum number of entries before LRU eviction kicks in.
    """

    def __init__(self, ttl_seconds: float = 60.0, max_size: int = 10000) -> None:
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._store: OrderedDict[str, float] = OrderedDict()
        self._lock = asyncio.Lock()

    def _compute_key(self, method: str, params: dict[str, Any]) -> str:
        """Compute a deterministic SHA-256 key from *method* and *params*."""
        raw = json.dumps({"method": method, "params": params}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    async def check_and_mark(self, method: str, params: dict[str, Any]) -> bool:
        """Check whether a request is a duplicate and mark it as seen.

        Returns:
            ``True`` if the request was already seen within the TTL window
            (i.e. it is a **duplicate**).  ``False`` if it is new.
        """
        key = self._compute_key(method, params)
        now = time.monotonic()

        async with self._lock:
            entry = self._store.get(key)

            if entry is not None:
                if now - entry <= self._ttl:
                    # Still within TTL — duplicate.
                    self._store.move_to_end(key)
                    logger.debug("dedup_duplicate", method=method)
                    return True
                # Expired — remove stale entry and treat as new.
                del self._store[key]

            # Mark as seen.
            self._store[key] = now
            self._store.move_to_end(key)

            # LRU eviction when over capacity.
            while len(self._store) > self._max_size:
                evicted_key, _ = self._store.popitem(last=False)
                logger.debug("dedup_evicted", key=evicted_key[:16])

            return False

    async def clear(self) -> None:
        """Remove all tracked entries."""
        async with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        """Return the number of currently tracked entries."""
        return len(self._store)
