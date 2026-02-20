from __future__ import annotations

import asyncio

import pytest

from openclaw_sdk.utils.async_helpers import run_sync, with_timeout

# ---------------------------------------------------------------------------
# run_sync
# ---------------------------------------------------------------------------


def test_run_sync_returns_value() -> None:
    """run_sync executes a coroutine and returns its result."""

    async def _coro() -> int:
        return 42

    result = run_sync(_coro())
    assert result == 42


def test_run_sync_propagates_exception() -> None:
    """run_sync re-raises exceptions from the coroutine."""

    async def _boom() -> None:
        raise ValueError("oops")

    with pytest.raises(ValueError, match="oops"):
        run_sync(_boom())


def test_run_sync_string_return() -> None:
    async def _greet() -> str:
        return "hello"

    assert run_sync(_greet()) == "hello"


def test_run_sync_awaits_async_sleep() -> None:
    """Verify that actual async I/O (asyncio.sleep) works correctly."""

    async def _sleep_and_return() -> str:
        await asyncio.sleep(0)
        return "done"

    assert run_sync(_sleep_and_return()) == "done"


# ---------------------------------------------------------------------------
# with_timeout — success cases
# ---------------------------------------------------------------------------


async def test_with_timeout_completes_within_limit() -> None:
    async def _fast() -> str:
        return "quick"

    result = await with_timeout(_fast(), seconds=5.0)
    assert result == "quick"


async def test_with_timeout_with_sleep_within_limit() -> None:
    async def _brief_sleep() -> int:
        await asyncio.sleep(0.01)
        return 99

    result = await with_timeout(_brief_sleep(), seconds=5.0)
    assert result == 99


async def test_with_timeout_returns_correct_type() -> None:
    async def _list_coro() -> list[int]:
        return [1, 2, 3]

    result = await with_timeout(_list_coro(), seconds=1.0)
    assert result == [1, 2, 3]


# ---------------------------------------------------------------------------
# with_timeout — timeout expiry
# ---------------------------------------------------------------------------


async def test_with_timeout_raises_on_expiry() -> None:
    """with_timeout raises asyncio.TimeoutError when the coroutine is too slow."""

    async def _slow() -> None:
        await asyncio.sleep(10)

    with pytest.raises(asyncio.TimeoutError):
        await with_timeout(_slow(), seconds=0.01)


async def test_with_timeout_raises_immediately_on_zero_timeout() -> None:
    async def _noop() -> None:
        await asyncio.sleep(1)

    with pytest.raises(asyncio.TimeoutError):
        await with_timeout(_noop(), seconds=0.0)


# ---------------------------------------------------------------------------
# with_timeout — exception propagation
# ---------------------------------------------------------------------------


async def test_with_timeout_propagates_inner_exception() -> None:
    async def _boom() -> None:
        raise RuntimeError("inner error")

    with pytest.raises(RuntimeError, match="inner error"):
        await with_timeout(_boom(), seconds=5.0)


# ---------------------------------------------------------------------------
# run_sync — ThreadPoolExecutor path (called from running loop)
# ---------------------------------------------------------------------------


async def test_run_sync_in_running_loop() -> None:
    """run_sync works when called from within an async context (uses ThreadPoolExecutor)."""

    async def _coro() -> str:
        return "from-thread"

    # Inside an async test the event loop is already running, so run_sync
    # takes the ThreadPoolExecutor path (lines 36-38 of async_helpers.py).
    result = run_sync(_coro())
    assert result == "from-thread"
