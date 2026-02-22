"""Unit tests for RateLimiter."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from openclaw_sdk.resilience.rate_limiter import RateLimiter


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


async def _succeed() -> dict[str, Any]:
    return {"ok": True}


# ------------------------------------------------------------------ #
# test_allows_calls_within_limit
# ------------------------------------------------------------------ #


async def test_allows_calls_within_limit() -> None:
    """Calls within the limit should be allowed immediately."""
    rl = RateLimiter(max_calls=5, period=60.0)

    for _ in range(5):
        await rl.acquire()

    # All 5 calls should have been permitted without blocking.


# ------------------------------------------------------------------ #
# test_blocks_when_exhausted
# ------------------------------------------------------------------ #


async def test_blocks_when_exhausted() -> None:
    """acquire() should block when the call budget is exhausted."""
    rl = RateLimiter(max_calls=2, period=0.1)

    # Use up the budget.
    await rl.acquire()
    await rl.acquire()

    # The next acquire should block until the period elapses.
    start = time.monotonic()
    await rl.acquire()
    elapsed = time.monotonic() - start

    # Should have waited approximately 0.1 seconds.
    assert elapsed >= 0.05  # allow some tolerance


# ------------------------------------------------------------------ #
# test_replenishes_after_period
# ------------------------------------------------------------------ #


async def test_replenishes_after_period() -> None:
    """Tokens should become available again after the period elapses."""
    rl = RateLimiter(max_calls=2, period=0.05)

    # Exhaust the budget.
    await rl.acquire()
    await rl.acquire()
    assert rl.remaining == 0

    # Wait for the period to elapse.
    await asyncio.sleep(0.1)

    # Tokens should have replenished.
    assert rl.remaining == 2


# ------------------------------------------------------------------ #
# test_remaining_decrements
# ------------------------------------------------------------------ #


async def test_remaining_decrements() -> None:
    """remaining should decrement with each acquire()."""
    rl = RateLimiter(max_calls=3, period=60.0)

    assert rl.remaining == 3

    await rl.acquire()
    assert rl.remaining == 2

    await rl.acquire()
    assert rl.remaining == 1

    await rl.acquire()
    assert rl.remaining == 0


# ------------------------------------------------------------------ #
# test_execute_delegates
# ------------------------------------------------------------------ #


async def test_execute_delegates() -> None:
    """execute() should acquire a slot and then call the function."""
    rl = RateLimiter(max_calls=10, period=60.0)

    result = await rl.execute(_succeed)
    assert result == {"ok": True}

    # Should have consumed one slot.
    assert rl.remaining == 9


# ------------------------------------------------------------------ #
# test_custom_limits
# ------------------------------------------------------------------ #


async def test_custom_limits() -> None:
    """RateLimiter should respect custom max_calls and period."""
    rl = RateLimiter(max_calls=100, period=1.0)

    assert rl.remaining == 100

    for _ in range(50):
        await rl.acquire()

    assert rl.remaining == 50
