"""Retry policy with exponential backoff and jitter for gateway calls."""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from typing import Any, Awaitable, Callable, TypeVar

from pydantic import BaseModel, Field

from openclaw_sdk.core.exceptions import GatewayError, OpenClawError

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


class RetryPolicy(BaseModel):
    """Configurable retry policy with exponential backoff.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retries).
        backoff_base: Base delay in seconds for exponential backoff.
        backoff_max: Maximum delay in seconds (caps the exponential growth).
        jitter: If ``True``, add random jitter to the backoff delay.
        retryable_exceptions: Tuple of exception types that are eligible for retry.
    """

    max_retries: int = Field(default=3, ge=0, le=50)
    backoff_base: float = Field(default=1.0, ge=0.0)
    backoff_max: float = Field(default=60.0, ge=0.0)
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (GatewayError, TimeoutError)

    model_config = {"arbitrary_types_allowed": True}

    def _is_retryable(self, exc: Exception) -> bool:
        """Determine whether an exception should be retried.

        Resolution order:

        1. If the exception's **own class** (not a base class) explicitly
           overrides ``is_retryable``, that value takes precedence.  This
           lets subclasses like ``AuthenticationError`` (``False``) or
           ``RateLimitError`` (``True``) control retry behaviour directly.
        2. Otherwise, the exception is retried when it is an instance of
           one of the configured ``retryable_exceptions``.
        """
        # Check whether the concrete class (excluding the base OpenClawError
        # default) provides an explicit is_retryable override.
        if isinstance(exc, OpenClawError):
            # Walk the MRO; if any class *before* OpenClawError defines
            # is_retryable, honour it.
            for klass in type(exc).__mro__:
                if klass is OpenClawError:
                    break
                if "is_retryable" in klass.__dict__:
                    return bool(exc.is_retryable)
        elif hasattr(exc, "is_retryable"):
            # Non-SDK exceptions with an is_retryable attribute.
            return bool(exc.is_retryable)

        return isinstance(exc, self.retryable_exceptions)

    def _compute_delay(self, attempt: int) -> float:
        """Compute the backoff delay for the given attempt (0-indexed).

        Uses exponential backoff: ``backoff_base * 2^attempt``, capped at
        ``backoff_max``.  When ``jitter`` is enabled, the delay is uniformly
        distributed between 0 and the computed value.
        """
        delay: float = min(self.backoff_base * (2 ** attempt), self.backoff_max)
        if self.jitter:
            delay = random.uniform(0, delay)  # noqa: S311
        return delay

    async def execute(
        self,
        fn: Callable[..., Awaitable[_T]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        """Execute *fn* with retry logic.

        Calls ``await fn(*args, **kwargs)`` and retries on retryable
        exceptions up to ``max_retries`` times with exponential backoff.

        Args:
            fn: An async callable to execute.
            *args: Positional arguments forwarded to *fn*.
            **kwargs: Keyword arguments forwarded to *fn*.

        Returns:
            The return value of *fn*.

        Raises:
            Exception: The last exception raised by *fn* if all retries are
                exhausted, or immediately if the exception is not retryable.
        """
        last_exc: Exception | None = None

        for attempt in range(1 + self.max_retries):
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc

                if not self._is_retryable(exc):
                    raise

                if attempt >= self.max_retries:
                    logger.warning(
                        "Retry exhausted after %d attempt(s): %s",
                        attempt + 1,
                        exc,
                    )
                    raise

                delay = self._compute_delay(attempt)
                logger.info(
                    "Retry attempt %d/%d after %.2fs: %s",
                    attempt + 1,
                    self.max_retries,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

        # Should never be reached, but satisfies the type checker.
        assert last_exc is not None  # noqa: S101
        raise last_exc

    def as_decorator(
        self,
    ) -> Callable[[Callable[..., Awaitable[_T]]], Callable[..., Awaitable[_T]]]:
        """Return a decorator that wraps async functions with this retry policy.

        Usage::

            policy = RetryPolicy(max_retries=5)

            @policy.as_decorator()
            async def fragile_call():
                ...
        """

        def decorator(
            fn: Callable[..., Awaitable[_T]],
        ) -> Callable[..., Awaitable[_T]]:
            @functools.wraps(fn)
            async def wrapper(*args: Any, **kwargs: Any) -> _T:
                return await self.execute(fn, *args, **kwargs)

            return wrapper

        return decorator


def retry_async(
    max_retries: int = 3,
    backoff_base: float = 1.0,
    backoff_max: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (GatewayError, TimeoutError),
) -> Callable[[Callable[..., Awaitable[_T]]], Callable[..., Awaitable[_T]]]:
    """Decorator factory for async functions with retry logic.

    Creates a :class:`RetryPolicy` from the given parameters and uses it to
    wrap the decorated async function.

    Usage::

        @retry_async(max_retries=3)
        async def fetch_data():
            ...

    Args:
        max_retries: Maximum number of retry attempts (0 = no retries).
        backoff_base: Base delay in seconds for exponential backoff.
        backoff_max: Maximum delay in seconds (caps exponential growth).
        jitter: If ``True``, add random jitter to the backoff delay.
        retryable_exceptions: Tuple of exception types eligible for retry.

    Returns:
        A decorator that wraps an async callable with retry logic.
    """
    policy = RetryPolicy(
        max_retries=max_retries,
        backoff_base=backoff_base,
        backoff_max=backoff_max,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
    )

    def decorator(
        fn: Callable[..., Awaitable[_T]],
    ) -> Callable[..., Awaitable[_T]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> _T:
            return await policy.execute(fn, *args, **kwargs)

        return wrapper

    return decorator
