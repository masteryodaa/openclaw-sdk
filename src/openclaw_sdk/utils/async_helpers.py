from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


def run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine synchronously.

    Creates a new event loop if none is running.
    If a loop is already running (e.g. inside Jupyter or an existing async context),
    submits the coroutine to a fresh thread-owned event loop via
    ``asyncio.run_coroutine_threadsafe`` so the calling thread blocks until done.

    Args:
        coro: The coroutine to run.

    Returns:
        The value returned by *coro*.

    Raises:
        Any exception raised by *coro*.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — safe to create a fresh one.
        return asyncio.run(coro)

    # A loop is already running (Jupyter, test harness with asyncio_mode="auto", etc.).
    # Run the coroutine in a brand-new loop on a background thread so this thread
    # can block on its result without deadlocking the existing loop.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


async def with_timeout(coro: Coroutine[Any, Any, T], seconds: float) -> T:
    """Run *coro* with a deadline, raising ``asyncio.TimeoutError`` if it exceeds *seconds*.

    Args:
        coro: The coroutine to run.
        seconds: Maximum number of seconds to wait.

    Returns:
        The value returned by *coro*.

    Raises:
        asyncio.TimeoutError: If *coro* does not complete within *seconds*.
    """
    return await asyncio.wait_for(coro, timeout=seconds)
