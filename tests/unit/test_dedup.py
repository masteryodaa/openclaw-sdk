"""Tests for core/dedup.py — RequestDeduplicator."""
from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

from openclaw_sdk.core.dedup import RequestDeduplicator


# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------


async def test_first_request_not_duplicate() -> None:
    dedup = RequestDeduplicator()
    is_dup = await dedup.check_and_mark("chat.send", {"message": "hello"})
    assert is_dup is False


async def test_same_request_is_duplicate() -> None:
    dedup = RequestDeduplicator()
    await dedup.check_and_mark("chat.send", {"message": "hello"})
    is_dup = await dedup.check_and_mark("chat.send", {"message": "hello"})
    assert is_dup is True


async def test_different_params_not_duplicate() -> None:
    dedup = RequestDeduplicator()
    await dedup.check_and_mark("chat.send", {"message": "hello"})
    is_dup = await dedup.check_and_mark("chat.send", {"message": "world"})
    assert is_dup is False


async def test_different_method_not_duplicate() -> None:
    dedup = RequestDeduplicator()
    await dedup.check_and_mark("chat.send", {"message": "hello"})
    is_dup = await dedup.check_and_mark("chat.abort", {"message": "hello"})
    assert is_dup is False


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------


async def test_ttl_expiry_allows_retry() -> None:
    """After TTL expires, the same request should no longer be a duplicate."""
    dedup = RequestDeduplicator(ttl_seconds=5.0)

    base = time.monotonic()
    with patch("openclaw_sdk.core.dedup.time") as mock_time:
        mock_time.monotonic.return_value = base
        await dedup.check_and_mark("chat.send", {"x": 1})

        # Within TTL — still a duplicate.
        mock_time.monotonic.return_value = base + 3.0
        assert await dedup.check_and_mark("chat.send", {"x": 1}) is True

        # After TTL — no longer a duplicate.
        mock_time.monotonic.return_value = base + 6.0
        assert await dedup.check_and_mark("chat.send", {"x": 1}) is False


# ---------------------------------------------------------------------------
# LRU eviction
# ---------------------------------------------------------------------------


async def test_lru_eviction() -> None:
    dedup = RequestDeduplicator(max_size=3)

    await dedup.check_and_mark("m", {"i": 1})
    await dedup.check_and_mark("m", {"i": 2})
    await dedup.check_and_mark("m", {"i": 3})
    assert dedup.size == 3

    # Adding a 4th should evict the oldest (i=1).
    await dedup.check_and_mark("m", {"i": 4})
    assert dedup.size == 3

    # i=1 was evicted — should no longer be a duplicate.
    is_dup = await dedup.check_and_mark("m", {"i": 1})
    assert is_dup is False


# ---------------------------------------------------------------------------
# clear() and size
# ---------------------------------------------------------------------------


async def test_clear() -> None:
    dedup = RequestDeduplicator()
    await dedup.check_and_mark("m", {"a": 1})
    await dedup.check_and_mark("m", {"a": 2})
    assert dedup.size == 2
    await dedup.clear()
    assert dedup.size == 0

    # After clear, previously-seen requests are new again.
    assert await dedup.check_and_mark("m", {"a": 1}) is False


async def test_size_property() -> None:
    dedup = RequestDeduplicator()
    assert dedup.size == 0
    await dedup.check_and_mark("m", {"k": "v"})
    assert dedup.size == 1
    await dedup.check_and_mark("m", {"k": "v2"})
    assert dedup.size == 2


# ---------------------------------------------------------------------------
# Concurrent access
# ---------------------------------------------------------------------------


async def test_concurrent_access() -> None:
    """Multiple concurrent check_and_mark calls should not corrupt state."""
    dedup = RequestDeduplicator()

    async def _mark(i: int) -> bool:
        return await dedup.check_and_mark("m", {"i": i})

    results = await asyncio.gather(*[_mark(i) for i in range(50)])
    # All 50 are unique — none should be a duplicate.
    assert all(r is False for r in results)
    assert dedup.size == 50


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


async def test_empty_params() -> None:
    dedup = RequestDeduplicator()
    is_dup = await dedup.check_and_mark("chat.send", {})
    assert is_dup is False
    is_dup = await dedup.check_and_mark("chat.send", {})
    assert is_dup is True
