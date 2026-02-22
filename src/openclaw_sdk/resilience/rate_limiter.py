"""Token bucket rate limiter for API calls."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, TypeVar

_T = TypeVar("_T")


class RateLimiter:
    """Token bucket rate limiter for API calls.

    Limits the number of calls allowed within a rolling time window.
    When the limit is exhausted, :meth:`acquire` blocks until enough
    time has elapsed for a token to become available.

    Args:
        max_calls: Maximum number of calls allowed per *period*.
        period: Length of the time window in seconds (default ``60.0``).
    """

    def __init__(self, max_calls: int = 60, period: float = 60.0) -> None:
        self._max_calls = max_calls
        self._period = period
        self._timestamps: list[float] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def acquire(self) -> None:
        """Wait until a call is allowed under the rate limit.

        Blocks asynchronously if the call budget for the current window
        has been exhausted, resuming once a slot becomes available.
        """
        while True:
            now = time.monotonic()
            self._purge(now)

            if len(self._timestamps) < self._max_calls:
                self._timestamps.append(now)
                return

            # Wait until the oldest timestamp in the window expires.
            wait_time = self._timestamps[0] + self._period - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            # Loop back to re-check after sleeping.

    async def execute(
        self,
        fn: Callable[..., Awaitable[_T]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        """Execute *fn* after acquiring a rate limit slot.

        Args:
            fn: An async callable to execute.
            *args: Positional arguments forwarded to *fn*.
            **kwargs: Keyword arguments forwarded to *fn*.

        Returns:
            The return value of *fn*.
        """
        await self.acquire()
        return await fn(*args, **kwargs)

    @property
    def remaining(self) -> int:
        """Return the number of calls still available in the current window."""
        self._purge(time.monotonic())
        return max(0, self._max_calls - len(self._timestamps))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _purge(self, now: float) -> None:
        """Remove timestamps that have fallen outside the current window."""
        cutoff = now - self._period
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.pop(0)
