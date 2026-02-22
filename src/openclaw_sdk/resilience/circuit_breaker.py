"""Circuit breaker pattern for gateway calls."""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable, TypeVar

from openclaw_sdk.core.exceptions import CircuitOpenError

_T = TypeVar("_T")

# Circuit breaker states
_CLOSED = "closed"
_OPEN = "open"
_HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for gateway calls.

    Prevents cascading failures by tracking consecutive errors and
    short-circuiting calls when a failure threshold is exceeded.

    States:
        - **closed** (normal): calls pass through normally.
        - **open** (failing): calls are rejected immediately with
          :class:`CircuitOpenError`.
        - **half_open** (testing): a limited number of calls are allowed
          through to probe whether the downstream service has recovered.

    Args:
        failure_threshold: Number of consecutive failures required to
            open the circuit.
        recovery_timeout: Seconds to wait in the open state before
            transitioning to half-open.
        half_open_max_calls: Maximum number of probe calls allowed in
            the half-open state before deciding to close or re-open.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls

        self._failure_count: int = 0
        self._half_open_calls: int = 0
        self._state: str = _CLOSED
        self._opened_at: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        """Return the current circuit breaker state.

        Automatically transitions from *open* to *half_open* when the
        recovery timeout has elapsed.
        """
        if self._state == _OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self._recovery_timeout:
                self._state = _HALF_OPEN
                self._half_open_calls = 0
        return self._state

    async def execute(
        self,
        fn: Callable[..., Awaitable[_T]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        """Execute *fn* through the circuit breaker.

        Args:
            fn: An async callable to execute.
            *args: Positional arguments forwarded to *fn*.
            **kwargs: Keyword arguments forwarded to *fn*.

        Returns:
            The return value of *fn*.

        Raises:
            CircuitOpenError: If the circuit is currently open.
        """
        current = self.state

        if current == _OPEN:
            raise CircuitOpenError(
                "Circuit breaker is open, calls are being rejected",
                code="CIRCUIT_OPEN",
            )

        if current == _HALF_OPEN and self._half_open_calls >= self._half_open_max_calls:
            # Already exhausted the probe budget; re-open.
            self._trip()
            raise CircuitOpenError(
                "Circuit breaker is open, half-open probe limit reached",
                code="CIRCUIT_OPEN",
            )

        if current == _HALF_OPEN:
            self._half_open_calls += 1

        try:
            result: _T = await fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def reset(self) -> None:
        """Manually reset the circuit breaker to the closed state."""
        self._state = _CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        self._opened_at = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_success(self) -> None:
        """Record a successful call."""
        if self._state == _HALF_OPEN:
            # Probe succeeded — close the circuit.
            self.reset()
        else:
            # Reset the consecutive failure counter.
            self._failure_count = 0

    def _on_failure(self) -> None:
        """Record a failed call."""
        if self._state == _HALF_OPEN:
            # Probe failed — re-open immediately.
            self._trip()
            return

        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._trip()

    def _trip(self) -> None:
        """Transition to the open state."""
        self._state = _OPEN
        self._opened_at = time.monotonic()
        self._failure_count = 0
        self._half_open_calls = 0
